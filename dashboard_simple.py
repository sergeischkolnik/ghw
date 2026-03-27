import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="GHW Dashboard", layout="wide")
st.title("📊 GHW Workflows Dashboard")

@st.cache_resource
def get_connection():
    return sqlite3.connect('ghw.db', check_same_thread=False)

def load_data():
    conn = get_connection()
    
    # Load workshops (TALLERs)
    try:
        workshops_df = pd.read_sql("SELECT * FROM workshops", conn)
        workshops_df['type'] = 'TALLER'
    except:
        workshops_df = pd.DataFrame()
    
    # Load services (SERVICIOs)
    try:
        services_df = pd.read_sql("SELECT * FROM services", conn)
        services_df['type'] = 'SERVICIO'
    except:
        services_df = pd.DataFrame()
    
    return workshops_df, services_df

workshops, services = load_data()

if workshops.empty and services.empty:
    st.error("❌ No data found. Run: python test_data.py")
else:
    # Display stats
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Workflows", len(workshops) + len(services))
    col2.metric("TALLERs", len(workshops))
    col3.metric("SERVICIOs", len(services))
    
    # Show data
    if not workshops.empty:
        st.subheader("🔧 TALLERs")
        st.dataframe(workshops[['id', 'machine_name', 'machine_num', 'component_id', 'comment', 'created_at']], use_container_width=True)
    
    if not services.empty:
        st.subheader("🚜 SERVICIOs")
        st.dataframe(services[['id', 'client_id', 'service_id', 'comment', 'created_at']], use_container_width=True)
    
    # Export
    st.subheader("💾 Exportar")
    all_data = pd.concat([workshops, services], ignore_index=True)
    csv = all_data.to_csv(index=False)
    st.download_button("CSV", csv, f"workflows_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", "text/csv")

st.info("Dashboard simple y directo - sin cache issues")
