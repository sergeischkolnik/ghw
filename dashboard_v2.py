import streamlit as st
import psycopg2
import pandas as pd
import plotly.express as px
from datetime import datetime
import os

st.set_page_config(page_title="GHW Dashboard", layout="wide")
st.title("📊 GHW Workflows")

# Get PostgreSQL connection URL from environment
DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    st.error("❌ DATABASE_URL environment variable not set")
    st.stop()


@st.cache_data(ttl=60)
def load_data():
    """Load data from PostgreSQL"""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        
        # Load TALLER workflows (from workshops table)
        taller = pd.read_sql_query("""
            SELECT id, machine_name, machine_num, comment, start_ts as timestamp
            FROM workshops
            ORDER BY start_ts DESC
        """, conn)
        
        # Load SERVICIO workflows (from services table)
        servicio = pd.read_sql_query("""
            SELECT id, client_id as client_name, service_id as service, comment, start_ts as timestamp
            FROM services
            ORDER BY start_ts DESC
        """, conn)
        
        conn.close()
        return taller, servicio
    except Exception as e:
        st.error(f"❌ Database error: {e}")
        return pd.DataFrame(), pd.DataFrame()


# Add manual refresh button
if st.button("🔄 Refresh Now"):
    st.cache_data.clear()
    st.rerun()

# Display last update time
st.caption(f"ℹ️ Last update: {datetime.now().strftime('%H:%M:%S')}")

try:
    taller_df, servicio_df = load_data()
    
    # Debug: Show database info
    with st.expander("🔍 Debug Info"):
        st.write(f"**Database:** PostgreSQL (via DATABASE_URL)")
        st.write(f"**Taller workflows:** {len(taller_df)}")
        st.write(f"**Servicio workflows:** {len(servicio_df)}")
        if len(taller_df) > 0:
            st.write(f"**Latest TALLER:** {taller_df['timestamp'].iloc[0]}")
        if len(servicio_df) > 0:
            st.write(f"**Latest SERVICIO:** {servicio_df['timestamp'].iloc[0]}")
    
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

