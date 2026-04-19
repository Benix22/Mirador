import base64
import io
import zipfile
import lxml.etree as ET
from zeep import Client, Transport, helpers
from requests import Session
import requests
import urllib3
import os
from datetime import datetime

# Silence insecure request warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class TLSAdapter(requests.adapters.HTTPAdapter):
    def __init__(self, verify=True, cert_path=None, key_path=None, **kwargs):
        self.verify = verify
        self.cert_path = cert_path
        self.key_path = key_path
        super().__init__(**kwargs)

    def init_poolmanager(self, *args, **kwargs):
        import ssl
        ctx = ssl.create_default_context()
        ctx.set_ciphers('DEFAULT@SECLEVEL=1')
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        
        if not self.verify:
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            
        if self.cert_path:
            ctx.load_cert_chain(certfile=self.cert_path, keyfile=self.key_path)
            
        kwargs['ssl_context'] = ctx
        return super(TLSAdapter, self).init_poolmanager(*args, **kwargs)

class HospedajesClient:
    def __init__(self, wsdl_path, endpoint=None, username=None, password=None, cert_path=None, key_path=None, verify_ssl=True, mock_mode=False):
        self.wsdl_path = wsdl_path
        self.endpoint = endpoint
        self.mock_mode = mock_mode
        self.client = None
        
        if not mock_mode:
            session = Session()
            adapter = TLSAdapter(verify=verify_ssl, cert_path=cert_path, key_path=key_path)
            session.mount('https://', adapter)
            session.verify = verify_ssl
            
            if not verify_ssl:
                session.trust_env = False
                
            if username and password:
                session.auth = requests.auth.HTTPBasicAuth(username, password)
            
            transport = Transport(session=session, timeout=15)
            self.client = Client(wsdl_path, transport=transport)
            
            if endpoint:
                self.service = self.client.create_service(
                    '{http://www.soap.servicios.hospedajes.mir.es/comunicacion}ComunicacionPortSoap11',
                    endpoint
                )
            else:
                self.service = self.client.service
            
            self._session = session
        else:
            self._session = None

    def close(self):
        if self._session:
            self._session.close()

    def _create_zip_base64(self, xml_content, filename="solicitud.xml"):
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
            zip_file.writestr(filename, xml_content)
        return base64.b64encode(zip_buffer.getvalue()).decode("utf-8")

    def generate_alta_parte_hospedaje_xml(self, cod_establecimiento, comunicaciones):
        # XML Schema defined namespaces
        NS_ALTA = "http://www.neg.hospedajes.mir.es/altaParteHospedaje"
        NS_MAP = {"alta": NS_ALTA}
        
        # Root element
        root = ET.Element(f"{{{NS_ALTA}}}peticion", nsmap=NS_MAP)
        solicitud = ET.SubElement(root, "solicitud")
        
        # 1. codigoEstablecimiento (Mandatory)
        ET.SubElement(solicitud, "codigoEstablecimiento").text = cod_establecimiento
        
        # 2. comunicacion (Mandatory, 1 to unbounded)
        for com in comunicaciones:
            com_el = ET.SubElement(solicitud, "comunicacion")
            
            # 2.1 contrato (Mandatory)
            contrato = ET.SubElement(com_el, "contrato")
            ET.SubElement(contrato, "referencia").text = com['referencia']
            ET.SubElement(contrato, "fechaContrato").text = com['fechaContrato']
            ET.SubElement(contrato, "fechaEntrada").text = com['fechaEntrada']
            ET.SubElement(contrato, "fechaSalida").text = com['fechaSalida']
            ET.SubElement(contrato, "numPersonas").text = str(com['numPersonas'])
            
            # numHabitaciones (Optional but recommended)
            if 'numHabitaciones' in com:
                ET.SubElement(contrato, "numHabitaciones").text = str(com['numHabitaciones'])
            
            # internet (Optional but recommended, Rule: 1 for Yes, 0 for No)
            if 'internet' in com:
                ET.SubElement(contrato, "internet").text = "1" if com['internet'] else "0"
                
            # 2.1.1 pago (Mandatory inside contrato)
            p_data = com.get('pago', {})
            pago = ET.SubElement(contrato, "pago")
            ET.SubElement(pago, "tipoPago").text = p_data.get('tipoPago', 'EF')
            if p_data.get('fechaPago'):
                ET.SubElement(pago, "fechaPago").text = p_data['fechaPago']
            if p_data.get('medioPago'):
                ET.SubElement(pago, "medioPago").text = p_data['medioPago']
            if p_data.get('titular'):
                ET.SubElement(pago, "titular").text = p_data['titular']
            if p_data.get('caducidadTarjeta'):
                ET.SubElement(pago, "caducidadTarjeta").text = p_data['caducidadTarjeta']

            # 2.2 persona (Mandatory inside comunicacion, 1 to unbounded)
            for p in com['personas']:
                pers = ET.SubElement(com_el, "persona")
                ET.SubElement(pers, "rol").text = p['rol']
                ET.SubElement(pers, "nombre").text = p['nombre']
                ET.SubElement(pers, "apellido1").text = p['apellido1']
                if p.get('apellido2'):
                    ET.SubElement(pers, "apellido2").text = p['apellido2']
                
                if p.get('tipoDocumento'):
                    ET.SubElement(pers, "tipoDocumento").text = p['tipoDocumento']
                if p.get('numeroDocumento'):
                    ET.SubElement(pers, "numeroDocumento").text = p['numeroDocumento']
                if p.get('soporteDocumento'):
                    ET.SubElement(pers, "soporteDocumento").text = p['soporteDocumento']
                
                ET.SubElement(pers, "fechaNacimiento").text = p['fechaNacimiento']
                if p.get('nacionalidad'):
                    ET.SubElement(pers, "nacionalidad").text = p['nacionalidad']
                if p.get('sexo'):
                    ET.SubElement(pers, "sexo").text = p['sexo']
                
                # 2.2.1 direccion (Mandatory inside persona)
                dir_node = ET.SubElement(pers, "direccion")
                ET.SubElement(dir_node, "direccion").text = p['direccion']['direccion']
                
                if p['direccion'].get('codigoMunicipio'):
                    ET.SubElement(dir_node, "codigoMunicipio").text = p['direccion']['codigoMunicipio']
                    
                ET.SubElement(dir_node, "codigoPostal").text = p['direccion']['codigoPostal']
                ET.SubElement(dir_node, "pais").text = p['direccion']['pais']

                if p.get('telefono'):
                    ET.SubElement(pers, "telefono").text = p['telefono']
                if p.get('correo'):
                    ET.SubElement(pers, "correo").text = p['correo']
                if p.get('parentesco'):
                    ET.SubElement(pers, "parentesco").text = p['parentesco']

        return ET.tostring(root, encoding='UTF-8', xml_declaration=True, pretty_print=True)

    def comunicacion(self, cod_arrendador, aplicacion, tipo_operacion, tipo_comunicacion, xml_content):
        payload = self._create_zip_base64(xml_content)
        
        # HEADER according to the server's requested signature:
        # codigoArrendador, aplicacion, tipoOperacion, tipoComunicacion
        cabecera = {
            'codigoArrendador': cod_arrendador,
            'aplicacion': aplicacion,
            'tipoOperacion': tipo_operacion,
            'tipoComunicacion': tipo_comunicacion
        }
        
        if self.mock_mode:
            return {"status": "MOCK", "cabecera": cabecera, "preview": payload[:100]}
            
        try:
            response = self.service.comunicacion(peticion={'cabecera': cabecera, 'solicitud': payload})
            return helpers.serialize_object(response)
        except Exception as e:
            return {"error": str(e)}

    def consulta_lote(self, lista_lotes):
        if self.mock_mode: return {"status": "MOCK", "lotes": lista_lotes}
        try:
            # En el WSDL: consultaLoteRequest -> codigosLote -> lote[]
            response = self.service.consultaLote(codigosLote={'lote': lista_lotes})
            return helpers.serialize_object(response)
        except Exception as e:
            return {"error": str(e)}

    def consulta_comunicacion(self, lista_codigos):
        if self.mock_mode: return {"status": "MOCK", "codigos": lista_codigos}
        try:
            # En el WSDL: consultaComunicacionRequest -> codigos -> codigo[]
            response = self.service.consultaComunicacion(codigos={'codigo': lista_codigos})
            return helpers.serialize_object(response)
        except Exception as e:
            return {"error": str(e)}

    def anulacion_lote(self, numero_lote):
        if self.mock_mode: return {"status": "MOCK", "anulado": numero_lote}
        try:
            response = self.service.anulacionLote(lote=numero_lote)
            return helpers.serialize_object(response)
        except Exception as e:
            return {"error": str(e)}

    def catalogo(self, nombre_catalogo):
        if self.mock_mode: return {"status": "MOCK", "data": self.get_local_catalogo(nombre_catalogo)}
        
        # Usamos los nombres oficiales de la documentación
        target = nombre_catalogo
        
        try:
            response = self.service.catalogo(peticion={'catalogo': target})
            return helpers.serialize_object(response)
        except Exception as e:
            error_msg = str(e)
            if "502" in error_msg or "Proxy Error" in error_msg:
                return {
                    "error": "Error 502: El servidor del Ministerio no responde (Proxy Error).",
                    "details": "Esto es común en el entorno de pruebas (PRE). Inténtalo más tarde.",
                    "fallback": True,
                    "local_data": self.get_local_catalogo(nombre_catalogo)
                }
            if "401" in error_msg or "Unauthorized" in error_msg:
                return {
                    "error": "Error 401: No autorizado.",
                    "details": "Tus credenciales (Usuario/Password) o tu Certificado no están autorizados para PRODUCCIÓN. Revisa el archivo .env.",
                    "fallback": True,
                    "local_data": self.get_local_catalogo(nombre_catalogo)
                }
            return {"error": error_msg}
        
        return helpers.serialize_object(response)

    def get_local_catalogo(self, nombre_catalogo):
        # Datos de respaldo basados en la documentación oficial
        catalogos = {
            "SEXO": [
                {"codigo": "M", "descripcion": "VARÓN"},
                {"codigo": "F", "descripcion": "MUJER"},
                {"codigo": "X", "descripcion": "NO BINARIO / OTROS"}
            ],
            "TIPO_DOCUMENTO": [
                {"codigo": "NIF", "descripcion": "NIF / DNI"},
                {"codigo": "NIE", "descripcion": "NIE"},
                {"codigo": "PAS", "descripcion": "PASAPORTE"},
                {"codigo": "ID", "descripcion": "DOCUMENTO IDENTIDAD PAÍS"}
            ],
            "TIPO_PARENTESCO": [
                {"codigo": "P", "descripcion": "PADRE"},
                {"codigo": "M", "descripcion": "MADRE"},
                {"codigo": "A", "descripcion": "ABUELO/A"},
                {"codigo": "H", "descripcion": "HIJO/A"},
                {"codigo": "T", "descripcion": "TUTOR/A"},
                {"codigo": "O", "descripcion": "OTROS"}
            ],
            "TIPO_PAGO": [
                {"codigo": "EF", "descripcion": "EFECTIVO"},
                {"codigo": "TC", "descripcion": "TARJETA CRÉDITO"},
                {"codigo": "TR", "descripcion": "TRANSFERENCIA"},
                {"codigo": "OT", "descripcion": "OTROS"}
            ]
        }
        return catalogos.get(nombre_catalogo, [])
