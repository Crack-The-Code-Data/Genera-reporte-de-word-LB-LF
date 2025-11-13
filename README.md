# Genera Reporte de Word - Línea Base / Línea Final

Sistema automatizado para generar reportes en Word con análisis de cuestionarios educativos usando OpenAI y AWS.

## Descripción

Este proyecto automatiza la generación de reportes de diagnóstico educativo en formato Word, procesando datos de cuestionarios de entrada y salida (Línea Base / Línea Final). Utiliza OpenAI para generar análisis y conclusiones automáticas basadas en los datos recopilados.

## Características

- Generación automática de reportes en formato Word (.docx)
- Análisis de datos con OpenAI (GPT-4o-mini)
- Procesamiento de cuestionarios educativos (entrada/salida)
- Integración con AWS AppFlow para ejecutar flujos de datos
- Generación de gráficos y visualizaciones con matplotlib/seaborn
- Cálculo automático de costos de uso de OpenAI
- Análisis de múltiples dimensiones educativas

## Requisitos

- Python 3.8 o superior
- Cuenta de OpenAI con API key
- Cuenta de AWS con acceso a AppFlow (opcional)
- Credenciales de AWS configuradas (si se usa AppFlow)

## Instalación

1. Clonar el repositorio:
```bash
git clone <url-del-repositorio>
cd Genera-reporte-de-word-LB-LF
```

2. Crear un entorno virtual (recomendado):
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

3. Instalar dependencias:
```bash
pip install -r requirements.txt
```

## Configuración

### API Key de OpenAI

**IMPORTANTE:** Por razones de seguridad, NO incluyas tu API key directamente en el código.

Crea un archivo `.env` en la raíz del proyecto (este archivo está en .gitignore):

```env
OPENAI_API_KEY=tu_api_key_aqui
```

Modifica `openIA_analisis_conclusiones.py` para cargar la key desde el archivo .env:

```python
import os
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
```

Instala python-dotenv:
```bash
pip install python-dotenv
```

### AWS Credentials

Si usas el script de AWS AppFlow, configura tus credenciales:

```bash
aws configure
```

O mediante variables de entorno:
```bash
export AWS_ACCESS_KEY_ID=tu_access_key
export AWS_SECRET_ACCESS_KEY=tu_secret_key
export AWS_DEFAULT_REGION=us-east-1
```

## Uso

### Notebook Principal

Abre y ejecuta el notebook de análisis:
```bash
jupyter notebook "NB Cuestionarios.ipynb"
```

### Ejecutar Flujos de AWS AppFlow

Para forzar la ejecución de flujos scheduled en AppFlow:

```bash
# Ejecutar un flujo específico
python "Forzar flujo.py" nombre-del-flujo

# Ejecutar múltiples flujos
python "Forzar flujo.py" flujo1 flujo2 flujo3

# Modo interactivo (seleccionar de la lista)
python "Forzar flujo.py"

# Sin restaurar el trigger original
python "Forzar flujo.py" --no-restore nombre-del-flujo
```

## Estructura del Proyecto

```
.
├── Forzar flujo.py                    # Script para ejecutar flujos de AWS AppFlow
├── openIA_analisis_conclusiones.py    # Funciones de análisis con OpenAI
├── NB Cuestionarios.ipynb             # Notebook principal de análisis
├── requirements.txt                   # Dependencias del proyecto
└── README.md                         # Este archivo
```

## Funcionalidades Principales

### openIA_analisis_conclusiones.py

Módulo principal con funciones de análisis:

- `call_gpt()`: Interfaz para llamar a la API de OpenAI
- `analyze_dataframe()`: Analiza DataFrames y genera conclusiones
- `analyze_list()`: Genera resumen ejecutivo desde conclusiones parciales
- `insight_parcial()`: Genera insights intermedios
- `insight_list()`: Genera estructura JSON con hallazgos por categoría

**Características:**
- Registro automático de tokens utilizados
- Cálculo de costos por modelo
- Soporte para múltiples modelos GPT-4o, o1, o3, etc.

### Forzar flujo.py

Script para ejecutar flujos de AWS AppFlow con trigger Scheduled:

- Cambia temporalmente el trigger a OnDemand
- Ejecuta el flujo
- Restaura el trigger Scheduled original
- Soporte para ejecución paralela de múltiples flujos

### NB Cuestionarios.ipynb

Notebook interactivo que:
1. Procesa datos de cuestionarios educativos
2. Genera análisis estadísticos y visualizaciones
3. Usa OpenAI para generar conclusiones automáticas
4. Exporta resultados a documento Word

## Modelos de OpenAI Soportados

El sistema incluye costos actualizados para:
- GPT-4.1, GPT-4o, GPT-4o-mini
- O1, O3, O4-mini
- Modelos especializados (audio, search, realtime)

## Salida

El sistema genera:
- Reportes en formato Word (.docx) con análisis completos
- Archivos CSV con métricas de uso de OpenAI
- Visualizaciones (gráficos) en el documento Word
- Log de tokens y costos utilizados

## Seguridad

- **NUNCA** subas archivos `.env` o con API keys al repositorio
- Los archivos `.docx`, `.xlsx` y `.csv` están excluidos por .gitignore
- Las métricas de uso (`uso_modelo.csv`) no se suben al repositorio
- Revisa siempre que no haya credenciales en el código antes de hacer commit

## Costos

El uso de OpenAI tiene costos asociados. El sistema registra automáticamente:
- Tokens de entrada/salida por llamada
- Costo en USD por modelo utilizado
- Log detallado en `registro_tokens`

## Contribuir

Para contribuir al proyecto:
1. Haz un fork del repositorio
2. Crea una rama para tu feature
3. Realiza tus cambios
4. Asegúrate de no incluir credenciales
5. Envía un pull request

## Notas

- Los documentos de entrada/salida deben estar en formato Excel
- El sistema espera columnas específicas en los cuestionarios
- Los análisis se basan estrictamente en los datos proporcionados
- Las conclusiones son generadas por IA y deben ser revisadas

## Licencia

Este proyecto es de uso interno de Crack The Code.

## Soporte

Para reportar problemas o solicitar funcionalidades, contacta al equipo de desarrollo.
