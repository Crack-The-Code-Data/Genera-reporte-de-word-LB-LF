import pandas as pd
import openai
from typing import List, Union
import os
from datetime import datetime
from dotenv import load_dotenv

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

def call_gpt(prompt: str, modelo: str = "gpt-4o-mini", max_tokens: int = 1500, temperature: float = 0.7) -> str:
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
                {"role": "system", "content": """Eres un asistente analítico experto en datos, especializado en el sector educativo.
                 Vas a analizar datos de una empresa dedicada a la educación que implementa proyectos formativos. 
                 Tu tarea es interpretar los datos proporcionados, que incluyen respuestas a estas encuestas, y generar conclusiones sin suponer nada no basado estrictamente en los datos.
                 considerando diferencias entre las respuestas de entrada y salida, tendencias en las respuestas y posibles patrones demográficos o de comportamiento.
                 
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
    Analiza una lista y obtiene insights claves pero extensos.
    
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
Basándote en la siguiente introducción, información de proyectos y conclusiones parciales, genera un resumen estructurado en formato JSON que destaque los principales hallazgos e insights por dimensión o categoría.

👉 Introducción:
{introduccion}

👉 Proyectos:
{json_str}

👉 Conclusiones parciales:
{list_str}

🧾 Formato de salida (devuelve solo un JSON):
{{    
  "Contexto General del Diagnóstico": [
    "Insight 1",
    "Insight 2",
    "Insight 3",
    ...
  ],
  "Hallazgos Clave y Correlaciones Relevantes": {{
    "<Nombre de la categoría>": [
      "Insight 1",
      "Insight 2",
      "Insight 3",
      ...,
      "Implicación: ..."
    ],
    ...
  }},
  "Retos Priorizados Identificados": [
    {{
      "Eje": "Nombre del eje",
      "Reto": "Descripción del reto",
      "Relevancia": "Razón por la cual es importante"
    }},
    ...
  ],
  "Otras Secciones Relevantes": {{
    "Título de la sección": [
      "Insight 1",
      "Insight 2",
      "Insight 3",
      ...
    ],
    ...
  }},
  "Relevancia del Programa": [
    "Punto 1 sobre impacto del programa",
    "Punto 2",
    "Punto 3",
    ...
  ]
}}


✅ Instrucciones:
- No incluyas ningún texto fuera del JSON, asegurate de que el json sea valido.
- Si alguna sección no aplica, omítela (no dejes campos vacíos).
- Usa nombres de categoría o sección que surjan naturalmente del análisis.
- Redacta en estilo claro y sintético. Usa viñetas si lo considerás útil.
- Las implicaciones deben reflejar posibles líneas de acción o interpretaciones del dato.

"""
    
    return call_gpt(base_prompt, max_tokens=tokens)