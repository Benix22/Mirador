import os
import csv
import requests
from dotenv import load_dotenv
from db_manager import get_db

def import_municipios():
    load_dotenv(override=True)
    db = get_db()
    
    url = "https://raw.githubusercontent.com/codeforspain/ds-organizacion-administrativa/master/data/municipios.csv"
    print(f"Downloading data from {url}...")
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        # Ensure utf-8 decoding
        content = response.content.decode('utf-8')
        
        reader = csv.DictReader(content.splitlines())
        
        items = []
        for row in reader:
            # We need the 5 digit code and the name
            codigo = row.get('municipio_id')
            nombre = row.get('nombre')
            
            if codigo and nombre:
                items.append({
                    'codigo': codigo,
                    'descripcion': nombre
                })
        
        print(f"Found {len(items)} municipalities. Inserting into NeonDB...")
        if items:
            db.save_catalogo_batch('MUNICIPIO', items)
            print("Successfully inserted municipalities.")
        else:
            print("No valid rows found.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    import_municipios()
