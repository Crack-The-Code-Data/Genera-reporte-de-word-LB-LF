#!/usr/bin/env python3
"""
Script para ejecutar flujos de AppFlow con trigger Scheduled.
Cambia temporalmente el trigger a OnDemand, ejecuta, y restaura el Schedule.
"""

import boto3
from botocore.exceptions import ClientError
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
import time


def obtener_flujos_appflow() -> List[Dict]:
    """Lista todos los flujos de AppFlow disponibles."""
    client = boto3.client('appflow')
    flujos = []
    
    try:
        next_token = None
        
        while True:
            if next_token:
                response = client.list_flows(maxResults=100, nextToken=next_token)
            else:
                response = client.list_flows(maxResults=100)
            
            flujos.extend(response.get('flows', []))
            
            next_token = response.get('nextToken')
            if not next_token:
                break
        
        return flujos
    
    except ClientError as e:
        print(f"Error al listar flujos: {e}")
        return []


def obtener_detalle_flujo(flow_name: str) -> Dict:
    """Obtiene los detalles completos de un flujo."""
    client = boto3.client('appflow')
    
    try:
        response = client.describe_flow(flowName=flow_name)
        return response
    except Exception as e:
        print(f"Error al obtener detalles del flujo {flow_name}: {e}")
        return None


def cambiar_trigger_a_ondemand(flow_name: str, flow_config: Dict) -> bool:
    """
    Cambia el trigger de un flujo a OnDemand.
    
    Returns:
        True si fue exitoso, False en caso contrario
    """
    client = boto3.client('appflow')
    
    try:
        # Preparar la configuración para update_flow
        update_params = {
            'flowName': flow_name,
            'triggerConfig': {
                'triggerType': 'OnDemand'
            },
            'sourceFlowConfig': flow_config['sourceFlowConfig'],
            'destinationFlowConfigList': flow_config['destinationFlowConfigList'],
            'tasks': flow_config['tasks']
        }
        
        # Agregar campos opcionales si existen
        if 'description' in flow_config:
            update_params['description'] = flow_config['description']
        
        client.update_flow(**update_params)
        return True
    
    except Exception as e:
        print(f"  Error al cambiar trigger a OnDemand: {e}")
        return False


def restaurar_trigger_scheduled(flow_name: str, trigger_config_original: Dict, flow_config: Dict) -> bool:
    """
    Restaura el trigger original Scheduled de un flujo con fecha de inicio actualizada.
    
    Returns:
        True si fue exitoso, False en caso contrario
    """
    client = boto3.client('appflow')
    
    try:
        # Copiar la configuración del trigger original
        trigger_config_restaurado = trigger_config_original.copy()
        
        # Si es Scheduled, actualizar la fecha de inicio a una fecha futura válida
        if trigger_config_restaurado.get('triggerType') == 'Scheduled':
            trigger_props = trigger_config_restaurado.get('triggerProperties', {})
            
            # Crear una copia del objeto Scheduled
            if 'Scheduled' in trigger_props:
                scheduled_config = trigger_props['Scheduled'].copy()
                
                # Establecer scheduleStartTime a 5 minutos en el futuro
                from datetime import datetime, timedelta, timezone
                future_start = datetime.now(timezone.utc) + timedelta(minutes=5)
                scheduled_config['scheduleStartTime'] = future_start
                
                # Eliminar scheduleEndTime si existe y ya pasó
                if 'scheduleEndTime' in scheduled_config:
                    end_time = scheduled_config['scheduleEndTime']
                    if isinstance(end_time, datetime) and end_time < datetime.now(timezone.utc):
                        del scheduled_config['scheduleEndTime']
                
                # Actualizar la configuración
                trigger_props['Scheduled'] = scheduled_config
                trigger_config_restaurado['triggerProperties'] = trigger_props
        
        update_params = {
            'flowName': flow_name,
            'triggerConfig': trigger_config_restaurado,
            'sourceFlowConfig': flow_config['sourceFlowConfig'],
            'destinationFlowConfigList': flow_config['destinationFlowConfigList'],
            'tasks': flow_config['tasks']
        }
        
        if 'description' in flow_config:
            update_params['description'] = flow_config['description']
        
        client.update_flow(**update_params)
        
        # Activar el flujo después de actualizar
        try:
            client.start_flow(flowName=flow_name)
        except ClientError as e:
            # Si falla la activación, no es crítico (puede ser que ya esté activo)
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code != 'ConflictException':
                print(f"  Advertencia al activar flujo: {e}")
        
        return True
    
    except Exception as e:
        print(f"  Error al restaurar trigger Scheduled: {e}")
        return False


def ejecutar_flujo(flow_name: str) -> Dict:
    """Ejecuta un flujo de AppFlow."""
    client = boto3.client('appflow')
    
    try:
        response = client.start_flow(flowName=flow_name)
        
        return {
            'success': True,
            'execution_id': response.get('executionId', 'N/A'),
            'message': 'Iniciado exitosamente'
        }
    
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '')
        error_message = e.response.get('Error', {}).get('Message', '')
        
        return {
            'success': False,
            'execution_id': 'N/A',
            'message': f"{error_code}: {error_message}"
        }


def procesar_flujo_scheduled(flow_name: str, restaurar: bool = True) -> Dict:
    """
    Procesa un flujo Scheduled: cambia a OnDemand, ejecuta, y opcionalmente restaura.
    
    Args:
        flow_name: Nombre del flujo
        restaurar: Si True, restaura el trigger Scheduled después de ejecutar
        
    Returns:
        Diccionario con resultado del proceso
    """
    resultado = {
        'flow_name': flow_name,
        'trigger_original': None,
        'cambio_trigger': False,
        'ejecucion': None,
        'restauracion': False,
        'success': False,
        'message': ''
    }
    
    # 1. Obtener configuración actual del flujo
    flow_config = obtener_detalle_flujo(flow_name)
    
    if not flow_config:
        resultado['message'] = 'No se pudo obtener configuración del flujo'
        return resultado
    
    trigger_config = flow_config.get('triggerConfig', {})
    trigger_type = trigger_config.get('triggerType', 'Unknown')
    
    resultado['trigger_original'] = trigger_type
    
    # Si ya es OnDemand, solo ejecutar
    if trigger_type == 'OnDemand':
        resultado['cambio_trigger'] = True  # No necesitó cambio
        exec_result = ejecutar_flujo(flow_name)
        resultado['ejecucion'] = exec_result
        resultado['success'] = exec_result['success']
        resultado['message'] = exec_result['message']
        resultado['restauracion'] = True  # No necesitó restauración
        return resultado
    
    # 2. Cambiar trigger a OnDemand
    if not cambiar_trigger_a_ondemand(flow_name, flow_config):
        resultado['message'] = 'Error al cambiar trigger a OnDemand'
        return resultado
    
    resultado['cambio_trigger'] = True
    
    # Esperar un poco para que el cambio se propague
    time.sleep(2)
    
    # 3. Ejecutar el flujo
    exec_result = ejecutar_flujo(flow_name)
    resultado['ejecucion'] = exec_result
    
    # 4. Restaurar trigger Scheduled si se solicitó
    if restaurar:
        time.sleep(1)
        if restaurar_trigger_scheduled(flow_name, trigger_config, flow_config):
            resultado['restauracion'] = True
            resultado['success'] = exec_result['success']
            resultado['message'] = exec_result['message']
        else:
            resultado['restauracion'] = False
            resultado['success'] = False
            resultado['message'] = f"{exec_result['message']} | ⚠ No se pudo restaurar trigger Scheduled"
    else:
        resultado['success'] = exec_result['success']
        resultado['message'] = f"{exec_result['message']} | ⚠ Trigger quedó en OnDemand"
        resultado['restauracion'] = False
    
    return resultado


def main():
    """Función principal del script."""
    import sys
    
    print("=" * 120)
    print("EJECUCIÓN DE FLUJOS SCHEDULED (Cambio temporal a OnDemand)")
    print("=" * 120)
    
    # Verificar si se debe restaurar el trigger
    no_restaurar = '--no-restore' in sys.argv
    if no_restaurar:
        sys.argv.remove('--no-restore')
    
    restaurar = not no_restaurar
    
    if not restaurar:
        print("\n⚠ MODO --no-restore: Los triggers NO se restaurarán a Scheduled")
    
    # Obtener nombres de flujos
    if len(sys.argv) > 1:
        flow_names = sys.argv[1:]
        print(f"\nEjecutando {len(flow_names)} flujo(s) especificado(s)...\n")
    else:
        print("\nObteniendo lista de flujos...")
        flujos = obtener_flujos_appflow()
        
        if not flujos:
            print("No se encontraron flujos de AppFlow.")
            return
        
        flujos_activos = [f for f in flujos if f.get('flowStatus') == 'Active']
        
        if not flujos_activos:
            print("No se encontraron flujos activos.")
            return
        
        print(f"\nFlujos activos encontrados: {len(flujos_activos)}")
        print("\nLista de flujos:")
        for i, flujo in enumerate(flujos_activos, 1):
            print(f"  {i}. {flujo['flowName']}")
        
        print("\nOpciones:")
        print("  - Ingresa números separados por comas (ej: 1,3,5)")
        print("  - Ingresa 'all' para ejecutar todos")
        print("  - Ingresa 'q' para salir")
        
        seleccion = input("\nSelección: ").strip()
        
        if seleccion.lower() == 'q':
            print("Operación cancelada.")
            return
        elif seleccion.lower() == 'all':
            flow_names = [f['flowName'] for f in flujos_activos]
        else:
            try:
                indices = [int(x.strip()) - 1 for x in seleccion.split(',')]
                flow_names = [flujos_activos[i]['flowName'] for i in indices if 0 <= i < len(flujos_activos)]
            except (ValueError, IndexError):
                print("Selección inválida.")
                return
        
        if not flow_names:
            print("No se seleccionaron flujos válidos.")
            return
    
    # Confirmar ejecución
    print(f"\n¿Ejecutar {len(flow_names)} flujo(s)?")
    for name in flow_names:
        print(f"  - {name}")
    
    if restaurar:
        print("\nProceso: Cambiar a OnDemand → Ejecutar → Restaurar a Scheduled")
    else:
        print("\n⚠ Proceso: Cambiar a OnDemand → Ejecutar (SIN restaurar a Scheduled)")
    
    confirmar = input("\nContinuar? (s/n): ").strip().lower()
    if confirmar != 's':
        print("Operación cancelada.")
        return
    
    # Procesar flujos (NO en paralelo para evitar conflictos)
    print(f"\nProcesando {len(flow_names)} flujo(s)...")
    print("=" * 120)
    
    resultados = []
    for i, flow_name in enumerate(flow_names, 1):
        print(f"\n[{i}/{len(flow_names)}] Procesando: {flow_name}")
        resultado = procesar_flujo_scheduled(flow_name, restaurar)
        resultados.append(resultado)
        
        # Mostrar resultado inmediato
        if resultado['success']:
            print(f"  ✓ {resultado['message']}")
        else:
            print(f"  ✗ {resultado['message']}")
    
    # Mostrar resumen final
    print("\n" + "=" * 120)
    print("RESUMEN DE EJECUCIÓN")
    print("=" * 120)
    
    print(f"\n{'FLUJO':<45} {'TRIGGER':<12} {'RESULTADO':<15} {'RESTAURADO':<12} {'MENSAJE':<35}")
    print("-" * 120)
    
    exitosos = 0
    fallidos = 0
    no_restaurados = 0
    
    for r in resultados:
        flow_display = r['flow_name'][:44]
        trigger = r['trigger_original'] or 'Unknown'
        estado = "✓ EXITOSO" if r['success'] else "✗ FALLIDO"
        restaurado = "✓ Sí" if r['restauracion'] else "✗ No"
        mensaje = r['message'][:34]
        
        print(f"{flow_display:<45} {trigger:<12} {estado:<15} {restaurado:<12} {mensaje:<35}")
        
        if r['success']:
            exitosos += 1
        else:
            fallidos += 1
        
        if not r['restauracion'] and r['trigger_original'] == 'Scheduled':
            no_restaurados += 1
    
    print("=" * 120)
    print(f"\n✓ Exitosos: {exitosos}")
    print(f"✗ Fallidos: {fallidos}")
    
    if no_restaurados > 0:
        print(f"\n⚠ ATENCIÓN: {no_restaurados} flujo(s) NO fueron restaurados a Scheduled")
        print("  Estos flujos quedaron con trigger OnDemand y NO se ejecutarán automáticamente.")
        print("  Debes restaurarlos manualmente desde la consola de AWS o ejecutar este script nuevamente.")
    
    print()


if __name__ == "__main__":
    main()