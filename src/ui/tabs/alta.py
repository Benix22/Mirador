import streamlit as st
import pandas as pd
from datetime import datetime
from src.ui.utils import load_catalog, get_client
from src.core.db_manager import get_db
from src.core.iso_countries import get_iso_countries

def render_alta_tab(config):
    st.header("Envío de Comunicaciones (Alta)")
    tipo_com = st.selectbox("Tipo de Comunicación", [
        "PV - Partes de Viajeros", "RH - Reservas de Hospedaje",
        "AV - Alquiler de Vehículos", "RV - Reservas de Vehículos"
    ])
    st.divider()
    
    st.subheader("📋 Datos del Contrato")
    with st.form("main_data_form"):
        c1, c2 = st.columns(2)
        with c1:
            ref = st.text_input("🔗 Referencia del Contrato", f"REF-{datetime.now().strftime('%Y%m%d%H%M%S')}")
            f_cont = st.date_input("📅 Fecha Contrato", datetime.now())
            num_hab = st.number_input("🏨 Número de Habitaciones", min_value=1, value=1)
        with c2:
            f_ent = st.datetime_input("🛫 Fecha Entrada/Inicio", datetime.now())
            f_sal = st.datetime_input("🛬 Fecha Salida/Fin", datetime.now())
            tiene_internet = st.checkbox("🌐 ¿Tiene acceso a Internet?", value=False)
        
        st.divider()
        st.write("💳 Datos de Pago")
        p_col1, p_col2 = st.columns([1, 3])
        with p_col1:
            cat_pago = load_catalog("TIPO_PAGO", ["EF", "TC", "TR", "OT"], tenant_id="GLOBAL")
            tipo_pago = st.selectbox("💰 Tipo de Pago", options=list(cat_pago.keys()), format_func=lambda x: cat_pago[x])
            f_pago = st.date_input("📆 Fecha de Pago", datetime.now())
            p_caducidad = st.text_input("💳 Caducidad Tarjeta", value="", placeholder="MM/AAAA")
        with p_col2:
            medio_pago = st.text_input("🆔 Identificación del Medio de Pago", value="")
            p_titular = st.text_input("👤 Nombre Completo del Titular", "")
        
        st.form_submit_button("Guardar Datos Generales")

    st.write("---")
    t_col1, t_col2 = st.columns([3, 1], vertical_alignment="center")
    with t_col1:
        st.markdown(f"### 👥 Viajeros: **{len(st.session_state.viajeros)}**")
    with t_col2:
        c_add, c_rem = st.columns(2)
        with c_add:
            if st.button("➕", help="Añadir viajero", use_container_width=True):
                st.session_state.viajeros.append({'nombre': '', 'apellido1': ''})
                st.rerun()
        with c_rem:
            if st.button("🗑️", help="Quitar viajero", use_container_width=True) and len(st.session_state.viajeros) > 1:
                st.session_state.viajeros.pop()
                st.rerun()

    with st.form("travelers_form"):
        lista_personas_data = []
        for i, viajero in enumerate(st.session_state.viajeros):
            with st.expander(f"👤 Persona {i+1}: {viajero.get('nombre', '')} {viajero.get('apellido1', '')}", expanded=(i==len(st.session_state.viajeros)-1)):
                v1, v2 = st.columns([2, 1])
                with v1:
                    p_nom = st.text_input(f"Nombre P{i+1}", viajero.get('nombre', ''), key=f"nom_{i}")
                    p_ap1 = st.text_input(f"Primer Apellido P{i+1}", viajero.get('apellido1', ''), key=f"ap1_{i}")
                    is_nif = st.session_state.get(f"tdoc_{i}") == "NIF"
                    p_ap2 = st.text_input(f"Segundo Apellido P{i+1}" + (" ⚠️" if is_nif else ""), "", key=f"ap2_{i}")
                    is_nie = st.session_state.get(f"tdoc_{i}") == "NIE"
                    p_soporte = st.text_input(f"Número Soporte P{i+1}" + (" ⚠️" if is_nif or is_nie else ""), "", key=f"soporte_{i}")
                with v2:
                    cat_tdoc = load_catalog("TIPO_DOCUMENTO", ["NIF", "NIE", "PAS", "ID"], tenant_id="GLOBAL")
                    p_tdoc = st.selectbox(f"Tipo Doc P{i+1}", options=list(cat_tdoc.keys()), format_func=lambda x: cat_tdoc[x], key=f"tdoc_{i}")
                    p_doc = st.text_input(f"Documento P{i+1}", "", key=f"doc_{i}")
                    cat_sexo = load_catalog("SEXO", ["M", "F", "X"], tenant_id="GLOBAL")
                    p_sexo = st.selectbox(f"Sexo P{i+1}", options=list(cat_sexo.keys()), format_func=lambda x: cat_sexo[x], key=f"sexo_{i}")
                    p_fnac = st.date_input(f"Fecha Nacimiento P{i+1}", datetime(1980, 1, 1), key=f"fnac_{i}")
                
                iso_countries = get_iso_countries()
                country_list = list(iso_countries.keys())
                v3, v4 = st.columns(2)
                with v3:
                    p_nac = st.selectbox(f"Nacionalidad P{i+1}", options=country_list, index=country_list.index("ESP") if "ESP" in country_list else 0, format_func=lambda x: f"{x} - {iso_countries[x]}", key=f"nac_{i}")
                with v4:
                    cat_parentesco = load_catalog("TIPO_PARENTESCO", ["", "P", "M", "A", "H", "O"], tenant_id="GLOBAL")
                    p_parentesco = st.selectbox(f"Parentesco P{i+1}", options=list(cat_parentesco.keys()), format_func=lambda x: cat_parentesco[x] if x else "Ninguno", key=f"par_{i}")
                
                c1, c2 = st.columns(2)
                with c1: p_tel = st.text_input(f"Teléfono P{i+1}", "", key=f"tel_{i}")
                with c2: p_email = st.text_input(f"Correo Electrónico P{i+1}", "", key=f"email_{i}")
                
                d1, d2, d3, d4 = st.columns([2, 2, 1, 1])
                with d1: d_dir = st.text_input(f"Dirección P{i+1}", "", key=f"dir_{i}")
                with d2:
                    cat_mun = load_catalog("MUNICIPIO", ["28079"], tenant_id="GLOBAL")
                    d_mun = st.selectbox(f"Municipio P{i+1}", options=list(cat_mun.keys()), format_func=lambda x: cat_mun[x] if x in cat_mun else x, key=f"mun_{i}")
                with d3: d_cp = st.text_input(f"CP P{i+1}", "", key=f"cp_{i}")
                with d4: d_pais = st.selectbox(f"País P{i+1}", options=country_list, index=country_list.index("ESP") if "ESP" in country_list else 0, format_func=lambda x: f"{x} - {iso_countries[x]}", key=f"dpais_{i}")
                
                st.session_state.viajeros[i].update({'nombre': p_nom, 'apellido1': p_ap1})
                lista_personas_data.append({
                    'rol': "VI", 'nombre': p_nom, 'apellido1': p_ap1, 'apellido2': p_ap2,
                    'tipoDocumento': p_tdoc, 'numeroDocumento': p_doc, 'soporteDocumento': p_soporte,
                    'fechaNacimiento': p_fnac.strftime('%Y-%m-%d'), 'nacionalidad': p_nac, 'sexo': p_sexo,
                    'telefono': p_tel, 'correo': p_email, 'parentesco': p_parentesco,
                    'direccion': {'direccion': d_dir, 'codigoMunicipio': d_mun, 'codigoPostal': d_cp, 'pais': d_pais}
                })
        
        st.divider()
        if st.form_submit_button("🚀 ENVIAR COMUNICACIÓN A MIR", type="primary", use_container_width=True):
            # Validations... (simplified for now but should be here)
            client = get_client(config)
            if client:
                data = [{
                    'referencia': ref, 'fechaContrato': f_cont.strftime('%Y-%m-%d'),
                    'fechaEntrada': f_ent.strftime('%Y-%m-%dT%H:%M:%S'), 'fechaSalida': f_sal.strftime('%Y-%m-%dT%H:%M:%S'),
                    'numPersonas': len(lista_personas_data), 'numHabitaciones': num_hab, 'internet': tiene_internet,
                    'pago': {'tipoPago': tipo_pago, 'medioPago': medio_pago, 'fechaPago': f_pago.strftime('%Y-%m-%d'), 'titular': p_titular, 'caducidadTarjeta': p_caducidad},
                    'personas': lista_personas_data
                }]
                xml_content = client.generate_alta_parte_hospedaje_xml(config['cod_est'], data)
                res = client.comunicacion(config['cod_arrendador'], config['app_name'], 'A', tipo_com[:2], xml_content)
                
                if "error" not in res:
                    get_db().save_comunicacion_completa(config['tenant_id'], data, res)
                    st.success("✅ Comunicación enviada y guardada.")
                
                st.divider()
                if "error" in res:
                    st.error(f"❌ Error: {res['error']}")
                else:
                    resp_header = res.get('respuesta', {})
                    st.metric("📦 Número de Lote", resp_header.get('lote', 'N/A'))
                    if res.get('resultado'):
                        st.dataframe(pd.DataFrame(res['resultado']), use_container_width=True)
                
                with st.expander("🛠️ Depuración"):
                    st.code(xml_content.decode('utf-8'), language='xml')
                    st.json(res)
