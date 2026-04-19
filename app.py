import streamlit as st
import pandas as pd
from hospedajes_client import HospedajesClient
import os
from datetime import datetime
from dotenv import load_dotenv

# Optional DB Manager
try:
    from db_manager import get_db
    DB_AVAILABLE = True
except Exception as e:
    DB_AVAILABLE = False
    print(f"Database not available: {e}")

# --- Load Environment Variables ---
# override=True ensures .env values take precedence over system env vars
load_dotenv(override=True)

import warnings
# Suppress specific cryptography warning about PKCS#12 format
warnings.filterwarnings("ignore", category=UserWarning, message=".*PKCS#12 bundle could not be parsed as DER.*")

def get_env_bool(key, default="True"):
    val = str(os.getenv(key, default)).lower().strip()
    return val in ("true", "1", "t", "y", "yes")

# --- Init Database ---
if DB_AVAILABLE:
    try:
        get_db().init_db()
    except Exception as e:
        st.sidebar.error(f"Error conectando a BBDD: {e}")
        DB_AVAILABLE = False

# --- Page Configuration ---
st.set_page_config(
    page_title="MIR Hospedajes Web Service Client",
    page_icon="🏨",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Custom Styles ---
st.markdown("""
    <style>
    .main {
        background-color: #0e1117;
    }
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
        background-color: #ff4b4b;
        color: white;
    }
    .stExpander {
        background-color: #1e2130;
        border-radius: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- Sidebar: Configuration ---
with st.sidebar:
    st.title("⚙️ Configuración")
    
    with st.expander("🌐 Endpoints", expanded=True):
        env = st.selectbox("Entorno", ["Pruebas", "Producción", "Custom"])
        if env == "Pruebas":
            endpoint = "https://hospedajes.pre-ses.mir.es/hospedajes-web/ws/v1/comunicacion"
        elif env == "Producción":
            endpoint = "https://hospedajes.ses.mir.es/hospedajes-web/ws/v1/comunicacion"
        else:
            endpoint = st.text_input("Endpoint URL", "")
            
        wsdl = st.text_input("WSDL Path/URL", "comunicacion.wsdl")
        
    with st.expander("🔐 Autenticación", expanded=True):
        user = st.text_input("Usuario (CIF/NIF)", value=os.getenv("MIR_USER", ""))
        pwd = st.text_input("Contraseña", type="password", value=os.getenv("MIR_PASSWORD", ""))
        cod_arrendador = st.text_input("Código Arrendador", value=os.getenv("MIR_ARRENDADOR_CODE", ""))
        app_name = st.text_input("Nombre Aplicación", value=os.getenv("MIR_APP_NAME", "PythonClient_v1"))
        
    with st.expander("📜 Certificados (SSL)", expanded=False):
        cert_file = st.file_uploader("Certificado (.pem/.crt/.p12)", type=["pem", "crt", "p12", "pfx"])
        p12_password = st.text_input("Contraseña Certificado (.p12)", type="password", value=os.getenv("MIR_P12_PASSWORD", ""), help="Solo necesaria si subes un archivo .p12")
        key_file = st.file_uploader("Clave Privada (.key)", type=["key"], help="Opcional si usas .p12")
        verify_ssl = st.checkbox("Verificar SSL (CA)", value=get_env_bool("MODO_SSL", "True"), help="Desactiva esto solo si tienes errores de 'unable to get local issuer certificate' en pruebas.")
        
    mock_mode = st.toggle("🚀 Modo Mock (Sin red)", value=get_env_bool("MODO_MOCK", "True"))


# --- Session State ---
if 'client' not in st.session_state:
    st.session_state.client = None
if 'viajeros' not in st.session_state:
    st.session_state.viajeros = [{'nombre': 'JUAN', 'apellido1': 'GARCIA'}]

def add_viajero():
    st.session_state.viajeros.append({'nombre': '', 'apellido1': ''})

def remove_viajero():
    if len(st.session_state.viajeros) > 1:
        st.session_state.viajeros.pop()

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import pkcs12

def get_client():
    c_path = os.getenv("MIR_CERT_PATH", "")
    k_path = os.getenv("MIR_KEY_PATH", "")
    p12_path = os.getenv("MIR_P12_PATH", "")
    p12_pass = p12_password if p12_password else os.getenv("MIR_P12_PASSWORD", "")
    
    # Only use env paths if they actually exist
    if c_path and not os.path.exists(c_path):
        c_path = ""
    if k_path and not os.path.exists(k_path):
        k_path = ""
    if p12_path and not os.path.exists(p12_path):
        p12_path = ""
    
    # Create temp directory for uploads
    if not os.path.exists("temp_certs"):
        os.makedirs("temp_certs")
        
    # Handle File Uploader (Manual)
    if cert_file:
        file_bytes = cert_file.getbuffer()
        is_p12 = cert_file.name.endswith(".p12") or cert_file.name.endswith(".pfx")
    # Handle Env Path (Automatic)
    elif p12_path:
        with open(p12_path, "rb") as f:
            file_bytes = f.read()
        is_p12 = True
    else:
        file_bytes = None
        is_p12 = False

    if file_bytes:
        if is_p12:
            if not p12_pass:
                st.error("Por favor, introduce la contraseña del certificado .p12")
                return None
            try:
                private_key, certificate, additional_certificates = pkcs12.load_key_and_certificates(
                    file_bytes, p12_pass.encode()
                )
                # Combine cert and key into a single file for better compatibility
                combined_path = os.path.join("temp_certs", "combined.pem")
                with open(combined_path, "wb") as f:
                    # Write private key first
                    f.write(private_key.private_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PrivateFormat.PKCS8,
                        encryption_algorithm=serialization.NoEncryption()
                    ))
                    # Write certificate
                    f.write(certificate.public_bytes(serialization.Encoding.PEM))
                    # Write chain
                    if additional_certificates:
                        for extra_cert in additional_certificates:
                            if extra_cert:
                                f.write(extra_cert.public_bytes(serialization.Encoding.PEM))
                
                c_path = combined_path
                k_path = None # Key is already in c_path
            except Exception as e:
                st.error(f"Error al procesar el archivo .p12: {e}")
                return None
        else:
            c_path = os.path.join("temp_certs", cert_file.name)
            with open(c_path, "wb") as f:
                f.write(file_bytes)

    if key_file and not cert_file.name.endswith(".p12"):
        k_path = os.path.join("temp_certs", key_file.name)
        with open(k_path, "wb") as f:
            f.write(key_file.getbuffer())

    # Check if we can reuse the existing client
    config_hash = f"{wsdl}-{endpoint}-{user}-{pwd}-{c_path}-{k_path}-{verify_ssl}-{mock_mode}"
    if st.session_state.client and st.session_state.get('config_hash') == config_hash:
        return st.session_state.client

    # Close old client if exists
    if st.session_state.client:
        try:
            st.session_state.client.close()
        except:
            pass

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

# --- Catalog Helper ---
def load_catalog(tipo, defaults):
    if 'cat_cache' not in st.session_state:
        st.session_state.cat_cache = {}
        
    if tipo not in st.session_state.cat_cache:
        mapping = {k: k for k in defaults}
        if DB_AVAILABLE:
            try:
                db_data = get_db().get_catalogo(tipo)
                if db_data:
                    mapping = {item['codigo']: f"{item['codigo']} - {item['descripcion']}" for item in db_data}
            except:
                pass
        st.session_state.cat_cache[tipo] = mapping
    return st.session_state.cat_cache[tipo]

# --- Main Content ---
st.title("🏨 MIR Hospedajes - Portal de Comunicaciones")
if not get_env_bool("MODO_SSL", "True") and not get_env_bool("MODO_MOCK", "True"):
    st.warning("⚠️ Validación SSL desactivada. La conexión no es segura (solo para pruebas).")
elif not get_env_bool("MODO_MOCK", "True"):
    st.success("🔒 Validación SSL activa.")

st.info("Esta aplicación permite gestionar el envío de partes y reservas según el RD 933/2021.")

tabs = st.tabs(["📤 Alta", "🔍 Consultas", "❌ Anulaciones", "📚 Catálogo"])

# --- TAB: Alta ---
with tabs[0]:
    st.header("Envío de Comunicaciones (Alta)")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        tipo_com = st.selectbox("Tipo de Comunicación", [
            "PV - Partes de Viajeros",
            "RH - Reservas de Hospedaje",
            "AV - Alquiler de Vehículos",
            "RV - Reservas de Vehículos"
        ])
        cod_est = st.text_input("Código Establecimiento", value=os.getenv("MIR_ESTABLECIMIENTO_CODE", ""))
        
        st.write("---")
        st.write(f"👥 Viajeros: **{len(st.session_state.viajeros)}**")
        c_add, c_rem = st.columns(2)
        with c_add:
            st.button("➕ Añadir", on_click=add_viajero)
        with c_rem:
            st.button("🗑️ Quitar", on_click=remove_viajero)
        
    with col2:
        st.subheader("Datos de la Comunicación")
        # Main form for contract and payment
        with st.form("main_data_form"):
            c1, c2 = st.columns(2)
            with c1:
                ref = st.text_input("Referencia del Contrato", f"REF-{datetime.now().strftime('%Y%m%d%H%M%S')}")
                f_cont = st.date_input("Fecha Contrato", datetime.now())
                num_hab = st.number_input("Número de Habitaciones", min_value=1, value=1)
            with c2:
                f_ent = st.datetime_input("Fecha Entrada/Inicio", datetime.now())
                f_sal = st.datetime_input("Fecha Salida/Fin", datetime.now())
                tiene_internet = st.checkbox("¿Tiene acceso a Internet?", value=False)
            
            st.divider()
            st.write("💳 Datos de Pago")
            p_col1, p_col2 = st.columns([1, 3])
            with p_col1:
                cat_pago = load_catalog("TIPO_PAGO", ["EF", "TC", "TR", "OT"])
                tipo_pago = st.selectbox("Tipo de Pago", options=list(cat_pago.keys()), format_func=lambda x: cat_pago[x], help="Selecciona según el catálogo oficial")
                f_pago = st.date_input("Fecha de Pago", datetime.now())
                p_caducidad = st.text_input("Caducidad Tarjeta", value="", placeholder="MM/AAAA", help="Solo para TC")
            with p_col2:
                medio_pago = st.text_input("Identificación del Medio de Pago (IBAN, Tarjeta, etc.)", value="")
                p_titular = st.text_input("Nombre Completo del Titular del Pago", "")
            
            st.form_submit_button("Guardar Datos Generales", help="Pulsa esto para confirmar los datos de arriba antes de enviar.")

        # Traveler inputs (outside form to be dynamic)
        lista_personas_data = []
        for i, viajero in enumerate(st.session_state.viajeros):
            with st.expander(f"👤 Persona {i+1}: {viajero.get('nombre', '')} {viajero.get('apellido1', '')}", expanded=(i==len(st.session_state.viajeros)-1)):
                v1, v2 = st.columns([2, 1])
                with v1:
                    p_nom = st.text_input(f"Nombre P{i+1}", viajero.get('nombre', 'JUAN'), key=f"nom_{i}")
                    p_ap1 = st.text_input(f"Primer Apellido P{i+1}", viajero.get('apellido1', 'GARCIA'), key=f"ap1_{i}")
                    
                    # Logica para Segundo Apellido (Obligatorio para NIF)
                    label_ap2 = f"Segundo Apellido P{i+1}"
                    is_nif = st.session_state.get(f"tdoc_{i}") == "NIF"
                    if is_nif:
                        label_ap2 += " ⚠️ (Obligatorio para NIF)"
                    
                    p_ap2 = st.text_input(label_ap2, "", key=f"ap2_{i}")
                    
                    if is_nif and not p_ap2:
                        st.error(f"El segundo apellido es obligatorio para NIF (Persona {i+1})")
                    
                    # Soporte Documento (Obligatorio para NIF/NIE)
                    is_nie = st.session_state.get(f"tdoc_{i}") == "NIE"
                    label_soporte = f"Número Soporte P{i+1}"
                    if is_nif or is_nie:
                        label_soporte += " ⚠️ (Obligatorio para NIF/NIE)"
                    p_soporte = st.text_input(label_soporte, "", key=f"soporte_{i}", help="Ej: IDESP... para NIF o E... para NIE")
                
                with v2:
                    cat_tdoc = load_catalog("TIPO_DOCUMENTO", ["NIF", "NIE", "PAS", "ID"])
                    p_tdoc = st.selectbox(f"Tipo Doc P{i+1}", options=list(cat_tdoc.keys()), format_func=lambda x: cat_tdoc[x], key=f"tdoc_{i}")
                    p_doc = st.text_input(f"Documento P{i+1}", "12345678Z", key=f"doc_{i}")
                    
                    cat_sexo = load_catalog("SEXO", ["M", "F", "X"])
                    p_sexo = st.selectbox(f"Sexo P{i+1}", options=list(cat_sexo.keys()), format_func=lambda x: cat_sexo[x], key=f"sexo_{i}")
                    p_fnac = st.date_input(f"Fecha Nacimiento P{i+1}", datetime(1980, 1, 1), key=f"fnac_{i}")
                
                # Calcular si es menor de edad (18 años)
                es_menor = (datetime.now().date() - p_fnac).days < (18 * 365)
                
                v3, v4 = st.columns(2)
                with v3:
                    p_nac = st.text_input(f"Nacionalidad P{i+1}", "ESP", key=f"nac_{i}")
                    
                    cat_parentesco = load_catalog("TIPO_PARENTESCO", ["", "P", "M", "A", "H", "O"])
                    p_parentesco = st.selectbox(f"Parentesco P{i+1}", options=list(cat_parentesco.keys()), format_func=lambda x: cat_parentesco[x] if x else "Ninguno", key=f"par_{i}")
                    
                    if es_menor and not p_parentesco:
                        st.warning(f"Persona {i+1} es menor. El parentesco es obligatorio.")
                with v4:
                    p_rol = st.selectbox(f"Rol P{i+1}", ["VI"], help="VI: Viajero (Obligatorio)", key=f"rol_{i}")
                
                # Contacto
                st.write(f"📞 Contacto P{i+1} (Al menos uno obligatorio)")
                c1, c2 = st.columns(2)
                with c1:
                    p_tel = st.text_input(f"Teléfono P{i+1}", "", key=f"tel_{i}")
                with c2:
                    p_email = st.text_input(f"Correo Electrónico P{i+1}", "", key=f"email_{i}")
                
                if not p_tel and not p_email:
                    st.error(f"Debes indicar al menos un teléfono o correo para la Persona {i+1}")
                
                # Direccion
                st.write(f"🏠 Dirección P{i+1}")
                d1, d2, d3, d4 = st.columns([2, 2, 1, 1])
                with d1:
                    d_dir = st.text_input(f"Dirección P{i+1}", "CALLE FALSA 123", key=f"dir_{i}")
                with d2:
                    cat_mun = load_catalog("MUNICIPIO", ["28079"])
                    d_mun = st.selectbox(f"Municipio P{i+1}", options=list(cat_mun.keys()), format_func=lambda x: cat_mun[x] if x in cat_mun else x, key=f"mun_{i}", help="Escribe para buscar el municipio")
                with d3:
                    d_cp = st.text_input(f"CP P{i+1}", "28001", key=f"cp_{i}")
                with d4:
                    d_pais = st.text_input(f"País P{i+1}", "ESP", key=f"dpais_{i}")

                # Update session state with current values
                st.session_state.viajeros[i]['nombre'] = p_nom
                st.session_state.viajeros[i]['apellido1'] = p_ap1

                lista_personas_data.append({
                    'rol': p_rol, 'nombre': p_nom, 'apellido1': p_ap1, 'apellido2': p_ap2,
                    'tipoDocumento': p_tdoc, 'numeroDocumento': p_doc, 'soporteDocumento': p_soporte,
                    'fechaNacimiento': p_fnac.strftime('%Y-%m-%d'), 'nacionalidad': p_nac, 'sexo': p_sexo,
                    'telefono': p_tel, 'correo': p_email, 'parentesco': p_parentesco,
                    'direccion': {'direccion': d_dir, 'codigoMunicipio': d_mun, 'codigoPostal': d_cp, 'pais': d_pais}
                })
        
        st.divider()
        if st.button("🚀 ENVIAR COMUNICACIÓN A MIR", type="primary"):
            # Final validation
            errors = []
            for i, p in enumerate(lista_personas_data):
                if p['tipoDocumento'] == 'NIF' and not p.get('apellido2'):
                    errors.append(f"Persona {i+1}: Falta el segundo apellido (NIF obligatorio)")
                if p['tipoDocumento'] in ['NIF', 'NIE'] and not p.get('soporteDocumento'):
                    errors.append(f"Persona {i+1}: Falta el número de soporte (Obligatorio para {p['tipoDocumento']})")
                if not p.get('telefono') and not p.get('correo'):
                    errors.append(f"Persona {i+1}: Debe indicar al menos un teléfono o correo")
                if not p['direccion'].get('codigoMunicipio'):
                    errors.append(f"Persona {i+1}: El municipio es obligatorio")
                
                # Check for minor
                dob = datetime.strptime(p['fechaNacimiento'], '%Y-%m-%d').date()
                if (datetime.now().date() - dob).days < (18 * 365):
                    if not p.get('parentesco'):
                        errors.append(f"Persona {i+1}: Es menor de edad y falta el parentesco")
            
            if errors:
                for err in errors: st.error(err)
                st.stop()
                
            client = get_client()
            if client:
                # Preparar estructura de datos completa
                data = [{
                    'referencia': ref,
                    'fechaContrato': f_cont.strftime('%Y-%m-%d'),
                    'fechaEntrada': f_ent.strftime('%Y-%m-%dT%H:%M:%S'),
                    'fechaSalida': f_sal.strftime('%Y-%m-%dT%H:%M:%S'),
                    'numPersonas': len(lista_personas_data),
                    'numHabitaciones': num_hab,
                    'internet': tiene_internet,
                    'pago': {
                        'tipoPago': tipo_pago, 
                        'medioPago': medio_pago,
                        'fechaPago': f_pago.strftime('%Y-%m-%d'),
                        'titular': p_titular,
                        'caducidadTarjeta': p_caducidad
                    },
                    'personas': lista_personas_data
                }]
                
                xml_content = client.generate_alta_parte_hospedaje_xml(cod_est, data)
                res = client.comunicacion(cod_arrendador, app_name, 'A', tipo_com[:2], xml_content)
                
                st.success("Operación procesada")
                st.json(res)
                
                with st.expander("Ver XML Generado"):
                    st.code(xml_content.decode('utf-8'), language='xml')

# --- TAB: Consultas ---
with tabs[1]:
    st.header("Consulta de Lotes y Comunicaciones")
    op_consulta = st.radio("Buscar por:", ["Número de Lote", "Código de Comunicación"])
    search_val = st.text_input("Valor a buscar")
    
    if st.button("Consultar"):
        client = get_client()
        if op_consulta == "Número de Lote":
            res = client.consulta_lote([search_val])
        else:
            res = client.consulta_comunicacion([search_val])
        
        st.write("### Resultado")
        st.json(res)

# --- TAB: Anulaciones ---
with tabs[2]:
    st.header("Anulación de Comunicaciones")
    lote_anular = st.text_input("Número de Lote a anular completamente")
    
    confirmar = st.checkbox("Estoy seguro de que deseo anular este lote de forma irreversible.")
    
    if st.button("Anular Lote", type="primary", disabled=not confirmar):
        if lote_anular:
            client = get_client()
            res = client.anulacion_lote(lote_anular)
            st.write("### Resultado")
            st.json(res)
            if "error" not in res:
                st.success("Solicitud de anulación enviada y procesada.")
        else:
            st.error("Debes introducir un número de lote válido.")

# --- TAB: Catálogo ---
with tabs[3]:
    st.header("Consulta de Catálogos")
    cat_target = st.selectbox("Catálogo", [
        "SEXO", 
        "TIPO_DOCUMENTO", 
        "TIPO_MARCA_VEHICULO", 
        "TIPO_PAGO", 
        "TIPO_PARENTESCO", 
        "TIPO_COLOR", 
        "TIPO_ESTABLECIMIENTO", 
        "TIPO_VEHICULO"
    ])
    
    col_btn1, col_btn2 = st.columns(2)
    
    with col_btn1:
        if st.button("🌐 Cargar del Ministerio"):
            client = get_client()
            res = client.catalogo(cat_target)
            
            if "error" in res:
                st.error(res["error"])
                if res.get("details"):
                    st.info(res["details"])
                
                if res.get("fallback"):
                    st.warning(f"Usando datos de respaldo (Offline) para {cat_target}")
                    df = pd.DataFrame(res["local_data"])
                    st.dataframe(df, use_container_width=True)
            else:
                st.success(f"Datos de {cat_target} cargados desde el servidor")
                try:
                    # Parse data
                    if 'respuesta' in res and 'resultado' in res['respuesta']:
                        data = res['respuesta']['resultado'].get('tupla', [])
                        parsed_data = [{'codigo': t['codigo'], 'descripcion': t['descripcion']} for t in data]
                    else:
                        parsed_data = res.get('data', [])
                    
                    df = pd.DataFrame(parsed_data)
                    
                    if not df.empty:
                        st.dataframe(df, use_container_width=True)
                        
                        # Save to DB automatically
                        if DB_AVAILABLE:
                            try:
                                get_db().save_catalogo(cat_target, parsed_data)
                                st.success(f"✅ Catálogo {cat_target} sincronizado en NeonDB.")
                            except Exception as db_e:
                                st.error(f"Error al guardar en BBDD: {db_e}")
                    else:
                        st.write("El catálogo está vacío o no se ha podido procesar.")
                        st.json(res)
                except Exception as e:
                    st.json(res)
                    st.error(f"Error al procesar el formato de respuesta: {e}")

    with col_btn2:
        if st.button("🗄️ Cargar desde NeonDB"):
            if not DB_AVAILABLE:
                st.error("La conexión a la base de datos no está disponible.")
            else:
                try:
                    db_data = get_db().get_catalogo(cat_target)
                    if db_data:
                        df = pd.DataFrame(db_data)
                        st.success(f"Catálogo {cat_target} cargado desde NeonDB (Última act: {db_data[0].get('last_updated')})")
                        st.dataframe(df, use_container_width=True)
                    else:
                        st.warning(f"El catálogo {cat_target} no está en la base de datos todavía. Por favor cárgalo desde el Ministerio primero.")
                except Exception as db_e:
                    st.error(f"Error al leer de la BBDD: {db_e}")

# --- Footer ---
st.divider()
st.caption("MIR Hospedajes Python Client - Desarrollado para el cumplimiento del RD 933/2021.")
