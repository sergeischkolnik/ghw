import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="GHW Dashboard", layout="wide")
st.title("📊 GHW Workflows")

# Load data from legacy tables
def load_data():
    conn = sqlite3.connect('ghw.db', check_same_thread=False)
    
    # Load TALLER workflows
    taller = pd.read_sql_query("""
        SELECT id, machine_name, machine_number, component, comments, timestamp 
        FROM taller_outputs
        ORDER BY timestamp DESC
    """, conn)
    
    # Load SERVICIO workflows  
    servicio = pd.read_sql_query("""
        SELECT id, client_name, service, details, comments, timestamp 
        FROM servicio_outputs
        ORDER BY timestamp DESC
    """, conn)
    
    conn.close()
    return taller, servicio

try:
    taller_df, servicio_df = load_data()
    
    # KPIs
    col1, col2, col3 = st.columns(3)
    col1.metric("📋 Total", len(taller_df) + len(servicio_df))
    col2.metric("🔧 Talleres", len(taller_df))
    col3.metric("🚜 Servicios", len(servicio_df))
    
    # Type distribution
    st.divider()
    type_counts = pd.Series({'TALLER': len(taller_df), 'SERVICIO': len(servicio_df)})
    fig = px.pie(values=type_counts.values, names=type_counts.index, title="Distribución por tipo")
    st.plotly_chart(fig, use_container_width=True)
    
    st.divider()
    
    # Tabs for separate views
    tab1, tab2 = st.tabs(["🔧 TALLER", "🚜 SERVICIO"])
    
    with tab1:
        st.subheader(f"Talleres ({len(taller_df)})")
        if not taller_df.empty:
            st.dataframe(taller_df, use_container_width=True)
            csv = taller_df.to_csv(index=False)
            st.download_button(
                "📥 Descargar TALLER (CSV)", 
                csv, 
                f"taller_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                key="taller_csv"
            )
        else:
            st.info("No hay datos de TALLER")
    
    with tab2:
        st.subheader(f"Servicios ({len(servicio_df)})")
        if not servicio_df.empty:
            st.dataframe(servicio_df, use_container_width=True)
            csv = servicio_df.to_csv(index=False)
            st.download_button(
                "📥 Descargar SERVICIO (CSV)", 
                csv, 
                f"servicio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                key="servicio_csv"
            )
        else:
            st.info("No hay datos de SERVICIO")
        
except Exception as e:
    st.error(f"Error: {e}")

