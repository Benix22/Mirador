import streamlit as st
import pandas as pd
from src.ui.utils import get_client

def render_consultas_tab(config):
    st.header("Consulta de Lotes y Comunicaciones")
    op_consulta = st.radio("Buscar por:", ["Número de Lote", "Código de Comunicación"])
    search_val = st.text_input("Valor a buscar")
    
    if st.button("Consultar"):
        client = get_client(config)
        if op_consulta == "Número de Lote":
            res = client.consulta_lote([search_val])
        else:
            res = client.consulta_comunicacion([search_val])
        
        st.divider()
        if "error" in res:
            st.error(f"❌ Error: {res['error']}")
        else:
            if op_consulta == "Número de Lote":
                resp_header = res.get('respuesta', {})
                results = res.get('resultado', [])
            else:
                resp_header = res.get('resultado', {})
                results = res.get('comunicacion', [])
            
            code = resp_header.get('codigo', 0)
            desc = resp_header.get('descripcion', 'Operación completada')
            
            if code == 0: st.success(f"✅ {desc}")
            else: st.warning(f"⚠️ {desc} (Código: {code})")
            
            if results:
                with st.expander("📄 Ver detalles de la consulta", expanded=True):
                    st.dataframe(pd.DataFrame(results), use_container_width=True)
            
            with st.expander("⚙️ Ver JSON Completo"):
                st.json(res)
