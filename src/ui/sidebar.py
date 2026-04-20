import streamlit as st
import os
from src.core.db_manager import get_db
from src.ui.utils import get_env_bool

def render_sidebar(DB_AVAILABLE):
    current_tenant_id = "GLOBAL"
    tenant_config = None
    
    with st.sidebar:
        st.title("⚙️ Configuración")
        
        if DB_AVAILABLE:
            st.subheader("🏢 Establecimiento / Inquilino")
            user_role = st.session_state.user.get('role', 'user')
            user_id = st.session_state.user.get('id')
            
            if user_role == 'admin':
                tenants = get_db().get_tenants()
                tenant_options = {t['tenant_id']: t['nombre'] for t in tenants}
                
                selected_tenant_id = st.selectbox(
                    "Seleccionar Establecimiento",
                    options=["-- Nuevo --"] + list(tenant_options.keys()),
                    format_func=lambda x: tenant_options.get(x, "Añadir nuevo...")
                )
                current_tenant_id = selected_tenant_id if selected_tenant_id != "-- Nuevo --" else "GLOBAL"
                
                if selected_tenant_id != "-- Nuevo --":
                    tenant_config = get_db().get_tenant_config(selected_tenant_id)
                    if tenant_config:
                        st.info(f"Conectado a: **{tenant_config['nombre']}**")
                else:
                    with st.expander("🆕 Registrar Nuevo Establecimiento", expanded=False):
                        with st.form("new_tenant_form"):
                            nt_id = st.text_input("ID Único (Slug)", placeholder="hotel_playa")
                            nt_nombre = st.text_input("Nombre Comercial", placeholder="Hotel Playa Salobreña")
                            nt_user = st.text_input("MIR User")
                            nt_pass = st.text_input("MIR Password", type="password")
                            nt_arr = st.text_input("Cód. Arrendador")
                            nt_est = st.text_input("Cód. Establecimiento")
                            
                            if st.form_submit_button("Guardar Establecimiento"):
                                if nt_id and nt_nombre:
                                    get_db().save_tenant({
                                        'tenant_id': nt_id, 'owner_id': user_id, 'nombre': nt_nombre,
                                        'mir_user': nt_user, 'mir_password': nt_pass,
                                        'arrendador_code': nt_arr, 'establecimiento_code': nt_est,
                                        'p12_path': '', 'p12_password': ''
                                    })
                                    st.success("Establecimiento guardado!")
                                    st.rerun()
                                else:
                                    st.error("ID y Nombre son obligatorios")
            else:
                tenants = get_db().get_tenants(owner_id=user_id)
                if tenants:
                    current_tenant_id = tenants[0]['tenant_id']
                    tenant_config = get_db().get_tenant_config(current_tenant_id)
                    st.info(f"Conectado a: **{tenant_config['nombre']}**")
                else:
                    st.error("No tienes ningún establecimiento asignado. Contacta con soporte.")
                    st.stop()
                    
            st.divider()

        # Auth & Endpoints
        if st.session_state.user.get('role') == 'admin':
            with st.expander("🌐 Endpoints", expanded=False):
                env = st.selectbox("Entorno", ["Pruebas", "Producción", "Custom"])
                if env == "Pruebas":
                    endpoint = "https://hospedajes.pre-ses.mir.es/hospedajes-web/ws/v1/comunicacion"
                elif env == "Producción":
                    endpoint = "https://hospedajes.ses.mir.es/hospedajes-web/ws/v1/comunicacion"
                else:
                    endpoint = st.text_input("Endpoint URL", "")
                wsdl = st.text_input("WSDL Path/URL", "schemas/comunicacion.wsdl")
            mock_mode = st.toggle("🚀 Modo Mock (Sin red)", value=get_env_bool("MODO_MOCK", "True"))
        else:
            endpoint = "https://hospedajes.ses.mir.es/hospedajes-web/ws/v1/comunicacion"
            wsdl = "schemas/comunicacion.wsdl"
            mock_mode = get_env_bool("MODO_MOCK", "False")

        with st.expander("🔐 Autenticación", expanded=True):
            user = st.text_input("Usuario (CIF/NIF)", value=tenant_config['mir_user'] if tenant_config else os.getenv("MIR_USER", ""))
            pwd = st.text_input("Contraseña", type="password", value=tenant_config['mir_password'] if tenant_config else os.getenv("MIR_PASSWORD", ""))
            cod_arr = st.text_input("Código Arrendador", value=tenant_config['arrendador_code'] if tenant_config else os.getenv("MIR_ARRENDADOR_CODE", ""))
            cod_est = st.text_input("Código Establecimiento", value=tenant_config['establecimiento_code'] if tenant_config else os.getenv("MIR_ESTABLECIMIENTO_CODE", ""))
            app_name = st.text_input("Nombre Aplicación", value=os.getenv("MIR_APP_NAME", "PythonClient_v1"))
            
        with st.expander("📜 Certificados (SSL)", expanded=True):
            st.info("Sube tu certificado .p12 para realizar envíos.")
            cert_file = st.file_uploader("Certificado Digital (.p12 / .pfx)", type=["p12", "pfx"])
            p12_pass = st.text_input("Contraseña del Certificado", type="password")
            verify_ssl = get_env_bool("MODO_SSL", "True")

    config = {
        'endpoint': endpoint, 'wsdl': wsdl, 'mock_mode': mock_mode,
        'user': user, 'pwd': pwd, 'cod_arrendador': cod_arr, 'cod_est': cod_est, 'app_name': app_name,
        'cert_file': cert_file, 'p12_password': p12_pass, 'verify_ssl': verify_ssl,
        'tenant_id': current_tenant_id
    }
    return config
