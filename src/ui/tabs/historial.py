import streamlit as st
import pandas as pd
from src.core.db_manager import get_db

def render_historial_tab(config):
    st.header("📅 Historial de Reservas y Viajeros")
    historial = get_db().get_historial(config['tenant_id'])
    
    if historial:
        for item in historial:
            status_icon = "✅" if item['status_code'] == 0 else "❌"
            title = f"{status_icon} {item['referencia_contrato']} | Lote: {item['lote']} | {item['created_at'].strftime('%d/%m/%Y %H:%M')}"
            
            with st.expander(title):
                h_col1, h_col2, h_col3 = st.columns(3)
                with h_col1:
                    st.write("**Estancia:**")
                    st.write(f"🛫 {item['fecha_entrada'].strftime('%d/%m/%Y')}")
                    st.write(f"🛬 {item['fecha_salida'].strftime('%d/%m/%Y')}")
                with h_col2:
                    st.write("**Comunicación:**")
                    st.write(f"Tipo: `{item['tipo_comunicacion']}`")
                    st.write(f"Estado MIR: `{item['status_code']}`")
                with h_col3:
                    st.write("**Huéspedes:**")
                    st.write(f"👥 {item['num_viajeros']} personas")
                
                viajeros_lote = get_db().get_viajeros_by_comunicacion(item['id'])
                if viajeros_lote:
                    st.markdown("---")
                    st.write("📋 **Detalle de Viajeros:**")
                    st.dataframe(pd.DataFrame(viajeros_lote), use_container_width=True)
    else:
        st.info("No hay registros en el historial todavía.")
