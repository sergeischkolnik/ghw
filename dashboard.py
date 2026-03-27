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
    conn = sqlite3.connect('ghw.db')
    conn.row_factory = sqlite3.Row
    return conn

def load_workflows():
    """Load all workflows from DB"""
    conn = get_db_connection()
    try:
        df = pd.read_sql_query("""
            SELECT 
                id, 
                type, 
                machine_name, 
                machine_num, 
                client, 
                service,
                subservice,
                comment,
                panas,
                created_at,
                user_id
            FROM workflows 
            ORDER BY created_at DESC
        """, conn)
        
        # Convert to datetime
        if not df.empty:
            df['created_at'] = pd.to_datetime(df['created_at'])
        
        return df
    except Exception as e:
        st.error(f"Error loading workflows: {e}")
        return pd.DataFrame()

# Load data
df = load_workflows()

if df.empty:
    st.warning("⚠️ No workflows found in database")
else:
    # Sidebar filters
    st.sidebar.header("🔍 Filtros")
    
    # Filter by type
    workflow_types = ["Todos"] + df['type'].unique().tolist()
    selected_type = st.sidebar.selectbox("Tipo de Workflow", workflow_types)
    
    if selected_type != "Todos":
        df_filtered = df[df['type'] == selected_type]
    else:
        df_filtered = df
    
    # Filter by machine (only for TALLER)
    if 'TALLER' in df['type'].values:
        machines = ["Todas"] + sorted(df[df['type'] == 'TALLER']['machine_name'].dropna().unique().tolist())
        selected_machine = st.sidebar.selectbox("Máquina", machines)
        
        if selected_machine != "Todas":
            df_filtered = df_filtered[df_filtered['machine_name'] == selected_machine]
    
    # Filter by client (only for SERVICIO)
    if 'SERVICIO' in df['type'].values:
        clients = ["Todos"] + sorted(df[df['type'] == 'SERVICIO']['client'].dropna().unique().tolist())
        selected_client = st.sidebar.selectbox("Cliente", clients)
        
        if selected_client != "Todos":
            df_filtered = df_filtered[df_filtered['client'] == selected_client]
    
    # Date range filter
    st.sidebar.subheader("Rango de fechas")
    date_min = df['created_at'].min().date()
    date_max = df['created_at'].max().date()
    
    selected_date_min = st.sidebar.date_input("Desde", date_min)
    selected_date_max = st.sidebar.date_input("Hasta", date_max)
    
    df_filtered = df_filtered[
        (df_filtered['created_at'].dt.date >= selected_date_min) &
        (df_filtered['created_at'].dt.date <= selected_date_max)
    ]
    
    # ==== MAIN DASHBOARD ====
    
    # KPIs
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📋 Total Workflows", len(df_filtered))
    
    with col2:
        taller_count = len(df_filtered[df_filtered['type'] == 'TALLER'])
        st.metric("🔧 Talleres", taller_count)
    
    with col3:
        servicio_count = len(df_filtered[df_filtered['type'] == 'SERVICIO'])
        st.metric("🚜 Servicios", servicio_count)
    
    with col4:
        if not df_filtered.empty:
            last_workflow = df_filtered.iloc[0]
            time_ago = datetime.now() - pd.Timestamp(last_workflow['created_at']).to_pydatetime()
            hours_ago = int(time_ago.total_seconds() / 3600)
            st.metric("⏱️ Último workflow", f"{hours_ago}h atrás")
    
    # ==== CHARTS ====
    
    st.header("📈 Análisis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Workflows por día
        if not df_filtered.empty:
            df_daily = df_filtered.set_index('created_at').resample('D').size().reset_index()
            df_daily.columns = ['Fecha', 'Cantidad']
            
            fig = px.bar(df_daily, x='Fecha', y='Cantidad', 
                        title="Workflows por Día",
                        labels={'Cantidad': 'Cantidad de Workflows'})
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Distribución TALLER vs SERVICIO
        if not df_filtered.empty:
            type_dist = df_filtered['type'].value_counts().reset_index()
            type_dist.columns = ['Tipo', 'Cantidad']
            
            fig = px.pie(type_dist, names='Tipo', values='Cantidad',
                        title="Distribución: TALLER vs SERVICIO")
            st.plotly_chart(fig, use_container_width=True)
    
    # Máquinas más usadas (solo TALLER)
    if len(df_filtered[df_filtered['type'] == 'TALLER']) > 0:
        st.subheader("🔧 Máquinas más usadas")
        machine_usage = df_filtered[df_filtered['type'] == 'TALLER']['machine_name'].value_counts().reset_index()
        machine_usage.columns = ['Máquina', 'Uso']
        
        fig = px.barh(machine_usage, x='Uso', y='Máquina', 
                     title="Top Máquinas",
                     labels={'Uso': 'Cantidad de Workflows'})
        st.plotly_chart(fig, use_container_width=True)
    
    # Clientes más activos (solo SERVICIO)
    if len(df_filtered[df_filtered['type'] == 'SERVICIO']) > 0:
        st.subheader("👥 Clientes más activos")
        client_usage = df_filtered[df_filtered['type'] == 'SERVICIO']['client'].value_counts().head(10).reset_index()
        client_usage.columns = ['Cliente', 'Servicios']
        
        fig = px.barh(client_usage, x='Servicios', y='Cliente',
                     title="Top 10 Clientes")
        st.plotly_chart(fig, use_container_width=True)
    
    # ==== DATA TABLE ====
    
    st.header("📋 Tabla de Workflows")
    
    # Display table
    display_df = df_filtered[[
        'id', 'type', 'machine_name', 'machine_num', 'client', 
        'service', 'subservice', 'comment', 'panas', 'created_at'
    ]].copy()
    
    display_df['created_at'] = display_df['created_at'].dt.strftime('%Y-%m-%d %H:%M')
    
    # Rename columns for display
    display_df.columns = [
        'ID', 'Tipo', 'Máquina', 'Número', 'Cliente', 
        'Servicio', 'Sub-servicio', 'Comentario', 'PANAS', 'Fecha'
    ]
    
    st.dataframe(display_df, use_container_width=True, height=400)
    
    # ==== EXPORT ====
    
    st.header("💾 Exportar datos")
    
    col1, col2 = st.columns(2)
    
    with col1:
        csv = df_filtered.to_csv(index=False)
        st.download_button(
            label="📥 Descargar CSV",
            data=csv,
            file_name=f"workflows_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    
    with col2:
        json_data = df_filtered.to_json(orient='records', date_format='iso')
        st.download_button(
            label="📥 Descargar JSON",
            data=json_data,
            file_name=f"workflows_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )

st.sidebar.markdown("---")
st.sidebar.info("🤖 Dashboard en read-only. El bot sigue funcionando normalmente.")
