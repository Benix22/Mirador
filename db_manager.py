import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

class DBManager:
    def __init__(self):
        self.db_url = os.getenv("DATABASE_URL")
        if not self.db_url:
            raise ValueError("DATABASE_URL environment variable is not set")

    def get_connection(self):
        return psycopg2.connect(self.db_url)

    def init_db(self):
        """Initializes the database schema if it doesn't exist."""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS catalogos (
                        id SERIAL PRIMARY KEY,
                        tenant_id VARCHAR(50) DEFAULT 'GLOBAL',
                        tipo_catalogo VARCHAR(50) NOT NULL,
                        codigo VARCHAR(50) NOT NULL,
                        descripcion VARCHAR(255) NOT NULL,
                        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(tenant_id, tipo_catalogo, codigo)
                    );
                """)
            conn.commit()
        finally:
            conn.close()

    def save_catalogo(self, tipo_catalogo, items, tenant_id="GLOBAL"):
        """
        Saves or updates catalog items in the database.
        `items` should be a list of dictionaries with 'codigo' and 'descripcion'.
        """
        if not items:
            return

        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                # Use execute_values or executemany. For simplicity and upsert, we loop or use bulk
                for item in items:
                    codigo = item.get('codigo')
                    descripcion = item.get('descripcion')
                    if codigo is not None and descripcion is not None:
                        cur.execute("""
                            INSERT INTO catalogos (tenant_id, tipo_catalogo, codigo, descripcion, last_updated)
                            VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                            ON CONFLICT (tenant_id, tipo_catalogo, codigo) 
                            DO UPDATE SET 
                                descripcion = EXCLUDED.descripcion,
                                last_updated = CURRENT_TIMESTAMP;
                        """, (tenant_id, tipo_catalogo, codigo, descripcion))
            conn.commit()
        finally:
            conn.close()

    def save_catalogo_batch(self, tipo_catalogo, items, tenant_id="GLOBAL"):
        from psycopg2.extras import execute_values
        if not items: return
        
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                values = [(tenant_id, tipo_catalogo, item.get('codigo'), item.get('descripcion')) 
                          for item in items if item.get('codigo') and item.get('descripcion')]
                execute_values(cur, """
                    INSERT INTO catalogos (tenant_id, tipo_catalogo, codigo, descripcion, last_updated)
                    VALUES %s
                    ON CONFLICT (tenant_id, tipo_catalogo, codigo) 
                    DO UPDATE SET 
                        descripcion = EXCLUDED.descripcion,
                        last_updated = CURRENT_TIMESTAMP;
                """, values, template="(%s, %s, %s, %s, CURRENT_TIMESTAMP)")
            conn.commit()
        finally:
            conn.close()

    def get_catalogo(self, tipo_catalogo, tenant_id="GLOBAL"):
        """
        Retrieves a catalog from the database.
        Returns a list of dicts: [{'codigo': ..., 'descripcion': ...}, ...]
        """
        conn = self.get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT codigo, descripcion, last_updated 
                    FROM catalogos 
                    WHERE tenant_id = %s AND tipo_catalogo = %s
                    ORDER BY codigo ASC;
                """, (tenant_id, tipo_catalogo))
                results = cur.fetchall()
                # Convert RealDictRow to standard dict
                return [dict(row) for row in results]
        finally:
            conn.close()

# Singleton instance for easy importing
db = None

def get_db():
    global db
    if db is None:
        db = DBManager()
    return db
