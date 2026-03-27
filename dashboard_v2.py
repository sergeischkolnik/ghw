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
        SELECT id, 'TALLER' as type, machine_name, machine_number, component, comments, timestamp 
        FROM taller_outputs
    """, conn)
    
    # Load SERVICIO workflows  
    servicio = pd.read_sql_query("""
        SELECT id, 'SERVICIO' as type, client_name, null as machine_number, service, comments, timestamp 
        FROM servicio_outputs
    """, conn)
    
    conn.close()
    
    # Combine
    df = pd.concat([taller, servicio], ignore_index=True)
    return df

try:
    df = load_data()
    
    if df.empty:
        st.warning("No workflows found")
    else:
        # KPIs
        col1, col2, col3 = st.columns(3)
        col1.metric("📋 Total", len(df))
        col2.metric("🔧 Talleres", len(df[df['type']=='TALLER']))
        col3.metric("🚜 Servicios", len(df[df['type']=='SERVICIO']))
        
        # Type distribution
        type_counts = df['type'].value_counts()
        fig = px.pie(values=type_counts.values, names=type_counts.index, title="Distribución")
        st.plotly_chart(fig, use_container_width=True)
        
        # Table
        st.dataframe(df, use_container_width=True)
        
        # Export
        csv = df.to_csv(index=False)
        st.download_button("📥 Descargar CSV", csv, f"workflows_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        
except Exception as e:
    st.error(f"Error: {e}")

