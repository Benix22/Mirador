import streamlit as st
import os
import pandas as pd
from datetime import datetime
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import pkcs12
from src.core.hospedajes_client import HospedajesClient
from src.core.db_manager import get_db

def get_env_bool(key, default="True"):
    val = str(os.getenv(key, default)).lower().strip()
    return val in ("true", "1", "t", "y", "yes")

def local_css(file_name):
    if os.path.exists(file_name):
        with open(file_name) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

@st.cache_data(ttl=3600, show_spinner=False)
def load_catalog(tipo, defaults, tenant_id="GLOBAL"):
    mapping = {k: k for k in defaults}
    try:
        db_data = get_db().get_catalogo(tipo, tenant_id=tenant_id)
        if db_data:
            mapping = {item['codigo']: f"{item['codigo']} - {item['descripcion']}" for item in db_data}
    except Exception as e:
        st.warning(f"No se pudo cargar el catálogo {tipo} para {tenant_id}: {e}")
    return mapping

def get_client(config):
    # Close old client if exists
    if st.session_state.get('client'):
        try:
            # We don't close it immediately to allow reuse if config matches
            pass
        except:
            pass

    # Extract config
    wsdl = config.get('wsdl')
    endpoint = config.get('endpoint')
    user = config.get('user')
    pwd = config.get('pwd')
    cert_file = config.get('cert_file')
    p12_password = config.get('p12_password')
    verify_ssl = config.get('verify_ssl', True)
    mock_mode = config.get('mock_mode', False)
    
    c_path = os.getenv("MIR_CERT_PATH", "")
    k_path = os.getenv("MIR_KEY_PATH", "")
    p12_path = os.getenv("MIR_P12_PATH", "")

    # Create temp directory for uploads
    if not os.path.exists("temp_certs"):
        os.makedirs("temp_certs")
        
    file_bytes = None
    is_p12 = False

    if cert_file:
        file_bytes = cert_file.getbuffer()
        is_p12 = cert_file.name.endswith(".p12") or cert_file.name.endswith(".pfx")
    elif p12_path and os.path.exists(p12_path):
        with open(p12_path, "rb") as f:
            file_bytes = f.read()
        is_p12 = True

    if file_bytes:
        if is_p12:
            if not p12_password:
                st.error("Por favor, introduce la contraseña del certificado .p12")
                return None
            try:
                private_key, certificate, additional_certificates = pkcs12.load_key_and_certificates(
                    file_bytes, p12_password.encode()
                )
                combined_path = os.path.join("temp_certs", "combined.pem")
                with open(combined_path, "wb") as f:
                    f.write(private_key.private_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PrivateFormat.PKCS8,
                        encryption_algorithm=serialization.NoEncryption()
                    ))
                    f.write(certificate.public_bytes(serialization.Encoding.PEM))
                    if additional_certificates:
                        for extra_cert in additional_certificates:
                            if extra_cert:
                                f.write(extra_cert.public_bytes(serialization.Encoding.PEM))
                c_path = combined_path
                k_path = None
            except Exception as e:
                st.error(f"Error al procesar el archivo .p12: {e}")
                return None
        else:
            c_path = os.path.join("temp_certs", cert_file.name)
            with open(c_path, "wb") as f:
                f.write(file_bytes)

    config_hash = f"{wsdl}-{endpoint}-{user}-{pwd}-{c_path}-{k_path}-{verify_ssl}-{mock_mode}"
    if st.session_state.get('client') and st.session_state.get('config_hash') == config_hash:
        return st.session_state.client

    client = HospedajesClient(
        wsdl_path=wsdl,
        endpoint=endpoint,
        username=user,
        password=pwd,
        cert_path=c_path if c_path else None,
        key_path=k_path if k_path else None,
        verify_ssl=verify_ssl,
        mock_mode=mock_mode
    )
    
    st.session_state.client = client
    st.session_state.config_hash = config_hash
    return client
