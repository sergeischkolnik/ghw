"""
Script para crear datos de prueba en la base de datos local.
Corre: python test_data.py
"""
import asyncio
import db
import datetime
import random

async def create_test_data():
    """Crea workflows de prueba para el dashboard"""
    
    print("🔧 Inicializando BD...")
    await db.init_db()
    
    # Datos de ejemplo
    machines = ["Shaker", "Barredora", "Recogedora", "SBS Shaker", "Carro Estanque"]
    components = ["MOTOR", "CILINDROS", "MANGUERAS", "CABLES", "ACEITE_HIDRAULICO"]
    clients = ["Cliente A", "Cliente B", "Cliente C", "AgroTech SA", "Cosecha Plus"]
    services = ["PODADORA", "FUMIGADORA", "RASTRA"]
    
    print("\n📝 Creando workflows de prueba...\n")
    
    # Crear 15 TALLER workflows
    for i in range(15):
        now = datetime.datetime.now() - datetime.timedelta(days=random.randint(0, 30))
        workflow = {
            'type': 'TALLER',
            'machine_name': random.choice(machines),
            'machine_num': str(random.randint(1, 5)),
            'component_id': f'CP{str(i % 5).zfill(3)}',
            'subcomponent_id': f'CS{str(i % 8).zfill(3)}',
            'selected_indices': [random.randint(0, 5) for _ in range(random.randint(1, 3))],
            'current_items': ['Revisar Estado', 'Revisar Carga', 'Cambio de Aceite'],
            'comment': f'Revisión #{i+1}',
            'panas': random.choice(['bueno', 'regular', 'malo']),
            'start': now,
            'end': now + datetime.timedelta(hours=random.randint(1, 4))
        }
        try:
            id_result = await db.insert_workflow_with_retry(workflow, user_id=100 + i)
            print(f"✅ TALLER #{i+1} guardado (ID: {id_result})")
        except Exception as e:
            print(f"❌ Error en TALLER #{i+1}: {e}")
    
    # Crear 10 SERVICIO workflows
    for i in range(10):
        now = datetime.datetime.now() - datetime.timedelta(days=random.randint(0, 30))
        workflow = {
            'type': 'SERVICIO',
            'client': random.choice(clients),
            'service': random.choice(services),
            'subservice': f'SUB_{random.choice(services)}',
            'details': {
                'hileras': f'H{random.randint(1, 3)}',
                'caras': f'C{random.randint(1, 2)}',
                'pasadas': f'P{random.randint(1, 4)}'
            },
            'horometro_inicio': str(random.randint(100, 5000)),
            'horometro_termino': str(random.randint(5001, 10000)),
            'hectareas': str(round(random.uniform(1, 50), 1)),
            'comment': f'Servicio completado #{i+1}',
            'panas': random.choice(['excelente', 'bueno', 'regular']),
            'start': now,
            'end': now + datetime.timedelta(hours=random.randint(1, 8))
        }
        try:
            id_result = await db.insert_workflow_with_retry(workflow, user_id=200 + i)
            print(f"✅ SERVICIO #{i+1} guardado (ID: {id_result})")
        except Exception as e:
            print(f"❌ Error en SERVICIO #{i+1}: {e}")
    
    print("\n" + "="*50)
    print("✨ ¡Datos de prueba creados exitosamente!")
    print("="*50)
    print("\n📊 Ahora ejecuta: streamlit run dashboard.py")
    print("   Verás los gráficos y análisis de los workflows.\n")

if __name__ == '__main__':
    asyncio.run(create_test_data())
