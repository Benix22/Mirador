import streamlit as st
import pandas as pd
from src.core.db_manager import get_db

def render_estadisticas_tab(config):
    st.header("📈 Dashboard de Estadísticas")
    stats = get_db().get_statistics(config['tenant_id'])
    
    if stats:
        col1, col2, col3 = st.columns(3)
        with col1: st.metric("Total Huéspedes Registrados", stats['total_viajeros'])
        with col2: st.metric("Países de Origen", len(stats['nacionalidades']))
        with col3: st.metric("Viajeros Recurrentes", len(stats['repetidores']))
            
        st.divider()
        
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("🌍 Top Nacionalidades")
            if stats['nacionalidades']:
                df_nac = pd.DataFrame(stats['nacionalidades'])
                st.bar_chart(df_nac.set_index('nacionalidad'))
            else: st.info("Sin datos de nacionalidades aún.")
        with c2:
            st.subheader("📅 Evolución de Registros")
            if stats['evolucion']:
                df_evo = pd.DataFrame(stats['evolucion'])
                st.line_chart(df_evo.set_index('fecha'))
            else: st.info("Sin datos históricos aún.")

        st.divider()
        g1, g2 = st.columns(2)
        with g1:
            st.subheader("📍 Provincias de Origen (ESP)")
            if stats['provincias']:
                df_prov = pd.DataFrame(stats['provincias'])
                st.bar_chart(df_prov.set_index('provincia'))
            else: st.info("Sin datos de provincias aún.")
        with g2:
            st.subheader("🏘️ Municipios de Origen")
            if stats['municipios']:
                df_mun = pd.DataFrame(stats['municipios'])
                st.bar_chart(df_mun.set_index('municipio'))
            else: st.info("Sin datos de municipios aún.")
        
        st.subheader("👥 Huéspedes Frecuentes")
        if stats['repetidores']:
            st.dataframe(pd.DataFrame(stats['repetidores']), use_container_width=True)
        else: st.write("No se han detectado viajeros recurrentes todavía.")
    else:
        st.error("No se pudieron cargar las estadísticas.")
