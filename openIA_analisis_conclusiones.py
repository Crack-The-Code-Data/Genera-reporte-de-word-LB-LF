import pandas as pd
import openai
from typing import List, Union
import os
from datetime import datetime
from dotenv import load_dotenv
import json
import re

# Cargar variables de entorno desde .env
load_dotenv()

# Configurar la clave API de OpenAI desde variable de entorno
openai.api_key = os.getenv("OPENAI_API_KEY")

# Validar que la API key esté configurada
if not openai.api_key:
    raise ValueError("OPENAI_API_KEY no está configurada. Por favor, crea un archivo .env con tu API key.") 

registro_tokens=[]  # Nueva lista para registrar los tokens usados en cada ejecución

# Diccionario de precios por modelo (USD por 1K tokens)
PRECIOS_MODELOS = {
    'gpt-4.1': {'input': 2.00, 'output': 8.00},
    'gpt-4.1-mini': {'input': 0.40, 'output': 1.60},
    'gpt-4.1-nano': {'input': 0.10, 'output': 0.40},
    'gpt-4.5-preview': {'input': 75.00, 'output': 150.00},
    'gpt-4o': {'input': 2.50, 'output': 10.00},
    'gpt-4o-mini': {'input': 0.15, 'output': 0.60},
    'gpt-4o-mini-realtime-preview': {'input': 0.60, 'output': 2.40},
    'gpt-4o-realtime-preview': {'input': 5.00, 'output': 20.00},
    'gpt-4o-audio-preview': {'input': 2.50, 'output': 10.00},
    'gpt-4o-mini-audio-preview': {'input': 0.15, 'output': 0.60},
    'gpt-4o-search-preview': {'input': 2.50, 'output': 10.00},
    'gpt-4o-mini-search-preview': {'input': 0.15, 'output': 0.60},
    'o1': {'input': 15.00, 'output': 60.00},
    'o1-pro': {'input': 150.00, 'output': 600.00},
    'o3-pro': {'input': 20.00, 'output': 80.00},
    'o3': {'input': 2.00, 'output': 8.00},
    'o3-deep-research': {'input': 10.00, 'output': 40.00},
    'o4-mini': {'input': 1.10, 'output': 4.40},
    'o4-mini-deep-research': {'input': 2.00, 'output': 8.00},
    'o3-mini': {'input': 1.10, 'output': 4.40},
    'o1-mini': {'input': 1.10, 'output': 4.40},
    'codex-mini-latest': {'input': 1.50, 'output': 6.00},
    'computer-use-preview': {'input': 3.00, 'output': 12.00},
    'gpt-image-1': {'input': 5.00, 'output': 1.25},
}

def call_gpt(prompt: str, modelo: str = "gpt-4.1-nano", max_tokens: int = 1500, temperature: float = 0.7) -> str:
    """
    Llama a la API de OpenAI. Por defecto usa gpt-4o-mini.
    
    Args:
        prompt (str): Texto del prompt a enviar.
        max_tokens (int): Máximo de tokens en la respuesta.
        temperature (float): Control de creatividad (0.0-1.0).
    
    Returns:
        str: Respuesta del modelo.
    """
    try:
        response = openai.chat.completions.create(
            model=modelo,
            messages=[
                {"role": "system", "content": """
Eres un analista de datos educativos especializado en la redacción de informes técnicos profesionales.

CONTEXTO:
Debes redactar secciones específicas de un informe sobre resultados de proyectos educativos, basándote únicamente en los datos proporcionados.

DIRECTRICES ESTRICTAS:

1. OBJETIVIDAD ABSOLUTA:
   - Describe únicamente lo que muestran los datos, sin interpretaciones causales
   - Evita correlaciones no fundamentadas (ej: "X indica éxito del programa")
   - No atribuyas significado sin evidencia directa
   - Usa lenguaje neutral y descriptivo

2. LENGUAJE PROFESIONAL:
   - Emplea terminología técnica apropiada
   - Redacta en tercera persona
   - Utiliza voz pasiva cuando sea pertinente
   - Mantén un tono formal y académico

3. PROHIBICIONES EXPLÍCITAS:
   - NO inferir causalidad sin evidencia
   - NO hacer juicios de valor sobre los datos
   - NO relacionar variables demográficas con éxito/fracaso
   - NO incluir recomendaciones no solicitadas
   - NO usar adjetivos valorativos (exitoso, deficiente, prometedor)

4. FORMATO DE RESPUESTA:
   - Párrafos concisos de 3-5 oraciones
   - Incluye datos específicos cuando sea relevante (porcentajes, cifras)

EJEMPLO DE REDACCIÓN APROPIADA:
Incorrecto: "La alta participación femenina (70%) demuestra el éxito del programa"
Correcto: "La distribución por género muestra una participación del 70% de mujeres y 30% de hombres"

                 """},
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=temperature
        )
        result = response.choices[0].message.content.strip()

        usage = response.usage
        input_tokens = usage.prompt_tokens
        output_tokens = usage.completion_tokens

        # Determinar el modelo base para buscar en el diccionario (por si el nombre tiene sufijos de fecha)
        modelo_base = modelo.split("-")[0] if modelo not in PRECIOS_MODELOS else modelo
        if modelo not in PRECIOS_MODELOS:
            # Buscar coincidencia parcial si el modelo tiene sufijo de fecha
            for key in PRECIOS_MODELOS:
                if modelo.startswith(key):
                    modelo_base = key
                    break
        else:
            modelo_base = modelo
        precios = PRECIOS_MODELOS.get(modelo_base, {'input': 0, 'output': 0})
        
        cost_usd = (input_tokens * precios['input'] + output_tokens * precios['output']) / 1000000

        # Registrar información de tokens en la lista registro_tokens
        registro_tokens.append({
            'fecha_hora': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'modelo': modelo,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'costo_usd': cost_usd,
        })

        return result
    



    except openai.OpenAIError as e:
        return f"Error en la API de OpenAI: {str(e)}"
    except Exception as e:
        return f"Error inesperado: {str(e)}"

def analyze_dataframe(df: pd.DataFrame, pregunta: str = "", matriz: bool = False, tokens: int = 1000) -> str:
    """
    Analiza un DataFrame y obtiene conclusiones.
    
    Args:
        df (pd.DataFrame): DataFrame a analizar.
        pregunta (str): Pregunta asociada a los datos del DataFrame.
    
    Returns:
        str: Conclusión generada por el modelo.
    """
    # Convertir DataFrame a string (primeras filas y descripción)

    json_str = df.to_json(orient="records", lines=False, force_ascii=False)

    if matriz is True:

        base_prompt = f"""
        Contexto: '{pregunta}'.

        Realiza un análisis conciso de máximo 3 líneas. 
        Da una conclusion a partir de tendencias, valores atípicos o patrones relevantes para el lector.
        Sé claro, preciso y enfócate en los aspectos más significativos.

        No dees valores que no puedan ser observados en los datos y tampoco dees resultados de calculos
        .

        json a analizar:
        {json_str}

        Formato de salida: No uses markdown, solo texto plano. No uses titulos, solo párrafos. No uses emojis. No uses saltos de linea. Porcentajes con 1 decimal.
        """
    else:

        base_prompt = f"""
        Tema: '{pregunta}'.

        Realiza un análisis conciso de máximo 3 líneas. 
        Identifica y explica las características más importantes o destacadas de los datos, como tendencias, valores atípicos, distribuciones o patrones relevantes.
        Sé claro, preciso y enfócate en los aspectos más significativos.
        
        
        Json a analizar:
        {json_str}

        Formato de salida: No uses markdown, solo texto plano. No uses titulos, solo párrafos. No uses emojis. No uses saltos de linea. Porcentajes con 1 decimal.
        """
    
    return call_gpt(base_prompt, max_tokens=tokens)

def analyze_list(data_list: List[Union[int, float, str]], proyectos: pd.DataFrame = None, introduccion: str = "", tokens: int = 2000) -> str:
    """
    Analiza una lista y obtiene conclusiones.
    
    Args:
        data_list (List): Lista de datos a analizar.
        introduccion (str): Introducción o contexto del análisis.
    
    Returns:
        str: Conclusión generada por el modelo.
    """
    # Convertir lista a string
    list_str = ", ".join(str(item) for item in data_list)

    if proyectos is not None:
        json_str = proyectos.to_json(orient="records", lines=False, force_ascii=False)
    else:
        json_str = ""
    
    # Construir prompt base
    base_prompt = f"""
    Basándote en la siguiente introducción y las conclusiones parciales proporcionadas, 
    genera un resumen ejecutivo de todo el documento en un máximo de 3-4 párrafos. 
    Nombra a todos los proyectos y que actividades se realizaron en cada uno de ellos.
    Sintetiza la información, destacando los hallazgos clave, el impacto general del proyecto y cualquier
    recomendación o insight relevante para futuros proyectos. Mantén el tono profesional y orientado a resultados educativos

    Proyectos:
    {json_str}

    Introduccion:
    {introduccion}

    Las conclusiones parciales son: {list_str}.

    Formato de salida: No uses markdown, solo texto plano. No uses titulos, solo párrafos. No uses emojis. No uses saltos de linea.
    """
    
    return call_gpt(base_prompt, max_tokens=tokens)

def insight_parcial(data_list: List[Union[int, float, str]], pregunta: str = "", tokens: int = 1000) -> str:

    """
    Analiza una lista y obtiene insights claves.
    
    Args:
        data_list (List): Lista de datos a analizar.
    
    Returns:
        str: Conclusión generada por el modelo.
    """
    # Convertir lista a string
    list_str = ", ".join(str(item) for item in data_list)
    
    # Construir prompt base
    base_prompt = f"""
    Basandote en las conclusiones parciales a la {pregunta}. 
    Genera maximo 3 insight a modo de resumen para que vuelvan a ser interpretados por el modelo.

    Conclusiones parciales:
    {list_str} """
    
    return call_gpt(base_prompt, max_tokens=tokens)


def insight_list(data_list: List[Union[int, float, str]], proyectos: pd.DataFrame = None, introduccion: str = "", tokens: int = 2000) -> str:
    """
    Analiza una lista y obtiene insights claves pero extensos, devolviendo un JSON válido.
    
    Args:
        data_list (List): Lista de datos a analizar.
        proyectos (pd.DataFrame): DataFrame con información de proyectos.
        introduccion (str): Introducción o contexto del análisis.
        tokens (int): Máximo de tokens para la respuesta.
    
    Returns:
        str: JSON válido con insights generados por el modelo.
    """
    # Convertir lista a string
    list_str = ", ".join(str(item) for item in data_list)

    if proyectos is not None:
        json_str = proyectos.to_json(orient="records", lines=False, force_ascii=False)
    else:
        json_str = ""
    
    # Construir prompt mejorado con instrucciones más estrictas
    base_prompt = f"""
Basándote en la siguiente introducción, información de proyectos y conclusiones parciales, genera un resumen estructurado en formato JSON que destaque los principales hallazgos e insights por dimensión o categoría.

👉 Introducción:
{introduccion}

👉 Proyectos:
{json_str}

👉 Conclusiones parciales:
{list_str}

🧾 Formato de salida EXACTO (devuelve ÚNICAMENTE este JSON, sin texto adicional):
{{    
  "Contexto General del Diagnóstico": [
    "Insight 1",
    "Insight 2",
    "Insight 3"
  ],
  "Hallazgos Clave y Correlaciones Relevantes": {{
    "Nombre de la categoría": [
      "Insight 1",
      "Insight 2",
      "Insight 3",
      "Implicación: texto aquí"
    ]
  }},
  "Retos Priorizados Identificados": [
    {{
      "Eje": "Nombre del eje",
      "Reto": "Descripción del reto",
      "Relevancia": "Razón por la cual es importante"
    }}
  ],
  "Otras Secciones Relevantes": {{
    "Título de la sección": [
      "Insight 1",
      "Insight 2",
      "Insight 3"
    ]
  }},
  "Relevancia del Programa": [
    "Punto 1 sobre impacto del programa",
    "Punto 2",
    "Punto 3"
  ]
}}

✅ INSTRUCCIONES CRÍTICAS PARA JSON VÁLIDO:
- Tu respuesta DEBE ser ÚNICAMENTE el objeto JSON, sin markdown, sin explicaciones, sin comentarios
- NO uses comillas simples, SOLO comillas dobles
- NO pongas comas después del último elemento de arrays o objetos
- NO uses saltos de línea dentro de los strings (usa espacios en su lugar)
- Si necesitas usar comillas dentro de un string, escápalas con backslash
- NO incluyas los caracteres ```json o ``` al inicio o final
- Si alguna sección no aplica, omítela completamente
- Asegúrate de cerrar todos los corchetes y llaves correctamente
- Los valores numéricos NO deben estar entre comillas

RECUERDA: Solo devuelve el JSON, absolutamente NADA más.
"""
    
    # Llamar al modelo GPT
    respuesta_gpt = call_gpt(base_prompt, max_tokens=tokens)
    
    # Limpiar y validar el JSON
    json_limpio = limpiar_json_respuesta(respuesta_gpt)
    
    return json_limpio


def limpiar_json_respuesta(texto_respuesta: str) -> str:
    """
    Limpia y valida el JSON devuelto por GPT para asegurar que sea válido.
    
    Args:
        texto_respuesta (str): Respuesta cruda del modelo GPT.
    
    Returns:
        str: JSON válido como string.
    """
    try:
        # Paso 1: Extraer solo el JSON del texto
        # Buscar el patrón del JSON
        match = re.search(r'\{.*\}', texto_respuesta, re.DOTALL)
        
        if not match:
            print("⚠️ No se encontró JSON en la respuesta")
            return json.dumps({
                "error": "No se pudo generar el JSON",
                "respuesta_original": texto_respuesta[:500]
            })
        
        json_str = match.group(0)
        
        # Paso 2: Limpiezas básicas
        # Eliminar markdown si existe
        json_str = re.sub(r'```json\s*', '', json_str)
        json_str = re.sub(r'```\s*', '', json_str)
        
        # Paso 3: Intentar parsear directamente
        try:
            parsed = json.loads(json_str)
            # Si funciona, devolverlo como string JSON válido
            return json.dumps(parsed, ensure_ascii=False, indent=2)
        except json.JSONDecodeError:
            pass
        
        # Paso 4: Aplicar correcciones si falla el parseo inicial
        # Eliminar saltos de línea problemáticos dentro de strings
        json_str = re.sub(r'("(?:[^"\\]|\\.)*")', 
                         lambda m: m.group(0).replace('\n', ' ').replace('\r', ''), 
                         json_str)
        
        # Eliminar comas antes de } o ]
        json_str = re.sub(r',\s*([}\]])', r'\1', json_str)
        
        # Corregir comillas mal escapadas
        json_str = re.sub(r'\\([^"\\/bfnrtu])', r'\1', json_str)
        
        # Eliminar caracteres invisibles problemáticos
        json_str = ''.join(char for char in json_str if ord(char) >= 32 or char in '\n\r\t')
        
        # Paso 5: Segundo intento de parseo
        try:
            parsed = json.loads(json_str)
            return json.dumps(parsed, ensure_ascii=False, indent=2)
        except json.JSONDecodeError as e:
            print(f"⚠️ Error al parsear JSON después de limpieza: {e}")
            
            # Paso 6: Intento más agresivo de reparación
            try:
                # Reemplazar valores problemáticos
                json_str = re.sub(r':\s*undefined', ': null', json_str)
                json_str = re.sub(r':\s*NaN', ': null', json_str)
                
                # Asegurar que los strings estén entre comillas
                json_str = re.sub(r'([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', json_str)
                
                parsed = json.loads(json_str)
                return json.dumps(parsed, ensure_ascii=False, indent=2)
                
            except:
                # Paso 7: Si todo falla, devolver una estructura por defecto
                print("❌ No se pudo reparar el JSON. Devolviendo estructura por defecto.")
                return json.dumps({
                    "Contexto General del Diagnóstico": [
                        "Error al procesar la respuesta del modelo"
                    ],
                    "Hallazgos Clave y Correlaciones Relevantes": {
                        "Estado": ["Revisar manualmente la salida del modelo"]
                    },
                    "Retos Priorizados Identificados": [
                        {
                            "Eje": "Procesamiento",
                            "Reto": "Error en formato JSON",
                            "Relevancia": "Requiere revisión manual"
                        }
                    ],
                    "respuesta_original_truncada": texto_respuesta[:500]
                }, ensure_ascii=False, indent=2)
                
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return json.dumps({
            "error": str(e),
            "mensaje": "Error procesando la respuesta"
        })