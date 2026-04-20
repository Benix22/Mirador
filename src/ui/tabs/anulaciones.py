import streamlit as st
from src.ui.utils import get_client

def render_anulaciones_tab(config):
    st.header("Anulación de Comunicaciones")
    lote_anular = st.text_input("Número de Lote a anular completamente")
    confirmar = st.checkbox("Estoy seguro de que deseo anular este lote de forma irreversible.")
    
    if st.button("Anular Lote", type="primary", disabled=not confirmar):
        if lote_anular:
            client = get_client(config)
            res = client.anulacion_lote(lote_anular)
            st.divider()
            if "error" in res:
                st.error(f"❌ Error: {res['error']}")
            else:
                code = res.get('codigo', 0)
                desc = res.get('descripcion', 'Lote anulado correctamente')
                if code == 0: st.success(f"✅ {desc}")
                else: st.warning(f"⚠️ {desc} (Código: {code})")
                with st.expander("⚙️ Ver JSON Completo"):
                    st.json(res)
        else:
            st.error("Debes introducir un número de lote válido.")
