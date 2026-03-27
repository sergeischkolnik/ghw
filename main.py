import logging
import json
import unicodedata
import asyncio
import db
import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler
import tempfile
import os
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# conversation states
TYPE_CHOICE, MACHINE_NAME, MACHINE_NUM, COMPONENT, SUBCOMPONENT, CHECKLIST, COMMENT_CHOICE, COMMENT_TEXT, PANAS_CHOICE, PANAS_TEXT, SERVICE_CLIENT_SEARCH, SERVICE_CLIENT_SELECT, SERVICE_SERVICE_SELECT, SERVICE_SUBSERVICE_SELECT, SERVICE_DETAIL_HILERAS, SERVICE_DETAIL_CARAS, SERVICE_DETAIL_PASADAS, SERVICE_HOROMETRO_INICIO, SERVICE_HOROMETRO_TERMINO, SERVICE_HECTAREAS, SERVICE_HOROMETRO_INICIO_CONFIRM, SERVICE_HOROMETRO_TERMINO_CONFIRM, SERVICE_HECTAREAS_CONFIRM, COMMENT_TEXT_CONFIRM, PANAS_TEXT_CONFIRM = range(25)

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    # Clear any existing workflow data to start fresh
    context.user_data.clear()
    
    # Directly start the workflow
    return await workflow_start(update, context)


async def export_workflows(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin command: export recent workflows. Usage: /export_workflows [taller|servicio|all] [limit]"""
    args = context.args or []
    typ = (args[0].lower() if len(args) >= 1 else 'all')
    limit = int(args[1]) if len(args) >= 2 and args[1].isdigit() else 50

    results = {}
    if typ in ('taller', 'all'):
        rows = await db.get_recent_taller_outputs(limit=limit)
        results['taller_outputs'] = rows
    if typ in ('servicio', 'all'):
        rows = await db.get_recent_servicio_outputs(limit=limit)
        results['servicio_outputs'] = rows

    # write to temp file and send as document
    import tempfile, io
    payload = json.dumps(results, ensure_ascii=False, indent=2, default=str)
    with tempfile.NamedTemporaryFile('w', delete=False, suffix='.json', encoding='utf-8') as tmp:
        tmp.write(payload)
        tmp_path = tmp.name

    try:
        if update.message:
            await update.message.reply_document(open(tmp_path, 'rb'))
        elif update.callback_query:
            await update.callback_query.message.reply_document(open(tmp_path, 'rb'))
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass


async def simulate_taller(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Insert a simulated TALLER workflow into the DB for quick testing."""
    now = datetime.datetime.now()
    workflow = {
        'type': 'TALLER',
        'machine_name': 'Shaker (sim)',
        'machine_num': '1',
        'component_id': 'CP001',
        'subcomponent_id': 'CS007',
        'selected_indices': [0],
        'current_items': ['Simulated task'],
        'comment': 'Simulated workflow',
        'panas': 'sim',
        'start': now,
        'end': now
    }
    try:
        new_id = await db.insert_workflow_with_retry(workflow, user_id=update.effective_user.id)
        await update.message.reply_text(f"Simulated TALLER saved (id={new_id})")
    except Exception as e:
        await update.message.reply_text(f"Simulation failed: {e}")


async def simulate_servicio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Insert a simulated SERVICIO workflow into the DB for quick testing."""
    now = datetime.datetime.now()
    client = (ALL_CLIENTS[0] if ALL_CLIENTS else 'SIM_CLIENT')
    workflow = {
        'type': 'SERVICIO',
        'client': client,
        'service': 'S_TEST',
        'subservice': 'SS_TEST',
        'details': {},
        'horometro_inicio': '0',
        'horometro_termino': '10',
        'hectareas': '1',
        'comment': 'Simulated servicio',
        'panas': 'sim',
        'start': now,
        'end': now
    }
    try:
        new_id = await db.insert_workflow_with_retry(workflow, user_id=update.effective_user.id)
        await update.message.reply_text(f"Simulated SERVICIO saved (id={new_id})")
    except Exception as e:
        await update.message.reply_text(f"Simulation failed: {e}")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming messages and reply with hello."""
    await update.message.reply_text("hello")


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and send a telegram message to notify the developer."""
    logger.error(msg="Exception while handling an update:", exc_info=context.error)


# --- workflow data -------------------------------------------------------------
MAIN_TYPES = ["TALLER", "SERVICIO"]

MACHINE_NAMES = ["Shaker", "Barredora", "Recogedora", "SBS Shaker", "SBS Recibidora", "Carro Estanque", "Camioncito", "Elevador"]

MACHINE_NUMBERS = {str(i): f"Máquina {i}" for i in range(1, 11)}

# Load component structure and clients preferring DB, fallback to JSON files
try:
    COMPONENTS_DATA = db.get_components_sync()
    if not COMPONENTS_DATA:
        with open('components.json', 'r', encoding='utf-8') as f:
            COMPONENTS_DATA = json.load(f)
except Exception:
    try:
        with open('components.json', 'r', encoding='utf-8') as f:
            COMPONENTS_DATA = json.load(f)
    except Exception:
        COMPONENTS_DATA = {'colecciones': []}

# Load clients preferring DB
try:
    ALL_CLIENTS = db.get_clients_sync() or []
    if not ALL_CLIENTS:
        with open('clients.json', 'r', encoding='utf-8') as f:
            CLIENTS_DATA = json.load(f)
            ALL_CLIENTS = CLIENTS_DATA.get('clients', [])
except Exception:
    try:
        with open('clients.json', 'r', encoding='utf-8') as f:
            CLIENTS_DATA = json.load(f)
            ALL_CLIENTS = CLIENTS_DATA.get('clients', [])
    except (FileNotFoundError, json.JSONDecodeError):
        ALL_CLIENTS = []
        logger.warning("Could not load clients.json, client search disabled")

# Load services from JSON
try:
    with open('services.json', 'r', encoding='utf-8') as f:
        SERVICES_DATA = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    SERVICES_DATA = {}
    logger.warning("Could not load services.json, service selection disabled")

# Build service lookup dictionaries (similar to components structure)
SERVICIOS_PRINCIPALES = {}  # id -> nombre
SERVICIOS_SECUNDARIOS = {}   # id -> {nombre, pertenece_a}
SERVICIOS_SECUNDARIOS_BY_PRINCIPAL = {}  # principal_id -> [secondary_ids]

for col in SERVICES_DATA.get('colecciones', []):
    if col['nombre'] == 'servicios_principales':
        for doc in col['documentos']:
            SERVICIOS_PRINCIPALES[doc['_id']] = doc['nombre']
            SERVICIOS_SECUNDARIOS_BY_PRINCIPAL[doc['_id']] = []
    elif col['nombre'] == 'servicios_secundarios':
        for doc in col['documentos']:
            SERVICIOS_SECUNDARIOS[doc['_id']] = {
                'nombre': doc['nombre'],
                'pertenece_a': doc.get('pertenece_a')
            }

# Build the reverse lookup for services
for secondary_id, secondary_data in SERVICIOS_SECUNDARIOS.items():
    principal_id = secondary_data['pertenece_a']
    if principal_id in SERVICIOS_SECUNDARIOS_BY_PRINCIPAL:
        SERVICIOS_SECUNDARIOS_BY_PRINCIPAL[principal_id].append(secondary_id)

# Build detail service lookup dictionaries
DETALLES_SERVICIOS = {}  # id -> {nombre, tipo, aplica_a, opciones}

for col in SERVICES_DATA.get('colecciones', []):
    if col['nombre'] == 'detalles_servicios':
        for doc in col['documentos']:
            DETALLES_SERVICIOS[doc['_id']] = {
                'nombre': doc['nombre'],
                'tipo': doc.get('tipo'),
                'aplica_a': doc.get('aplica_a', []),
                'opciones': doc.get('opciones', [])
            }

# Build lookup dictionaries
PRINCIPALES = {}  # id -> {nombre, tareas}
SECUNDARIOS = {}   # id -> {nombre, pertenece_a, tareas}
SECUNDARIOS_BY_PRINCIPAL = {}  # principal_id -> [secondary_ids]

for col in COMPONENTS_DATA['colecciones']:
    if col['nombre'] == 'componentes_principales':
        for doc in col['documentos']:
            PRINCIPALES[doc['_id']] = {
                'nombre': doc['nombre'],
                'tareas': doc.get('tareas', [])
            }
            SECUNDARIOS_BY_PRINCIPAL[doc['_id']] = []
    elif col['nombre'] == 'componentes_secundarios':
        for doc in col['documentos']:
            SECUNDARIOS[doc['_id']] = {
                'nombre': doc['nombre'],
                'pertenece_a': doc.get('pertenece_a'),
                'tareas': doc.get('tareas', [])
            }

# Build the reverse lookup
for secondary_id, secondary_data in SECUNDARIOS.items():
    principal_id = secondary_data['pertenece_a']
    if principal_id in SECUNDARIOS_BY_PRINCIPAL:
        SECUNDARIOS_BY_PRINCIPAL[principal_id].append(secondary_id)

COMPONENTS = {
    "MOTOR": [
        "Revisar Estado de Motor",
        "Revisar Alternador/Carga",
        "Revisar Bomba de agua",
        "Revisar Radiador fugas",
        "Revisar Mangueras del Radiador",
        "Revisar Bomba elevadora",
        "Revisar Portafiltros",
        "Limpieza de radiador",
        "Agua de radiador",
        "Enderezar panel del radiador",
        "Revisar y probar inyectores",
        "Revisar estado de correa de motor",
        "Revisar rodamientos de tensores y poleas",
        "Cambio de Filtros",
        "Cambio de aceite de motor",
        "Revisar estado de aspa del ventilador",
    ],
    "CILINDROS": [
        "Revisar fugas en el cilindro",
        "Revisar estado del vástago",
        "Revisar estado de las tapas",
        "Revisar estado del puño y orejas traseras",
        "Revisar pasador",
        "Revisar estado en toma de cilindro",
        "Revisar estado de la botella",
        "Revisar estado de los niples",
        "Revisar estado de los packing",
        "Cilindros de barredores",
        "Cilindros de carrillera tenaza",
        "Cilindros de levante de tenaza",
        "Cilindros de Flipper",
        "Cilindros de levante de equipo",
        "Cilindros de cuerpos de carpa",
        "Cilindro de bin",
        "Cilindros de dirección",
    ],
    "MANGUERAS": [
        "Revisar fugas en mangueras",
        "Revisar Apriete de mangueras",
        "Revisar O rings de mangueras",
        "Revisar Mangueras que puedan rozar",
        "Revisar y ordenar mangueras",
        "Revisar fugas en motorín",
    ],
    "BARREDORES": [
        "Revisar y enderezar platos",
        "Revisar y reparar dedos",
        "Revisar y reparar seguros de conos",
        "Revisar y reparar brazos de barredores",
    ],
    "CABLES": [
        "Revisar estado de cables y protección",
        "Revisar chanchitos",
    ],
    "BATERIA": [
        "Revisar corriente en Bateria",
        "Revisar carga de bateria",
        "Revisar bornes de bateria",
        "Revisar fijación de la batería",
        "Revisar cableado en la batería",
    ],
    "MASAS": [
        "Revisar estado de aceite de las masas",
        "Cambio de aceite de masa",
        "Revisar rodamiento",
        "Cambio de retén de masa",
        "Revisar fugas en motor de masa",
        "Revisar retorno del motor",
        "Revisar fugas y niples del motor de masa",
    ],
    "NEUMATICO": [
        "Revisar estado de los neumáticos",
        "Revisar llantas estado de los bordes",
        "Revisar estado de los pernos de rueda y tuercas",
        "Revisar estado de ojos de la llanta",
        "Revisar que los neumáticos sean los mismos",
    ],
    "CINTAS": [
        "Revisar estado de la cinta",
        "Revisar estado de la cadena de la cinta",
        "Revisar estado de las pletinas de la cinta",
        "Revisar pernos de la cinta",
        "Revisar estado de rodamientos de la cinta",
        "Revisar estado de ejes",
        "Revisar estado de piñones de tracción",
        "Revisar estado de guías en los ejes",
        "Revisar estado de piñones en los ejes",
        "Revisar fugas en motorines de las cintas",
        "Reparar fugas en motorines de las cintas",
        "Revisar niples y conecciones motorín",
    ],
    "SOPLADOR_HOJAS": [
        "Revisar rodamientos de tenaza",
        "Revisar puntos de engrase de la tenaza",
        "Revisar alineación de las correas",
        "Revisar rodamientos de poleas",
        "Revisar pernos de los tensores",
        "Revisar pasador trasero de tenaza",
        "Revisar pernos de cubiertas",
        "Revisar estado de cubiertas",
        "Revisar estado de cojinetes",
        "Revisar estado de teflones donde desliza la tenaza",
        "Revisar fugas del boak",
        "Revisar estado de donas",
        "Revisar estado de pernos y tuercas de donas",
        "Revisar estado de golillas",
        "Revisar estado de aspa del ventilador",
        "Revisar estado de rodamiento del ventilador",
        "Revisar estado de araña",
        "Revisar estado de acople de araña",
        "Revisar estado de motor del ventilador",
        "Revisar estado de teflones de deslizamiento",
        "Revisar estado de tapa de teflones",
        "Cambio de teflones malos",
        "Reparar tapas en mal estado",
    ],
    "ELECTRICIDAD": [
        "Revisar corriente en Chapa",
        "Revisar corriente en motor",
        "Revisar corriente en electrovalvulas",
        "Revisar corriente en alternador",
        "Revisar corriente en sensores del motor",
    ],
    "TEFLON": [
        "Revisar teflones de las cintas",
        "Estirar teflones de las cintas",
    ],
    "PRESIONES": [
        "Revisar presiones de bomba de pistones",
        "Revisar flujo bomba de paletas",
        "Revisar presiones de husco 3000",
        "Revisar presiones de manillar",
    ],
    "JOYSTICK": [
        "Revisar fugas de Joystick",
        "Revisar señales eléctricas",
        "Revisar botones buenos y malos",
        "Ordenar botones",
    ],
    "LUCES": [
        "Revisar estado de focos",
        "Revisar cableado de luces",
        "Hacer protecciones para luces",
        "Reparar luces mal puestas",
    ],
    "ACEITE_HIDRAULICO": [
        "Revisar tapa de aceite",
        "Revisar tapa de estanque de petróleo",
        "Revisar/instalar tapa de protección de aceite",
        "Revisar/instalar tapa de protección de petróleo",
        "Revisar estado de aceite hidráulico",
        "Dializar aceite/Cambiar aceite",
        "Rellenar aceite hidráulico",
        "Limpieza de estanque con imán",
        "Limpieza de estanque por la toma de petroleo",
    ],
    "GOMAS": [
        "Revisar gomas laterales con cada cuerpo",
        "Revisar gomas de flipper",
        "Revisar/Cambiar pletinas flipper",
        "Revisar gomas radiador",
    ],
    "TENAZA": [
        "Revisar fisuras",
    ],
    "REPARACIONES": [
        "(Se registran fisuras encontradas)",
    ],
    "PROTECCIONES": [
        "Revisar estado de protecciones",
        "Reparar protecciones dañadas",
    ],
}

CHECKLISTS = {
    "MOTOR": [
        "Revisar Estado de Motor",
        "Revisar Alternador/Carga",
        "Revisar Bomba de agua",
        "Revisar Radiador fugas",
        "Revisar Mangueras del Radiador",
        "Revisar Bomba elevadora",
        "Revisar Portafiltros",
        "Limpieza de radiador",
        "Agua de radiador",
        "Enderezar panel del radiador",
        "Revisar y probar inyectores",
        "Revisar estado de correa de motor",
        "Revisar rodamientos de tensores y poleas",
        "Cambio de Filtros",
        "Cambio de aceite de motor",
        "Revisar estado de aspa del ventilador",
    ],
    "CILINDROS": [
        "Revisar fugas en el cilindro",
        "Revisar estado del vástago",
        "Revisar estado de las tapas",
        "Revisar estado del puño y orejas traseras",
        "Revisar pasador",
        "Revisar estado en toma de cilindro",
        "Revisar estado de la botella",
        "Revisar estado de los niples",
        "Revisar estado de los packing",
        "Cilindros de barredores",
        "Cilindros de carrillera tenaza",
        "Cilindros de levante de tenaza",
        "Cilindros de Flipper",
        "Cilindros de levante de equipo",
        "Cilindros de cuerpos de carpa",
        "Cilindro de bin",
        "Cilindros de dirección",
    ],
    "MANGUERAS": [
        "Revisar fugas en mangueras",
        "Revisar Apriete de mangueras",
        "Revisar O rings de mangueras",
        "Revisar Mangueras que puedan rozar",
        "Revisar y ordenar mangueras",
        "Revisar fugas en motorín",
    ],
    "BARREDORES": [
        "Revisar y enderezar platos",
        "Revisar y reparar dedos",
        "Revisar y reparar seguros de conos",
        "Revisar y reparar brazos de barredores",
    ],
    "CABLES": [
        "Revisar estado de cables y protección",
        "Revisar chanchitos",
    ],
    "BATERIA": [
        "Revisar corriente en Bateria",
        "Revisar carga de bateria",
        "Revisar bornes de bateria",
        "Revisar fijación de la batería",
        "Revisar cableado en la batería",
    ],
    "MASAS": [
        "Revisar estado de aceite de las masas",
        "Cambio de aceite de masa",
        "Revisar rodamiento",
        "Cambio de retén de masa",
        "Revisar fugas en motor de masa",
        "Revisar retorno del motor",
        "Revisar fugas y niples del motor de masa",
    ],
    "NEUMATICO": [
        "Revisar estado de los neumáticos",
        "Revisar llantas estado de los bordes",
        "Revisar estado de los pernos de rueda y tuercas",
        "Revisar estado de ojos de la llanta",
        "Revisar que los neumáticos sean los mismos",
    ],
    "CINTAS": [
        "Revisar estado de la cinta",
        "Revisar estado de la cadena de la cinta",
        "Revisar estado de las pletinas de la cinta",
        "Revisar pernos de la cinta",
        "Revisar estado de rodamientos de la cinta",
        "Revisar estado de ejes",
        "Revisar estado de piñones de tracción",
        "Revisar estado de guías en los ejes",
        "Revisar estado de piñones en los ejes",
        "Revisar fugas en motorines de las cintas",
        "Reparar fugas en motorines de las cintas",
        "Revisar niples y conecciones motorín",
    ],
    "SOPLADOR_HOJAS": [
        "Revisar rodamientos de tenaza",
        "Revisar puntos de engrase de la tenaza",
        "Revisar alineación de las correas",
        "Revisar rodamientos de poleas",
        "Revisar pernos de los tensores",
        "Revisar pasador trasero de tenaza",
        "Revisar pernos de cubiertas",
        "Revisar estado de cubiertas",
        "Revisar estado de cojinetes",
        "Revisar estado de teflones donde desliza la tenaza",
        "Revisar fugas del boak",
        "Revisar estado de donas",
        "Revisar estado de pernos y tuercas de donas",
        "Revisar estado de golillas",
        "Revisar estado de aspa del ventilador",
        "Revisar estado de rodamiento del ventilador",
        "Revisar estado de araña",
        "Revisar estado de acople de araña",
        "Revisar estado de motor del ventilador",
        "Revisar estado de teflones de deslizamiento",
        "Revisar estado de tapa de teflones",
        "Cambio de teflones malos",
        "Reparar tapas en mal estado",
    ],
    "ELECTRICIDAD": [
        "Revisar corriente en Chapa",
        "Revisar corriente en motor",
        "Revisar corriente en electrovalvulas",
        "Revisar corriente en alternador",
        "Revisar corriente en sensores del motor",
    ],
    "TEFLON": [
        "Revisar teflones de las cintas",
        "Estirar teflones de las cintas",
    ],
    "PRESIONES": [
        "Revisar presiones de bomba de pistones",
        "Revisar flujo bomba de paletas",
        "Revisar presiones de husco 3000",
        "Revisar presiones de manillar",
    ],
    "JOYSTICK": [
        "Revisar fugas de Joystick",
        "Revisar señales eléctricas",
        "Revisar botones buenos y malos",
        "Ordenar botones",
    ],
    "LUCES": [
        "Revisar estado de focos",
        "Revisar cableado de luces",
        "Hacer protecciones para luces",
        "Reparar luces mal puestas",
    ],
    "ACEITE_HIDRAULICO": [
        "Revisar tapa de aceite",
        "Revisar tapa de estanque de petróleo",
        "Revisar/instalar tapa de protección de aceite",
        "Revisar/instalar tapa de protección de petróleo",
        "Revisar estado de aceite hidráulico",
        "Dializar aceite/Cambiar aceite",
        "Rellenar aceite hidráulico",
        "Limpieza de estanque con imán",
        "Limpieza de estanque por la toma de petroleo",
    ],
    "GOMAS": [
        "Revisar gomas laterales con cada cuerpo",
        "Revisar gomas de flipper",
        "Revisar/Cambiar pletinas flipper",
        "Revisar gomas radiador",
    ],
    "TENAZA": [
        "Revisar fisuras",
    ],
}


def normalize_text(text):
    """Normalize text: remove accents and convert to lowercase."""
    nfd = unicodedata.normalize('NFD', text)
    return ''.join(c for c in nfd if unicodedata.category(c) != 'Mn').lower()


def build_keyboard(options, row_width=1):
    """Utility to construct inline keyboard from list of strings."""
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(opt, callback_data=opt)] for opt in options]
    )


async def workflow_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry point for the workflow conversation."""
    context.user_data['workflow'] = {
        'type': None,
        'machine': None,
        'component': None,
        'subpart': None,
        'checklist_items': [],
        'start': None,
        'end': None,
        'comment': None,
        'panas': None,
        'selected_indices': set(),
    }
    context.user_data['workflow']['start'] = __import__('datetime').datetime.now()

    keyboard = [[InlineKeyboardButton(t, callback_data=f"type|{t}")] for t in MAIN_TYPES]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text("Seleccione tipo de trabajo:", reply_markup=reply_markup)
    else:
        await update.message.reply_text("Seleccione tipo de trabajo:", reply_markup=reply_markup)
    return TYPE_CHOICE


async def type_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User selected TALLER or SERVICIO."""
    query = update.callback_query
    await query.answer()
    typ = query.data.replace("type|", "")
    context.user_data['workflow']['type'] = typ

    if typ == "TALLER":
        # Ask for machine name selection
        buttons = [[InlineKeyboardButton(name, callback_data=f"machine_name|{name}")] for name in MACHINE_NAMES]
        buttons.append([InlineKeyboardButton("◀ Atrás", callback_data="back|TYPE_CHOICE")])
        await query.edit_message_text("Seleccione máquina:", reply_markup=InlineKeyboardMarkup(buttons))
        return MACHINE_NAME
    else:
        # SERVICIO - search for client
        kb = [[InlineKeyboardButton("◀ Atrás", callback_data="back|TYPE_CHOICE")]]
        await query.edit_message_text("Ingrese nombre del cliente (o parte del nombre):", reply_markup=InlineKeyboardMarkup(kb))
        return SERVICE_CLIENT_SEARCH


async def service_client_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive client search text and show matching results."""
    search_text = update.message.text.strip()
    context.user_data['search_text'] = search_text
    
    # Normalize search text (remove accents, lowercase)
    normalized_search = normalize_text(search_text)
    
    # Filter clients that match the search (case-insensitive, accent-insensitive)
    matches = [client for client in ALL_CLIENTS if normalized_search in normalize_text(client)]
    
    if not matches:
        await update.message.reply_text("❌ No se encontraron clientes. Intente de nuevo:")
        return SERVICE_CLIENT_SEARCH
    
    # Store matches and show first page
    context.user_data['client_matches'] = matches
    context.user_data['client_page'] = 0
    
    return await show_client_page(update, context)


async def show_client_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display a page of client results (max 5 per page)."""
    matches = context.user_data.get('client_matches', [])
    page = context.user_data.get('client_page', 0)
    
    PAGE_SIZE = 5
    start_idx = page * PAGE_SIZE
    end_idx = start_idx + PAGE_SIZE
    
    page_clients = matches[start_idx:end_idx]
    total_pages = (len(matches) + PAGE_SIZE - 1) // PAGE_SIZE
    
    # Build buttons for this page
    buttons = []
    for i, client in enumerate(page_clients):
        callback_idx = start_idx + i
        display_num = start_idx + i + 1  # Correlative numbering across pages
        buttons.append([InlineKeyboardButton(f"{display_num}. {client}", callback_data=f"service_client|{callback_idx}")])
    
    # Navigation buttons
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("◀ Anterior", callback_data="service_client_prev"))
    if end_idx < len(matches):
        nav_buttons.append(InlineKeyboardButton("Siguiente ▶", callback_data="service_client_next"))
    if nav_buttons:
        buttons.append(nav_buttons)
    
    buttons.append([InlineKeyboardButton("◀ Atrás", callback_data="back|SERVICE_CLIENT_SEARCH")])
    
    message = f"Resultados: {len(matches)} clientes encontrados\nPágina {page + 1} de {total_pages}\n\nSeleccione uno:"
    
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(buttons))
    else:
        await update.message.reply_text(message, reply_markup=InlineKeyboardMarkup(buttons))
    
    return SERVICE_CLIENT_SELECT


async def service_client_pagination(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle pagination through client results."""
    query = update.callback_query
    await query.answer()
    
    page = context.user_data.get('client_page', 0)
    matches = context.user_data.get('client_matches', [])
    PAGE_SIZE = 5
    
    if query.data == "service_client_prev" and page > 0:
        context.user_data['client_page'] = page - 1
    elif query.data == "service_client_next":
        total_pages = (len(matches) + PAGE_SIZE - 1) // PAGE_SIZE
        if page < total_pages - 1:
            context.user_data['client_page'] = page + 1
    
    return await show_client_page(update, context)


async def service_client_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User selected a client."""
    query = update.callback_query
    await query.answer()
    
    client_idx = int(query.data.replace("service_client|", ""))
    matches = context.user_data.get('client_matches', [])
    
    if client_idx < len(matches):
        selected_client = matches[client_idx]
        context.user_data['workflow']['client'] = selected_client
        
        # Continue to service selection
        return await show_service_options(query, context)
    
    return SERVICE_CLIENT_SELECT


async def show_service_options(query, context: ContextTypes.DEFAULT_TYPE):
    """Show available principal service options."""
    buttons = [[InlineKeyboardButton(
        SERVICIOS_PRINCIPALES[service_id], 
        callback_data=f"service_select|{service_id}"
    )] for service_id in SERVICIOS_PRINCIPALES.keys()]
    buttons.append([InlineKeyboardButton("◀ Atrás", callback_data="back|SERVICE_CLIENT_SELECT")])
    
    client = context.user_data['workflow'].get('client', 'N/A')
    message = f"Cliente: {client}\n\nSeleccione tipo de servicio:"
    
    await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(buttons))
    return SERVICE_SERVICE_SELECT


async def service_service_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User selected a principal service type."""
    query = update.callback_query
    await query.answer()
    
    service_id = query.data.replace("service_select|", "")
    context.user_data['workflow']['service'] = service_id
    
    # Find service name for display
    service_name = SERVICIOS_PRINCIPALES.get(service_id, service_id)
    
    # Check if this service has subservices
    subservices = SERVICIOS_SECUNDARIOS_BY_PRINCIPAL.get(service_id, [])
    
    if subservices:
        # Show subservice options
        buttons = [[InlineKeyboardButton(
            SERVICIOS_SECUNDARIOS[sub_id]['nombre'], 
            callback_data=f"subservice_select|{sub_id}"
        )] for sub_id in subservices]
        buttons.append([InlineKeyboardButton("◀ Atrás", callback_data="back|SERVICE_SERVICE_SELECT")])
        
        client = context.user_data['workflow'].get('client', 'N/A')
        message = f"Cliente: {client}\nServicio: {service_name}\n\nSeleccione opción:"
        
        await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(buttons))
        return SERVICE_SUBSERVICE_SELECT
    else:
        # No subservices, continue to comments
        kb = [[InlineKeyboardButton("Sí", callback_data="comments_yes"), InlineKeyboardButton("No", callback_data="comments_no")]]
        kb.append([InlineKeyboardButton("◀ Atrás", callback_data="back|SERVICE_SERVICE_SELECT")])
        
        client = context.user_data['workflow'].get('client', 'N/A')
        await query.edit_message_text(f"Cliente: {client}\nServicio: {service_name}\n\n¿Comentarios?", reply_markup=InlineKeyboardMarkup(kb))
        return COMMENT_CHOICE


async def service_subservice_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User selected a subservice option."""
    query = update.callback_query
    await query.answer()
    
    subservice_id = query.data.replace("subservice_select|", "")
    context.user_data['workflow']['subservice'] = subservice_id
    
    # Find service and subservice names for display
    subservice_data = SERVICIOS_SECUNDARIOS.get(subservice_id, {})
    subservice_name = subservice_data.get('nombre', subservice_id)
    service_id = context.user_data['workflow'].get('service', '')
    service_name = SERVICIOS_PRINCIPALES.get(service_id, service_id)
    
    # Check if this subservice has details (only for Podadora/PODA)
    applicable_details = [d for d in DETALLES_SERVICIOS.values() if subservice_id in d.get('aplica_a', [])]
    
    if applicable_details:
        # Show first detail (Hileras)
        context.user_data['workflow']['details'] = {}
        return await show_service_detail_hileras(query, context, subservice_name, service_name)
    else:
        # No subservices, continue to Horómetro Inicio
        kb = [[InlineKeyboardButton("◀ Atrás", callback_data="back|SERVICE_SERVICE_SELECT")]]
        client = context.user_data['workflow'].get('client', 'N/A')
        message = f"Cliente: {client}\nServicio: {service_name}\n\nHorómetro de Inicio:"
        
        await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(kb))
        return SERVICE_HOROMETRO_INICIO


async def show_service_detail_hileras(query, context: ContextTypes.DEFAULT_TYPE, subservice_name: str, service_name: str):
    """Show Hileras detail options."""
    detail = DETALLES_SERVICIOS.get('D01', {})
    opciones = detail.get('opciones', [])
    
    buttons = [[InlineKeyboardButton(opt['nombre'], callback_data=f"detail_hileras|{opt['_id']}")] for opt in opciones]
    buttons.append([InlineKeyboardButton("◀ Atrás", callback_data="back|SERVICE_SUBSERVICE_SELECT")])
    
    client = context.user_data['workflow'].get('client', 'N/A')
    message = f"Cliente: {client}\nServicio: {service_name}\nOpción: {subservice_name}\n\n{detail.get('nombre', 'Hileras')}:"
    
    await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(buttons))
    return SERVICE_DETAIL_HILERAS


async def detail_hileras_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User selected Hileras detail."""
    query = update.callback_query
    await query.answer()
    
    hileras_id = query.data.replace("detail_hileras|", "")
    context.user_data['workflow']['details']['hileras'] = hileras_id
    
    # Find selected option name
    detail = DETALLES_SERVICIOS.get('D01', {})
    hileras_name = next((opt['nombre'] for opt in detail.get('opciones', []) if opt['_id'] == hileras_id), hileras_id)
    
    # Show Caras detail
    return await show_service_detail_caras(query, context, hileras_name)


async def show_service_detail_caras(query, context: ContextTypes.DEFAULT_TYPE, hileras_name: str):
    """Show Caras detail options."""
    detail = DETALLES_SERVICIOS.get('D02', {})
    opciones = detail.get('opciones', [])
    
    buttons = [[InlineKeyboardButton(opt['nombre'], callback_data=f"detail_caras|{opt['_id']}")] for opt in opciones]
    buttons.append([InlineKeyboardButton("◀ Atrás", callback_data="back|SERVICE_DETAIL_HILERAS")])
    
    client = context.user_data['workflow'].get('client', 'N/A')
    subservice_name = SERVICIOS_SECUNDARIOS.get(context.user_data['workflow'].get('subservice', ''), {}).get('nombre', '')
    service_name = SERVICIOS_PRINCIPALES.get(context.user_data['workflow'].get('service', ''), '')
    message = f"Cliente: {client}\nServicio: {service_name}\nOpción: {subservice_name}\nHileras: {hileras_name}\n\n{detail.get('nombre', 'Caras')}:"
    
    await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(buttons))
    return SERVICE_DETAIL_CARAS


async def detail_caras_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User selected Caras detail."""
    query = update.callback_query
    await query.answer()
    
    caras_id = query.data.replace("detail_caras|", "")
    context.user_data['workflow']['details']['caras'] = caras_id
    
    # Find selected option name
    detail = DETALLES_SERVICIOS.get('D02', {})
    caras_name = next((opt['nombre'] for opt in detail.get('opciones', []) if opt['_id'] == caras_id), caras_id)
    
    # Show Pasadas detail
    return await show_service_detail_pasadas(query, context, caras_name)


async def show_service_detail_pasadas(query, context: ContextTypes.DEFAULT_TYPE, caras_name: str):
    """Show Pasadas detail options."""
    detail = DETALLES_SERVICIOS.get('D03', {})
    opciones = detail.get('opciones', [])
    
    buttons = [[InlineKeyboardButton(opt['nombre'], callback_data=f"detail_pasadas|{opt['_id']}")] for opt in opciones]
    buttons.append([InlineKeyboardButton("◀ Atrás", callback_data="back|SERVICE_DETAIL_CARAS")])
    
    client = context.user_data['workflow'].get('client', 'N/A')
    subservice_name = SERVICIOS_SECUNDARIOS.get(context.user_data['workflow'].get('subservice', ''), {}).get('nombre', '')
    service_name = SERVICIOS_PRINCIPALES.get(context.user_data['workflow'].get('service', ''), '')
    hileras_id = context.user_data['workflow'].get('details', {}).get('hileras', '')
    hileras_detail = DETALLES_SERVICIOS.get('D01', {})
    hileras_name = next((opt['nombre'] for opt in hileras_detail.get('opciones', []) if opt['_id'] == hileras_id), '')
    
    message = f"Cliente: {client}\nServicio: {service_name}\nOpción: {subservice_name}\nHileras: {hileras_name}\nCaras: {caras_name}\n\n{detail.get('nombre', 'Pasadas')}:"
    
    await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(buttons))
    return SERVICE_DETAIL_PASADAS


async def detail_pasadas_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User selected Pasadas detail."""
    query = update.callback_query
    await query.answer()
    
    pasadas_id = query.data.replace("detail_pasadas|", "")
    context.user_data['workflow']['details']['pasadas'] = pasadas_id
    
    # Continue to Horómetro Inicio
    kb = [[InlineKeyboardButton("◀ Atrás", callback_data="back|SERVICE_HOROMETRO_INICIO")]]
    
    client = context.user_data['workflow'].get('client', 'N/A')
    subservice_name = SERVICIOS_SECUNDARIOS.get(context.user_data['workflow'].get('subservice', ''), {}).get('nombre', '')
    service_name = SERVICIOS_PRINCIPALES.get(context.user_data['workflow'].get('service', ''), '')
    
    message = f"Cliente: {client}\nServicio: {service_name}\nOpción: {subservice_name}\n\nHorómetro de Inicio:"
    
    await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(kb))
    return SERVICE_HOROMETRO_INICIO


async def machine_name_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User selected machine name."""
    query = update.callback_query
    await query.answer()
    machine_name = query.data.replace("machine_name|", "")
    context.user_data['workflow']['machine_name'] = machine_name

    # Ask for machine number
    buttons = [[InlineKeyboardButton(f"{k}", callback_data=f"machine_num|{k}")] for k in MACHINE_NUMBERS.keys()]
    buttons.append([InlineKeyboardButton("◀ Atrás", callback_data="back|MACHINE_NAME")])
    await query.edit_message_text(f"Máquina: {machine_name}\nSeleccione número:", reply_markup=InlineKeyboardMarkup(buttons))
    return MACHINE_NUM


async def machine_num_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User selected machine number."""
    query = update.callback_query
    await query.answer()
    machine_num = query.data.replace("machine_num|", "")
    context.user_data['workflow']['machine_num'] = machine_num

    # Ask for component (main blue boxes)
    buttons = [[InlineKeyboardButton(PRINCIPALES[pid]['nombre'], callback_data=f"component|{pid}")] for pid in sorted(PRINCIPALES.keys())]
    buttons.append([InlineKeyboardButton("◀ Atrás", callback_data="back|MACHINE_NUM")])
    await query.edit_message_text(f"Máquina: {context.user_data['workflow']['machine_name']} {machine_num}\nSeleccione componente:", reply_markup=InlineKeyboardMarkup(buttons))
    return COMPONENT


async def machine_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Legacy - not used anymore."""
    pass


async def component_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User selected a component (main blue box)."""
    query = update.callback_query
    await query.answer()
    principal_id = query.data.replace("component|", "")
    context.user_data['workflow']['component_id'] = principal_id

    # Check if this component has sub-components
    sub_ids = SECUNDARIOS_BY_PRINCIPAL.get(principal_id, [])
    
    if sub_ids:
        # Has sub-components -> show them
        buttons = [[InlineKeyboardButton(SECUNDARIOS[sid]['nombre'], callback_data=f"subcomponent|{sid}")] for sid in sub_ids]
        buttons.append([InlineKeyboardButton("◀ Atrás", callback_data="back|COMPONENT")])
        principal_name = PRINCIPALES[principal_id]['nombre']
        await query.edit_message_text(f"Componente: {principal_name}\nSeleccione sub-componente:", reply_markup=InlineKeyboardMarkup(buttons))
        return SUBCOMPONENT
    else:
        # No sub-components -> show tasks directly
        items = PRINCIPALES[principal_id].get('tareas', [])
        if not items:
            items = ["(Sin items disponibles)"]
        
        context.user_data['workflow']['selected_indices'] = set()
        context.user_data['workflow']['current_items'] = items
        
        buttons = []
        for idx, item in enumerate(items):
            buttons.append([InlineKeyboardButton(f"☐ {item}", callback_data=f"toggle|{idx}")])
        buttons.append([InlineKeyboardButton("Finalizar", callback_data="done_checklist"), InlineKeyboardButton("◀ Atrás", callback_data="back|COMPONENT")])
        
        principal_name = PRINCIPALES[principal_id]['nombre']
        await query.edit_message_text(
            f"Componente: {principal_name}\nSeleccione items:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return CHECKLIST


async def subcomponent_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User selected a sub-component (yellow box) and now see the checklist."""
    query = update.callback_query
    await query.answer()
    secondary_id = query.data.replace("subcomponent|", "")
    context.user_data['workflow']['subcomponent_id'] = secondary_id

    # Get items from secondary component
    items = SECUNDARIOS[secondary_id].get('tareas', [])
    
    if not items:
        items = ["(Sin items disponibles)"]
    
    # Initialize selection tracking
    context.user_data['workflow']['selected_indices'] = set()
    context.user_data['workflow']['current_items'] = items
    
    # Show checklist with toggles
    buttons = []
    for idx, item in enumerate(items):
        buttons.append([InlineKeyboardButton(f"☐ {item}", callback_data=f"toggle|{idx}")])
    buttons.append([InlineKeyboardButton("Finalizar", callback_data="done_checklist"), InlineKeyboardButton("◀ Atrás", callback_data="back|SUBCOMPONENT")])
    
    subcomp_name = SECUNDARIOS[secondary_id]['nombre']
    await query.edit_message_text(
        f"Sub-componente: {subcomp_name}\nSeleccione items:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    return CHECKLIST


async def toggle_checklist_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggle a checklist item selection."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "done_checklist":
        # Move to comments
        context.user_data['workflow']['end'] = __import__('datetime').datetime.now()
        kb = [[InlineKeyboardButton("Sí", callback_data="comments_yes"), InlineKeyboardButton("No", callback_data="comments_no")]]
        kb.append([InlineKeyboardButton("◀ Atrás", callback_data="back|CHECKLIST")])
        await query.edit_message_text("¿Comentarios?", reply_markup=InlineKeyboardMarkup(kb))
        return COMMENT_CHOICE
    
    idx = int(query.data.replace("toggle|", ""))
    selected = context.user_data['workflow']['selected_indices']
    
    if idx in selected:
        selected.remove(idx)
    else:
        selected.add(idx)
    
    # Redraw checklist
    items = context.user_data['workflow']['current_items']
    
    buttons = []
    for i, item in enumerate(items):
        check = "☑" if i in selected else "☐"
        buttons.append([InlineKeyboardButton(f"{check} {item}", callback_data=f"toggle|{i}")])
    buttons.append([InlineKeyboardButton("Finalizar", callback_data="done_checklist"), InlineKeyboardButton("◀ Atrás", callback_data="back|CHECKLIST")])
    
    # Get current subcomponent/component name for display
    subcomp_id = context.user_data['workflow'].get('subcomponent_id')
    comp_id = context.user_data['workflow'].get('component_id')
    
    if subcomp_id:
        title = f"Sub-componente: {SECUNDARIOS[subcomp_id]['nombre']}"
    else:
        title = f"Componente: {PRINCIPALES[comp_id]['nombre']}"
    
    await query.edit_message_text(
        f"{title}\nSeleccione items:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    return CHECKLIST


async def comment_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle comment yes/no choice."""
    query = update.callback_query
    await query.answer()
    if query.data == "comments_yes":
        kb = [[InlineKeyboardButton("◀ Atrás", callback_data="back|COMMENT_CHOICE")]]
        await query.edit_message_text("Ingrese su comentario:", reply_markup=InlineKeyboardMarkup(kb))
        return COMMENT_TEXT
    else:
        return await ask_panas(query, context)


async def receive_comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive comment text and show confirmation."""
    comment_value = update.message.text.strip()
    context.user_data['workflow']['comment_temp'] = comment_value
    
    # Show confirmation with buttons
    kb = [
        [InlineKeyboardButton("✓ Confirmar", callback_data="confirm_comment"),
         InlineKeyboardButton("◀ Atrás", callback_data="back|COMMENT_CHOICE")]
    ]
    await update.message.reply_text(
        f"Comentario: {comment_value}\n\n¿Confirmar?",
        reply_markup=InlineKeyboardMarkup(kb)
    )
    return COMMENT_TEXT_CONFIRM


async def ask_panas(query, context: ContextTypes.DEFAULT_TYPE, message=None):
    """Ask about PANAS."""
    kb = [[InlineKeyboardButton("Sí", callback_data="panas_yes"), InlineKeyboardButton("No", callback_data="panas_no")]]
    kb.append([InlineKeyboardButton("◀ Atrás", callback_data="back|COMMENT_CHOICE")])
    if query:
        await query.edit_message_text("¿PANAS?", reply_markup=InlineKeyboardMarkup(kb))
    else:
        await message.reply_text("¿PANAS?", reply_markup=InlineKeyboardMarkup(kb))
    return PANAS_CHOICE


async def panas_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle PANAS yes/no choice."""
    query = update.callback_query
    await query.answer()
    if query.data == "panas_yes":
        kb = [[InlineKeyboardButton("◀ Atrás", callback_data="back|PANAS_CHOICE")]]
        await query.edit_message_text("Ingrese detalle de PANAS:", reply_markup=InlineKeyboardMarkup(kb))
        return PANAS_TEXT
    else:
        # No PANAS, finish workflow
        return await finish_workflow(query, context)


async def show_horometro_inicio(query, context: ContextTypes.DEFAULT_TYPE):
    """Show Horómetro de Inicio question."""
    kb = [[InlineKeyboardButton("◀ Atrás", callback_data="back|SERVICE_HOROMETRO_INICIO")]]
    if query:
        await query.edit_message_text("Horómetro de Inicio:", reply_markup=InlineKeyboardMarkup(kb))
    return SERVICE_HOROMETRO_INICIO


async def receive_panas_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive PANAS text and show confirmation."""
    panas_value = update.message.text.strip()
    context.user_data['workflow']['panas_temp'] = panas_value
    
    # Show confirmation with buttons
    kb = [
        [InlineKeyboardButton("✓ Confirmar", callback_data="confirm_panas"),
         InlineKeyboardButton("◀ Atrás", callback_data="back|PANAS_CHOICE")]
    ]
    await update.message.reply_text(
        f"PANAS: {panas_value}\n\n¿Confirmar?",
        reply_markup=InlineKeyboardMarkup(kb)
    )
    return PANAS_TEXT_CONFIRM


async def receive_horometro_inicio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive Horómetro de Inicio and show confirmation."""
    horometro_value = update.message.text.strip()
    context.user_data['workflow']['horometro_inicio_temp'] = horometro_value
    
    # Show confirmation with buttons
    kb = [
        [InlineKeyboardButton("✓ Confirmar", callback_data="confirm_horometro_inicio"),
         InlineKeyboardButton("◀ Atrás", callback_data="back|SERVICE_DETAIL_PASADAS")]
    ]
    await update.message.reply_text(
        f"Horómetro de Inicio: {horometro_value}\n\n¿Confirmar?",
        reply_markup=InlineKeyboardMarkup(kb)
    )
    return SERVICE_HOROMETRO_INICIO_CONFIRM


async def receive_horometro_termino(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive Horómetro de Término and show confirmation."""
    horometro_value = update.message.text.strip()
    context.user_data['workflow']['horometro_termino_temp'] = horometro_value
    
    # Show confirmation with buttons
    kb = [
        [InlineKeyboardButton("✓ Confirmar", callback_data="confirm_horometro_termino"),
         InlineKeyboardButton("◀ Atrás", callback_data="back|SERVICE_HOROMETRO_INICIO_CONFIRM")]
    ]
    await update.message.reply_text(
        f"Horómetro de Término: {horometro_value}\n\n¿Confirmar?",
        reply_markup=InlineKeyboardMarkup(kb)
    )
    return SERVICE_HOROMETRO_TERMINO_CONFIRM


async def receive_hectareas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive Hectáreas and show confirmation."""
    hectareas_value = update.message.text.strip()
    context.user_data['workflow']['hectareas_temp'] = hectareas_value
    
    # Show confirmation with buttons
    kb = [
        [InlineKeyboardButton("✓ Confirmar", callback_data="confirm_hectareas"),
         InlineKeyboardButton("◀ Atrás", callback_data="back|SERVICE_HOROMETRO_TERMINO_CONFIRM")]
    ]
    await update.message.reply_text(
        f"Cantidad de Hectáreas: {hectareas_value}\n\n¿Confirmar?",
        reply_markup=InlineKeyboardMarkup(kb)
    )
    return SERVICE_HECTAREAS_CONFIRM


async def confirm_horometro_inicio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirm Horómetro Inicio and continue to Horómetro Término."""
    query = update.callback_query
    await query.answer()
    
    # Guardar el valor confirmado
    horometro_value = context.user_data['workflow'].get('horometro_inicio_temp', '')
    context.user_data['workflow']['horometro_inicio'] = horometro_value
    
    # Continuar a Horómetro Término
    kb = [[InlineKeyboardButton("◀ Atrás", callback_data="back|SERVICE_HOROMETRO_INICIO_CONFIRM")]]
    await query.edit_message_text("Horómetro de Término:", reply_markup=InlineKeyboardMarkup(kb))
    return SERVICE_HOROMETRO_TERMINO


async def confirm_horometro_termino(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirm Horómetro Término and continue to Hectáreas."""
    query = update.callback_query
    await query.answer()
    
    # Guardar el valor confirmado
    horometro_value = context.user_data['workflow'].get('horometro_termino_temp', '')
    context.user_data['workflow']['horometro_termino'] = horometro_value
    
    # Continuar a Hectáreas
    kb = [[InlineKeyboardButton("◀ Atrás", callback_data="back|SERVICE_HOROMETRO_TERMINO_CONFIRM")]]
    await query.edit_message_text("Cantidad de Hectáreas:", reply_markup=InlineKeyboardMarkup(kb))
    return SERVICE_HECTAREAS


async def confirm_hectareas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirm Hectáreas and continue to Comments."""
    query = update.callback_query
    await query.answer()
    
    # Guardar el valor confirmado
    hectareas_value = context.user_data['workflow'].get('hectareas_temp', '')
    context.user_data['workflow']['hectareas'] = hectareas_value
    
    # Continuar a Comentarios
    kb = [[InlineKeyboardButton("Sí", callback_data="comments_yes"), InlineKeyboardButton("No", callback_data="comments_no")]]
    kb.append([InlineKeyboardButton("◀ Atrás", callback_data="back|SERVICE_HECTAREAS_CONFIRM")])
    await query.edit_message_text("¿Desea agregar un comentario?", reply_markup=InlineKeyboardMarkup(kb))
    return COMMENT_CHOICE


async def confirm_comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirm comment and continue to PANAS."""
    query = update.callback_query
    await query.answer()
    
    # Guardar el valor confirmado
    comment_value = context.user_data['workflow'].get('comment_temp', '')
    context.user_data['workflow']['comment'] = comment_value
    
    # Continuar a PANAS
    return await ask_panas(query, context)


async def confirm_panas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirm PANAS and finish workflow."""
    query = update.callback_query
    await query.answer()
    
    # Guardar el valor confirmado
    panas_value = context.user_data['workflow'].get('panas_temp', '')
    context.user_data['workflow']['panas'] = panas_value
    
    # Terminar el workflow
    return await finish_workflow(query, context)


async def back_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle back button navigation."""
    query = update.callback_query
    await query.answer()
    
    # Parse which state to go back to
    target_state = query.data.split("|")[1]
    
    # Navigate back based on target state - redraw the previous menu
    if target_state == "TYPE_CHOICE":
        # Go back to initial type selection
        keyboard = [[InlineKeyboardButton(t, callback_data=f"type|{t}")] for t in MAIN_TYPES]
        await query.edit_message_text("Seleccione tipo de trabajo:", reply_markup=InlineKeyboardMarkup(keyboard))
        return TYPE_CHOICE
    
    elif target_state == "SERVICE_CLIENT_SEARCH":
        # Go back to client search
        kb = [[InlineKeyboardButton("◀ Atrás", callback_data="back|TYPE_CHOICE")]]
        await query.edit_message_text("Ingrese nombre del cliente (o parte del nombre):", reply_markup=InlineKeyboardMarkup(kb))
        return SERVICE_CLIENT_SEARCH
    
    elif target_state == "SERVICE_CLIENT_SELECT":
        # Go back to showing search results
        return await show_client_page(update, context)
    
    elif target_state == "SERVICE_SERVICE_SELECT":
        # Go back to service selection
        return await show_service_options(query, context)
    
    elif target_state == "SERVICE_SUBSERVICE_SELECT":
        # Go back to subservice selection
        service_id = context.user_data['workflow'].get('service', '')
        service_name = SERVICIOS_PRINCIPALES.get(service_id, service_id)
        subservices = SERVICIOS_SECUNDARIOS_BY_PRINCIPAL.get(service_id, [])
        
        buttons = [[InlineKeyboardButton(
            SERVICIOS_SECUNDARIOS[sub_id]['nombre'], 
            callback_data=f"subservice_select|{sub_id}"
        )] for sub_id in subservices]
        buttons.append([InlineKeyboardButton("◀ Atrás", callback_data="back|SERVICE_SERVICE_SELECT")])
        
        client = context.user_data['workflow'].get('client', 'N/A')
        message = f"Cliente: {client}\nServicio: {service_name}\n\nSeleccione opción:"
        
        await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(buttons))
        return SERVICE_SUBSERVICE_SELECT
    
    elif target_state == "SERVICE_DETAIL_HILERAS":
        # Go back to Hileras detail
        subservice_name = SERVICIOS_SECUNDARIOS.get(context.user_data['workflow'].get('subservice', ''), {}).get('nombre', '')
        service_name = SERVICIOS_PRINCIPALES.get(context.user_data['workflow'].get('service', ''), '')
        return await show_service_detail_hileras(query, context, subservice_name, service_name)
    
    elif target_state == "SERVICE_DETAIL_CARAS":
        # Go back to Caras detail
        hileras_id = context.user_data['workflow'].get('details', {}).get('hileras', '')
        hileras_detail = DETALLES_SERVICIOS.get('D01', {})
        hileras_name = next((opt['nombre'] for opt in hileras_detail.get('opciones', []) if opt['_id'] == hileras_id), '')
        return await show_service_detail_caras(query, context, hileras_name)
    
    elif target_state == "SERVICE_DETAIL_PASADAS":
        # Go back to Pasadas detail
        caras_id = context.user_data['workflow'].get('details', {}).get('caras', '')
        caras_detail = DETALLES_SERVICIOS.get('D02', {})
        caras_name = next((opt['nombre'] for opt in caras_detail.get('opciones', []) if opt['_id'] == caras_id), '')
        return await show_service_detail_pasadas(query, context, caras_name)
    
    elif target_state == "MACHINE_NAME":
        # Go back to machine name selection
        workflow = context.user_data.get('workflow', {})
        buttons = [[InlineKeyboardButton(name, callback_data=f"machine_name|{name}")] for name in MACHINE_NAMES]
        buttons.append([InlineKeyboardButton("◀ Atrás", callback_data="back|TYPE_CHOICE")])
        await query.edit_message_text("Seleccione máquina:", reply_markup=InlineKeyboardMarkup(buttons))
        return MACHINE_NAME
    
    elif target_state == "MACHINE_NUM":
        # Go back to machine number selection
        workflow = context.user_data.get('workflow', {})
        machine_name = workflow.get('machine_name', '')
        buttons = [[InlineKeyboardButton(f"{k}", callback_data=f"machine_num|{k}")] for k in MACHINE_NUMBERS.keys()]
        buttons.append([InlineKeyboardButton("◀ Atrás", callback_data="back|MACHINE_NAME")])
        await query.edit_message_text(f"Máquina: {machine_name}\nSeleccione número:", reply_markup=InlineKeyboardMarkup(buttons))
        return MACHINE_NUM
    
    elif target_state == "COMPONENT":
        # Go back to component selection
        workflow = context.user_data.get('workflow', {})
        machine_name = workflow.get('machine_name', '')
        machine_num = workflow.get('machine_num', '')
        buttons = [[InlineKeyboardButton(PRINCIPALES[pid]['nombre'], callback_data=f"component|{pid}")] for pid in sorted(PRINCIPALES.keys())]
        buttons.append([InlineKeyboardButton("◀ Atrás", callback_data="back|MACHINE_NUM")])
        await query.edit_message_text(f"Máquina: {machine_name} {machine_num}\nSeleccione componente:", reply_markup=InlineKeyboardMarkup(buttons))
        return COMPONENT
    
    elif target_state == "SUBCOMPONENT":
        # Go back to subcomponent selection (redraw)
        workflow = context.user_data.get('workflow', {})
        principal_id = workflow.get('component_id')
        if principal_id:
            sub_ids = SECUNDARIOS_BY_PRINCIPAL.get(principal_id, [])
            buttons = [[InlineKeyboardButton(SECUNDARIOS[sid]['nombre'], callback_data=f"subcomponent|{sid}")] for sid in sub_ids]
            buttons.append([InlineKeyboardButton("◀ Atrás", callback_data="back|COMPONENT")])
            principal_name = PRINCIPALES[principal_id]['nombre']
            await query.edit_message_text(f"Componente: {principal_name}\nSeleccione sub-componente:", reply_markup=InlineKeyboardMarkup(buttons))
        return SUBCOMPONENT
    
    elif target_state == "CHECKLIST":
        # Go back to checklist - rebuild it with correct back button
        workflow = context.user_data.get('workflow', {})
        items = workflow.get('current_items', [])
        selected = workflow.get('selected_indices', set())
        
        buttons = []
        for i, item in enumerate(items):
            check = "☑" if i in selected else "☐"
            buttons.append([InlineKeyboardButton(f"{check} {item}", callback_data=f"toggle|{i}")])
        
        # Determine correct back button target
        subcomp_id = workflow.get('subcomponent_id')
        if subcomp_id:
            back_target = "SUBCOMPONENT"
        else:
            back_target = "COMPONENT"
        
        buttons.append([InlineKeyboardButton("Finalizar", callback_data="done_checklist"), InlineKeyboardButton("◀ Atrás", callback_data=f"back|{back_target}")])
        
        # Get current subcomponent/component name for display
        comp_id = workflow.get('component_id')
        
        if subcomp_id:
            title = f"Sub-componente: {SECUNDARIOS[subcomp_id]['nombre']}"
        else:
            title = f"Componente: {PRINCIPALES[comp_id]['nombre']}"
        
        await query.edit_message_text(
            f"{title}\nSeleccione items:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return CHECKLIST
    
    elif target_state == "COMMENT_CHOICE":
        # Go back to checklist
        workflow = context.user_data.get('workflow', {})
        items = workflow.get('current_items', [])
        selected = workflow.get('selected_indices', set())
        
        buttons = []
        for i, item in enumerate(items):
            check = "☑" if i in selected else "☐"
            buttons.append([InlineKeyboardButton(f"{check} {item}", callback_data=f"toggle|{i}")])
        buttons.append([InlineKeyboardButton("Finalizar", callback_data="done_checklist"), InlineKeyboardButton("◀ Atrás", callback_data="back|CHECKLIST")])
        
        await query.edit_message_text("Seleccione items:", reply_markup=InlineKeyboardMarkup(buttons))
        return CHECKLIST
    
    elif target_state == "PANAS_CHOICE":
        # Go back to comment choice
        kb = [[InlineKeyboardButton("Sí", callback_data="comments_yes"), InlineKeyboardButton("No", callback_data="comments_no")]]
        kb.append([InlineKeyboardButton("◀ Atrás", callback_data="back|CHECKLIST")])
        await query.edit_message_text("¿Desea agregar un comentario?", reply_markup=InlineKeyboardMarkup(kb))
        return COMMENT_CHOICE
    
    elif target_state == "SERVICE_HOROMETRO_INICIO":
        # Go back to subservice/last service detail step
        subservice_id = context.user_data['workflow'].get('subservice', '')
        applicable_details = [d for d in DETALLES_SERVICIOS.values() if subservice_id in d.get('aplica_a', [])]
        
        if applicable_details:
            # Has detalles, go back to pasadas
            caras_id = context.user_data['workflow'].get('details', {}).get('caras', '')
            caras_detail = DETALLES_SERVICIOS.get('D02', {})
            caras_name = next((opt['nombre'] for opt in caras_detail.get('opciones', []) if opt['_id'] == caras_id), '')
            return await show_service_detail_pasadas(query, context, caras_name)
        else:
            # No detalles, go back to subservice selection
            service_id = context.user_data['workflow'].get('service', '')
            service_name = SERVICIOS_PRINCIPALES.get(service_id, service_id)
            subservices = SERVICIOS_SECUNDARIOS_BY_PRINCIPAL.get(service_id, [])
            
            buttons = [[InlineKeyboardButton(
                SERVICIOS_SECUNDARIOS[sub_id]['nombre'], 
                callback_data=f"subservice_select|{sub_id}"
            )] for sub_id in subservices]
            buttons.append([InlineKeyboardButton("◀ Atrás", callback_data="back|SERVICE_SUBSERVICE_SELECT")])
            
            client = context.user_data['workflow'].get('client', 'N/A')
            message = f"Cliente: {client}\nServicio: {service_name}\n\nSeleccione opción:"
            
            await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(buttons))
            return SERVICE_SUBSERVICE_SELECT
    
    elif target_state == "SERVICE_HOROMETRO_TERMINO":
        # Go back to Horómetro Inicio
        kb = [[InlineKeyboardButton("◀ Atrás", callback_data="back|SERVICE_HOROMETRO_INICIO")]]
        await query.edit_message_text("Horómetro de Inicio:", reply_markup=InlineKeyboardMarkup(kb))
        return SERVICE_HOROMETRO_INICIO
    
    elif target_state == "SERVICE_HECTAREAS":
        # Go back to Horómetro Término
        kb = [[InlineKeyboardButton("◀ Atrás", callback_data="back|SERVICE_HOROMETRO_TERMINO")]]
        await query.edit_message_text("Horómetro de Término:", reply_markup=InlineKeyboardMarkup(kb))
        return SERVICE_HOROMETRO_TERMINO
    
    elif target_state == "SERVICE_HOROMETRO_INICIO_CONFIRM":
        # Go back to Horómetro Inicio input (show message asking for horometro)
        kb = [[InlineKeyboardButton("◀ Atrás", callback_data="back|SERVICE_DETAIL_PASADAS")]]
        await query.edit_message_text("Horómetro de Inicio:", reply_markup=InlineKeyboardMarkup(kb))
        return SERVICE_HOROMETRO_INICIO
    
    elif target_state == "SERVICE_HOROMETRO_TERMINO_CONFIRM":
        # Go back to Horómetro Termino input
        kb = [[InlineKeyboardButton("◀ Atrás", callback_data="back|SERVICE_HOROMETRO_INICIO_CONFIRM")]]
        await query.edit_message_text("Horómetro de Término:", reply_markup=InlineKeyboardMarkup(kb))
        return SERVICE_HOROMETRO_TERMINO
    
    elif target_state == "SERVICE_HECTAREAS_CONFIRM":
        # Go back to Hectáreas input
        kb = [[InlineKeyboardButton("◀ Atrás", callback_data="back|SERVICE_HOROMETRO_TERMINO_CONFIRM")]]
        await query.edit_message_text("Cantidad de Hectáreas:", reply_markup=InlineKeyboardMarkup(kb))
        return SERVICE_HECTAREAS
    
    elif target_state == "COMMENT_TEXT_CONFIRM":
        # Go back to Comment choice
        # Determine previous state based on workflow type
        workflow_type = context.user_data['workflow'].get('type', 'TALLER')
        if workflow_type == 'SERVICIO':
            prev_back = "back|SERVICE_HECTAREAS_CONFIRM"
        else:
            prev_back = "back|CHECKLIST"
        
        kb = [[InlineKeyboardButton("Sí", callback_data="comments_yes"), InlineKeyboardButton("No", callback_data="comments_no")]]
        kb.append([InlineKeyboardButton("◀ Atrás", callback_data=prev_back)])
        await query.edit_message_text("¿Desea agregar un comentario?", reply_markup=InlineKeyboardMarkup(kb))
        return COMMENT_CHOICE
    
    elif target_state == "PANAS_TEXT_CONFIRM":
        # Go back to PANAS choice
        kb = [[InlineKeyboardButton("Sí", callback_data="panas_yes"), InlineKeyboardButton("No", callback_data="panas_no")]]
        kb.append([InlineKeyboardButton("◀ Atrás", callback_data="back|COMMENT_CHOICE")])
        await query.edit_message_text("¿PANAS?", reply_markup=InlineKeyboardMarkup(kb))
        return PANAS_CHOICE
    
    elif target_state == "COMMENT_CHOICE" and context.user_data['workflow'].get('hectareas'):
        # Coming from service flow (hectareas was filled)
        # Go back to Hectáreas
        kb = [[InlineKeyboardButton("◀ Atrás", callback_data="back|SERVICE_HECTAREAS")]]
        await query.edit_message_text("Cantidad de Hectáreas:", reply_markup=InlineKeyboardMarkup(kb))
        return SERVICE_HECTAREAS

    
    return TYPE_CHOICE


async def ask_comments(query, context: ContextTypes.DEFAULT_TYPE, message=None):
    """Ask about comments."""
    kb = [[InlineKeyboardButton("Sí", callback_data="comments_yes"), InlineKeyboardButton("No", callback_data="comments_no")]]
    kb.append([InlineKeyboardButton("◀ Atrás", callback_data="back|CHECKLIST")])
    if query:
        await query.edit_message_text("¿Desea agregar un comentario?", reply_markup=InlineKeyboardMarkup(kb))
    else:
        await message.reply_text("¿Desea agregar un comentario?", reply_markup=InlineKeyboardMarkup(kb))
    return COMMENT_CHOICE


async def finish_workflow(query, context: ContextTypes.DEFAULT_TYPE, message=None):
    """Finish workflow and show summary."""
    data = context.user_data['workflow']
    
    summary = "📋 Workflow completado\n\n"
    summary += f"Tipo: {data['type']}\n"
    if data['type'] == 'TALLER':
        summary += f"Máquina: {data.get('machine_name', 'N/A')} {data.get('machine_num', 'N/A')}\n"
        comp_id = data.get('component_id')
        if comp_id:
            summary += f"Componente: {PRINCIPALES[comp_id]['nombre']}\n"
        subcomp_id = data.get('subcomponent_id')
        if subcomp_id:
            summary += f"Sub-componente: {SECUNDARIOS[subcomp_id]['nombre']}\n"
        
        # Include selected checklist items
        if data['selected_indices']:
            items = data['current_items']
            selected_items = [items[i] for i in sorted(data['selected_indices']) if i < len(items)]
            summary += f"Items revisados:\n"
            for item in selected_items:
                summary += f"  ✓ {item}\n"
    elif data['type'] == 'SERVICIO':
        if data.get('client'):
            summary += f"Cliente: {data['client']}\n"
        if data.get('service'):
            service_name = SERVICIOS_PRINCIPALES.get(data['service'], data['service'])
            summary += f"Servicio: {service_name}\n"
        if data.get('subservice'):
            subservice_data = SERVICIOS_SECUNDARIOS.get(data['subservice'], {})
            subservice_name = subservice_data.get('nombre', data['subservice'])
            summary += f"Opción: {subservice_name}\n"
        
        # Include service details if present
        if data.get('details'):
            details_data = data['details']
            if details_data.get('hileras'):
                hileras_detail = DETALLES_SERVICIOS.get('D01', {})
                hileras_name = next((opt['nombre'] for opt in hileras_detail.get('opciones', []) if opt['_id'] == details_data['hileras']), '')
                if hileras_name:
                    summary += f"Hileras: {hileras_name}\n"
            if details_data.get('caras'):
                caras_detail = DETALLES_SERVICIOS.get('D02', {})
                caras_name = next((opt['nombre'] for opt in caras_detail.get('opciones', []) if opt['_id'] == details_data['caras']), '')
                if caras_name:
                    summary += f"Caras: {caras_name}\n"
            if details_data.get('pasadas'):
                pasadas_detail = DETALLES_SERVICIOS.get('D03', {})
                pasadas_name = next((opt['nombre'] for opt in pasadas_detail.get('opciones', []) if opt['_id'] == details_data['pasadas']), '')
                if pasadas_name:
                    summary += f"Pasadas: {pasadas_name}\n"
    
    summary += f"\nInicio: {data['start']}\n"
    summary += f"Fin: {data['end']}\n"
    
    if data.get('horometro_inicio'):
        summary += f"\nHorómetro Inicio: {data['horometro_inicio']}\n"
    if data.get('horometro_termino'):
        summary += f"Horómetro Término: {data['horometro_termino']}\n"
    if data.get('hectareas'):
        summary += f"Hectáreas: {data['hectareas']}\n"
    
    if data.get('comment'):
        summary += f"\nComentario: {data['comment']}\n"
    if data.get('panas'):
        summary += f"PANAS: {data['panas']}\n"
    
    # Persist workflow to DB (attempt with retry and report id/errors to user)
    db_result_msg = ''
    try:
        user_id = None
        if query:
            user = getattr(query, 'from_user', None)
            if user:
                user_id = getattr(user, 'id', None)
        elif message:
            user_id = getattr(message.from_user, 'id', None)
        # use retrying wrapper
        new_id = await db.insert_workflow_with_retry(data, user_id=user_id)
        db_result_msg = f"\nGuardado en la base de datos (id={new_id})."
    except Exception as e:
        logger.exception("Failed to save workflow to DB: %s", e)
        db_result_msg = "\nOcurrió un error al guardar en la base de datos."

    # Add restart button
    keyboard = [[InlineKeyboardButton("🔄 Comenzar nuevamente", callback_data="start_workflow")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # append DB save result to summary
    summary += db_result_msg

    if query:
        await query.edit_message_text(summary, reply_markup=reply_markup)
    else:
        await message.reply_text(summary, reply_markup=reply_markup)
    
    return ConversationHandler.END


def main() -> None:
    """Start the bot."""
    # Initialize database quickly (no heavy migrations on startup)
    try:
        asyncio.run(db.init_db())
    except Exception as e:
        logger.exception(f"Failed to initialize database: {e}")

    # Get token from environment variable
    token = os.getenv("TELEGRAM_TOKEN", "8671366249:AAH5hTmnL4E4BYiWA7rMUYsQlGkfJL7ZmH0")
    application = Application.builder().token(token).build()

    # simple commands
    application.add_handler(CommandHandler("workflow", workflow_start))
    application.add_handler(CommandHandler("export_workflows", export_workflows))
    application.add_handler(CommandHandler("simulate_taller", simulate_taller))
    application.add_handler(CommandHandler("simulate_servicio", simulate_servicio))

    # conversation handler for workflow
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CommandHandler("workflow", workflow_start), 
            CallbackQueryHandler(workflow_start, pattern=r"^start_workflow")
        ],
        states={
            TYPE_CHOICE: [
                CallbackQueryHandler(type_selected, pattern=r"^type\|"),
                CallbackQueryHandler(back_button_handler, pattern=r"^back\|"),
                CommandHandler("start", start)
            ],
            SERVICE_CLIENT_SEARCH: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, service_client_search),
                CallbackQueryHandler(back_button_handler, pattern=r"^back\|"),
                CommandHandler("start", start)
            ],
            SERVICE_CLIENT_SELECT: [
                CallbackQueryHandler(service_client_selected, pattern=r"^service_client\|"),
                CallbackQueryHandler(service_client_pagination, pattern=r"^service_client_(prev|next)"),
                CallbackQueryHandler(back_button_handler, pattern=r"^back\|"),
                CommandHandler("start", start)
            ],
            SERVICE_SERVICE_SELECT: [
                CallbackQueryHandler(service_service_selected, pattern=r"^service_select\|"),
                CallbackQueryHandler(back_button_handler, pattern=r"^back\|"),
                CommandHandler("start", start)
            ],
            SERVICE_SUBSERVICE_SELECT: [
                CallbackQueryHandler(service_subservice_selected, pattern=r"^subservice_select\|"),
                CallbackQueryHandler(back_button_handler, pattern=r"^back\|"),
                CommandHandler("start", start)
            ],
            SERVICE_DETAIL_HILERAS: [
                CallbackQueryHandler(detail_hileras_selected, pattern=r"^detail_hileras\|"),
                CallbackQueryHandler(back_button_handler, pattern=r"^back\|"),
                CommandHandler("start", start)
            ],
            SERVICE_DETAIL_CARAS: [
                CallbackQueryHandler(detail_caras_selected, pattern=r"^detail_caras\|"),
                CallbackQueryHandler(back_button_handler, pattern=r"^back\|"),
                CommandHandler("start", start)
            ],
            SERVICE_DETAIL_PASADAS: [
                CallbackQueryHandler(detail_pasadas_selected, pattern=r"^detail_pasadas\|"),
                CallbackQueryHandler(back_button_handler, pattern=r"^back\|"),
                CommandHandler("start", start)
            ],
            MACHINE_NAME: [
                CallbackQueryHandler(machine_name_selected, pattern=r"^machine_name\|"),
                CallbackQueryHandler(back_button_handler, pattern=r"^back\|"),
                CommandHandler("start", start)
            ],
            MACHINE_NUM: [
                CallbackQueryHandler(machine_num_selected, pattern=r"^machine_num\|"),
                CallbackQueryHandler(back_button_handler, pattern=r"^back\|"),
                CommandHandler("start", start)
            ],
            COMPONENT: [
                CallbackQueryHandler(component_selected, pattern=r"^component\|"),
                CallbackQueryHandler(back_button_handler, pattern=r"^back\|"),
                CommandHandler("start", start)
            ],
            SUBCOMPONENT: [
                CallbackQueryHandler(subcomponent_selected, pattern=r"^subcomponent\|"),
                CallbackQueryHandler(back_button_handler, pattern=r"^back\|"),
                CommandHandler("start", start)
            ],
            CHECKLIST: [
                CallbackQueryHandler(toggle_checklist_item, pattern=r"^(toggle\||done_checklist)"),
                CallbackQueryHandler(back_button_handler, pattern=r"^back\|"),
                CommandHandler("start", start)
            ],
            COMMENT_CHOICE: [
                CallbackQueryHandler(comment_choice, pattern=r"^comments_"),
                CallbackQueryHandler(back_button_handler, pattern=r"^back\|"),
                CommandHandler("start", start)
            ],
            COMMENT_TEXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_comment),
                CallbackQueryHandler(back_button_handler, pattern=r"^back\|"),
                CommandHandler("start", start)
            ],
            PANAS_CHOICE: [
                CallbackQueryHandler(panas_choice, pattern=r"^panas_"),
                CallbackQueryHandler(back_button_handler, pattern=r"^back\|"),
                CommandHandler("start", start)
            ],
            PANAS_TEXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_panas_text),
                CallbackQueryHandler(back_button_handler, pattern=r"^back\|"),
                CommandHandler("start", start)
            ],
            SERVICE_HOROMETRO_INICIO: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_horometro_inicio),
                CallbackQueryHandler(back_button_handler, pattern=r"^back\|"),
                CommandHandler("start", start)
            ],
            SERVICE_HOROMETRO_TERMINO: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_horometro_termino),
                CallbackQueryHandler(back_button_handler, pattern=r"^back\|"),
                CommandHandler("start", start)
            ],
            SERVICE_HECTAREAS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_hectareas),
                CallbackQueryHandler(back_button_handler, pattern=r"^back\|"),
                CommandHandler("start", start)
            ],
            SERVICE_HOROMETRO_INICIO_CONFIRM: [
                CallbackQueryHandler(confirm_horometro_inicio, pattern=r"^confirm_horometro_inicio"),
                CallbackQueryHandler(back_button_handler, pattern=r"^back\|"),
                CommandHandler("start", start)
            ],
            SERVICE_HOROMETRO_TERMINO_CONFIRM: [
                CallbackQueryHandler(confirm_horometro_termino, pattern=r"^confirm_horometro_termino"),
                CallbackQueryHandler(back_button_handler, pattern=r"^back\|"),
                CommandHandler("start", start)
            ],
            SERVICE_HECTAREAS_CONFIRM: [
                CallbackQueryHandler(confirm_hectareas, pattern=r"^confirm_hectareas"),
                CallbackQueryHandler(back_button_handler, pattern=r"^back\|"),
                CommandHandler("start", start)
            ],
            COMMENT_TEXT_CONFIRM: [
                CallbackQueryHandler(confirm_comment, pattern=r"^confirm_comment"),
                CallbackQueryHandler(back_button_handler, pattern=r"^back\|"),
                CommandHandler("start", start)
            ],
            PANAS_TEXT_CONFIRM: [
                CallbackQueryHandler(confirm_panas, pattern=r"^confirm_panas"),
                CallbackQueryHandler(back_button_handler, pattern=r"^back\|"),
                CommandHandler("start", start)
            ],
        },
        fallbacks=[CommandHandler('cancel', finish_workflow)],
    )
    application.add_handler(conv_handler)

    application.add_error_handler(error_handler)
    # Ensure an event loop is available on Python 3.10+ where get_event_loop() may
    # raise if no loop is set in the main thread. Create and set one if needed.
    try:
        asyncio.get_running_loop()
    except Exception:
        asyncio.set_event_loop(asyncio.new_event_loop())

    print("Bot is starting polling...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
