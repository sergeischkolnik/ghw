import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go

# Page config
st.set_page_config(page_title="GHW Dashboard", layout="wide", initial_sidebar_state="expanded")

# Title
st.title("📊 GHW Workflows Dashboard")

# Connect to DB (read-only)
@st.cache_resource
def get_db_connection():
    conn = sqlite3.connect('ghw.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def load_workflows():
    """Load all workflows from DB (both workshops and services)"""
    conn = get_db_connection()
    try:
        # Check if tables exist first
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='workshops'")
        workshops_exists = cursor.fetchone()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='services'")
        services_exists = cursor.fetchone()
        
        if not workshops_exists and not services_exists:
            return None
        
        # Build union query for both tables
        query = """
        SELECT 
            'TALLER' as type,
            id,
            machine_name,
            machine_num as machine_num,
            NULL as client,
            component_id as service,
            subcomponent_id as subservice,
            comment,
            panas,
            created_at,
            user_id
        FROM workshops
        WHERE 1=1
        """
        
        if not workshops_exists:
            query = "SELECT 1 WHERE 0=1"  # Empty result
        
        if services_exists:
            query += """
            UNION ALL
            SELECT 
                'SERVICIO' as type,
                id,
                NULL as machine_name,
                NULL as machine_num,
                client_id as client,
                service_id as service,
                subservice_id as subservice,
                comment,
                panas,
                created_at,
                user_id
            FROM services
            """
        
        query += " ORDER BY created_at DESC"
        
        df = pd.read_sql_query(query, conn)
        
        # Convert to datetime
        if not df.empty:
            df['created_at'] = pd.to_datetime(df['created_at'])
        
        return df
    except Exception as e:
        st.error(f"Error loading workflows: {e}")
        return pd.DataFrame()

# Load data
df = load_workflows()

if df is None:
    st.warning("⚠️ La tabla de workflows aún no existe en la base de datos.")
    st.info("""
    **¿Cómo crear datos?**
    
    1. **Opción A - Bot en Telegram (Arriba en Render):**
       - Abre Telegram → busca `@ghw_bot` (o tu bot)
       - Envía `/start`
       - Completa un workflow (TALLER o SERVICIO)
       - Los datos se guardan automáticamente
    
    2. **Opción B - Datos de prueba (Local):**
       - Corre el bot localmente: `python main.py`
       - Usa los comandos: `/simulate_taller` o `/simulate_servicio`
       - Luego recarga esta página
    
    Una vez tengas workflows guardados, verás los datos aquí. 📊
    """)
elif df.empty:
    st.warning("⚠️ No workflows found in database")
else:
    # Sidebar filters
    st.sidebar.header("🔍 Filtros")
    
    df_filtered = df.copy()
    
    # Filter by type
    workflow_types = ["Todos"] + sorted(df['type'].dropna().unique().tolist())
    selected_type = st.sidebar.selectbox("Tipo de Workflow", workflow_types)
    
    if selected_type != "Todos":
        df_filtered = df_filtered[df_filtered['type'] == selected_type]
    
    # Filter by machine
    if len(df_filtered[df_filtered['type'] == 'TALLER']) > 0:
        machines = ["Todas"] + sorted(df_filtered[df_filtered['type'] == 'TALLER']['machine_name'].dropna().unique().tolist())
        selected_machine = st.sidebar.selectbox("Máquina", machines)
        
        if selected_machine != "Todas":
            df_filtered = df_filtered[df_filtered['machine_name'] == selected_machine]
    
    # Filter by client
    if len(df_filtered[df_filtered['type'] == 'SERVICIO']) > 0:
        clients = ["Todos"] + sorted(df_filtered[df_filtered['type'] == 'SERVICIO']['client'].dropna().unique().tolist())
        selected_client = st.sidebar.selectbox("Cliente", clients)
        
        if selected_client != "Todos":
            df_filtered = df_filtered[df_filtered['client'] == selected_client]
    
    # KPIs
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📋 Total Workflows", len(df_filtered))
    with col2:
        st.metric("🔧 Talleres", len(df_filtered[df_filtered['type'] == 'TALLER']))
    with col3:
        st.metric("🚜 Servicios", len(df_filtered[df_filtered['type'] == 'SERVICIO']))
    with col4:
        st.metric("⏱️ Workflows", len(df_filtered))
    
    # Charts
    st.header("📈 Análisis")
    col1, col2 = st.columns(2)
    
    with col1:
        type_dist = df_filtered['type'].value_counts().reset_index()
        type_dist.columns = ['Tipo', 'Cantidad']
        if not type_dist.empty:
            fig = px.pie(type_dist, names='Tipo', values='Cantidad', title="Distribución")
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        machine_usage = df_filtered[df_filtered['type'] == 'TALLER']['machine_name'].value_counts().reset_index()
        if not machine_usage.empty:
            machine_usage.columns = ['Máquina', 'Uso']
            fig = px.barh(machine_usage, x='Uso', y='Máquina', title="Máquinas")
            st.plotly_chart(fig, use_container_width=True)
    
    # Table
    st.header("📋 Workflows")
    display_df = df_filtered[['id', 'type', 'machine_name', 'client', 'comment', 'created_at']].copy()
    st.dataframe(display_df, use_container_width=True)
    
    # Export
    st.header("💾 Exportar")
    col1, col2 = st.columns(2)
    with col1:
        csv = df_filtered.to_csv(index=False)
        st.download_button("📥 CSV", csv, f"workflows_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", "text/csv")
    with col2:
        json_data = df_filtered.to_json(orient='records', date_format='iso')
        st.download_button("📥 JSON", json_data, f"workflows_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", "application/json")

st.sidebar.markdown("---")
st.sidebar.info("🤖 Dashboard sincronizado con la BD")
