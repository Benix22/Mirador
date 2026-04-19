import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

class DBManager:
    def __init__(self):
        self.db_url = os.getenv("DATABASE_URL")
        if not self.db_url:
            raise ValueError(" DATABASE_URL environment variable is not set")

    def get_connection(self):
        return psycopg2.connect(self.db_url)

    def init_db(self):
        """Initializes the database schema if it doesn't exist."""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        email VARCHAR(255) UNIQUE NOT NULL,
                        password_hash VARCHAR(255) NOT NULL,
                        role VARCHAR(50) DEFAULT 'user',
                        subscription_active BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );

                    CREATE TABLE IF NOT EXISTS tenants (
                        tenant_id VARCHAR(50) PRIMARY KEY,
                        owner_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                        nombre VARCHAR(100) NOT NULL,
                        mir_user VARCHAR(50) NOT NULL,
                        mir_password VARCHAR(100) NOT NULL,
                        arrendador_code VARCHAR(50) NOT NULL,
                        establecimiento_code VARCHAR(50) NOT NULL,
                        p12_path TEXT,
                        p12_password VARCHAR(100),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );

                    -- For existing DBs, ensure the column exists
                    ALTER TABLE tenants ADD COLUMN IF NOT EXISTS owner_id INTEGER REFERENCES users(id) ON DELETE SET NULL;

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

    def get_tenants(self, owner_id=None):
        """Returns a list of tenants. If owner_id is provided, filters by owner."""
        conn = self.get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                if owner_id:
                    cur.execute("SELECT tenant_id, nombre FROM tenants WHERE owner_id = %s ORDER BY nombre ASC;", (owner_id,))
                else:
                    cur.execute("SELECT tenant_id, nombre FROM tenants ORDER BY nombre ASC;")
                return [dict(row) for row in cur.fetchall()]
        finally:
            conn.close()

    def get_tenant_config(self, tenant_id):
        """Returns the full configuration for a specific tenant."""
        conn = self.get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM tenants WHERE tenant_id = %s;", (tenant_id,))
                res = cur.fetchone()
                return dict(res) if res else None
        finally:
            conn.close()

    def save_tenant(self, data):
        """Saves or updates a tenant configuration."""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO tenants (
                        tenant_id, owner_id, nombre, mir_user, mir_password, 
                        arrendador_code, establecimiento_code, p12_path, p12_password
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (tenant_id) DO UPDATE SET
                        owner_id = COALESCE(EXCLUDED.owner_id, tenants.owner_id),
                        nombre = EXCLUDED.nombre,
                        mir_user = EXCLUDED.mir_user,
                        mir_password = EXCLUDED.mir_password,
                        arrendador_code = EXCLUDED.arrendador_code,
                        establecimiento_code = EXCLUDED.establecimiento_code,
                        p12_path = EXCLUDED.p12_path,
                        p12_password = EXCLUDED.p12_password;
                """, (
                    data['tenant_id'], data.get('owner_id'), data['nombre'], data['mir_user'], data['mir_password'],
                    data['arrendador_code'], data['establecimiento_code'], 
                    data.get('p12_path'), data.get('p12_password')
                ))
            conn.commit()
        finally:
            conn.close()

    # --- User Management ---
    
    def create_user(self, email, password_hash, role='user', subscription_active=False):
        conn = self.get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    INSERT INTO users (email, password_hash, role, subscription_active)
                    VALUES (%s, %s, %s, %s) RETURNING id;
                """, (email, password_hash, role, subscription_active))
                res = cur.fetchone()
            conn.commit()
            return res['id'] if res else None
        finally:
            conn.close()

    def get_user_by_email(self, email):
        conn = self.get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM users WHERE email = %s;", (email,))
                res = cur.fetchone()
                return dict(res) if res else None
        finally:
            conn.close()

# Singleton instance for easy importing
db = None

def get_db():
    global db
    if db is None:
        db = DBManager()
    return db
