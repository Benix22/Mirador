import streamlit as st
from src.core.db_manager import get_db
from src.core import auth as auth_core
import re

def login_view():
    with st.form("login_form"):
        log_email = st.text_input("Correo Electrónico")
        log_pass = st.text_input("Contraseña", type="password")
        if st.form_submit_button("Entrar", type="primary"):
            user_data = get_db().get_user_by_email(log_email)
            if user_data and auth_core and auth_core.verify_password(user_data['password_hash'], log_pass):
                if not user_data['subscription_active'] and user_data['role'] != 'admin':
                    st.error("Tu suscripción no está activa. Por favor, realiza el pago o contacta con soporte.")
                else:
                    st.session_state.user = user_data
                    st.rerun()
            else:
                st.error("Credenciales incorrectas")

def register_view():
    with st.form("register_form"):
        st.subheader("Datos de Acceso")
        reg_email = st.text_input("Correo Electrónico *")
        reg_pass = st.text_input("Contraseña *", type="password")
        reg_pass2 = st.text_input("Confirmar Contraseña *", type="password")
        
        st.subheader("Datos del Establecimiento (MIR)")
        reg_nombre = st.text_input("Nombre Comercial del Establecimiento *")
        reg_mir_user = st.text_input("Usuario MIR (CIF/NIF) *")
        reg_mir_pass = st.text_input("Contraseña MIR *", type="password")
        reg_arr = st.text_input("Código Arrendador *")
        reg_est = st.text_input("Código Establecimiento *")
        
        if st.form_submit_button("Crear Cuenta y Establecimiento", type="primary"):
            if reg_pass != reg_pass2:
                st.error("Las contraseñas no coinciden")
            elif not reg_email or not reg_nombre or not reg_arr or not reg_est or not reg_mir_user:
                st.error("Por favor, rellena todos los campos obligatorios")
            elif get_db().get_user_by_email(reg_email):
                st.error("Ya existe una cuenta con ese correo")
            else:
                role = 'admin' if reg_email == 'admin@mirador.com' else 'user'
                new_user_id = get_db().create_user(reg_email, auth_core.hash_password(reg_pass), role, True)
                if new_user_id:
                    slug_base = re.sub(r'[^a-z0-9]', '', reg_nombre.lower())[:15]
                    tenant_slug = f"{slug_base}_{new_user_id}"
                    get_db().save_tenant({
                        'tenant_id': tenant_slug,
                        'owner_id': new_user_id,
                        'nombre': reg_nombre,
                        'mir_user': reg_mir_user,
                        'mir_password': reg_mir_pass,
                        'arrendador_code': reg_arr,
                        'establecimiento_code': reg_est,
                        'p12_path': '',
                        'p12_password': ''
                    })
                    st.success("Cuenta creada exitosamente. Por favor, inicia sesión en la pestaña 'Iniciar Sesión'.")
                else:
                    st.error("Error al crear la cuenta")

def show_auth_ui():
    st.markdown("<h1 style='text-align: center;'>Bienvenido a Mirador</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #a0a0a0;'>Plataforma de Registro de Huéspedes (RD 933/2021)</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab_login, tab_register = st.tabs(["Iniciar Sesión", "Registrarse"])
        with tab_login:
            login_view()
        with tab_register:
            register_view()
