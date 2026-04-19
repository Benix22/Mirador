from hospedajes_client import HospedajesClient
import os
from dotenv import load_dotenv
import logging
import sys

# Enable logging to see the request
import http.client as http_client
http_client.HTTPConnection.debuglevel = 1

logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)
requests_log = logging.getLogger("requests.packages.urllib3")
requests_log.setLevel(logging.DEBUG)
requests_log.propagate = True

load_dotenv(override=True)

def test_catalogo_xml():
    wsdl = "comunicacion.wsdl"
    # Use a dummy endpoint to avoid real network call if we just want to see XML,
    # but we want to see the error too if possible.
    endpoint = os.getenv("MIR_ENDPOINT_PRE")
    user = os.getenv("MIR_USER")
    pwd = os.getenv("MIR_PASSWORD")
    
    client = HospedajesClient(
        wsdl_path=wsdl,
        endpoint=endpoint,
        username=user,
        password=pwd,
        verify_ssl=False, # As in .env
        mock_mode=False
    )
    
    print("\n--- TEST: PAISES (with mapping to PAIS) ---")
    res = client.catalogo("PAISES")
    print(f"Result keys: {res.keys() if isinstance(res, dict) else 'Zeep Object'}")
    if isinstance(res, dict) and "fallback" in res:
        print("MOCK FALLBACK ACTIVE")
    print(f"Result summary: {str(res)[:200]}...")

if __name__ == "__main__":
    test_catalogo_xml()
