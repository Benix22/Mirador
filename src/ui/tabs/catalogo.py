import streamlit as st
import pandas as pd
from src.ui.utils import get_client
from src.core.db_manager import get_db

def render_catalogo_tab(config, DB_AVAILABLE):
    st.header("Consulta de Catálogos")
    cat_target = st.selectbox("Catálogo", [
        "SEXO", "TIPO_DOCUMENTO", "TIPO_MARCA_VEHICULO", "TIPO_PAGO", 
        "TIPO_PARENTESCO", "TIPO_COLOR", "TIPO_ESTABLECIMIENTO", "TIPO_VEHICULO",
        "NACIONALIDAD", "PROVINCIA", "MUNICIPIO", "PAIS"
    ])
    
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("🌐 Cargar del Ministerio"):
            client = get_client(config)
            if client:
                res = client.catalogo(cat_target)
                if "error" in res:
                    st.error(res["error"])
                else:
                    st.success(f"Datos de {cat_target} cargados desde el servidor")
                    try:
                        if 'respuesta' in res and 'resultado' in res['respuesta']:
                            data = res['respuesta']['resultado'].get('tupla', [])
                            parsed_data = [{'codigo': t['codigo'], 'descripcion': t['descripcion']} for t in data]
                        else:
                            parsed_data = res.get('data', [])
                        
                        df = pd.DataFrame(parsed_data)
                        if not df.empty:
                            st.dataframe(df, use_container_width=True)
                            if DB_AVAILABLE:
                                get_db().save_catalogo(cat_target, parsed_data, tenant_id="GLOBAL")
                                st.success(f"✅ Catálogo {cat_target} sincronizado en BBDD.")
                    except Exception as e:
                        st.error(f"Error al procesar el formato de respuesta: {e}")

    with col_btn2:
        if st.button("🗄️ Cargar desde BBDD"):
            if not DB_AVAILABLE: st.error("La conexión a la base de datos no está disponible.")
            else:
                try:
                    db_data = get_db().get_catalogo(cat_target, tenant_id="GLOBAL")
                    if db_data:
                        df = pd.DataFrame(db_data)
                        st.success(f"Catálogo {cat_target} cargado desde BBDD.")
                        st.dataframe(df, use_container_width=True)
                    else:
                        st.warning(f"El catálogo {cat_target} no está en la base de datos todavía.")
                except Exception as db_e: st.error(f"Error al leer de la BBDD: {db_e}")
