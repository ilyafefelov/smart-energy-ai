"""
Database connection and schema management for Dagster asset results.
Uses PostgreSQL for persistent storage.
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)

LEGACY_UNSCOPED_TENANT_ID = "__legacy_unscoped__"


class Database:
    """PostgreSQL database connection manager."""
    
    def __init__(self):
        self.host = os.getenv("DB_HOST", "localhost")
        self.port = os.getenv("DB_PORT", "5432")
        self.user = os.getenv("DB_USER", "dagster")
        self.password = os.getenv("DB_PASSWORD", "dagster")
        self.database = os.getenv("DB_NAME", "dagster")
    
    def get_connection(self):
        """Create a new connection."""
        return psycopg2.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.database,
            cursor_factory=RealDictCursor
        )
    
    @contextmanager
    def get_connection_context(self):
        """Context manager for database connections."""
        conn = self.get_connection()
        try:
            yield conn
        finally:
            conn.close()
    
    def init_schema(self):
        """Initialize the database schema."""
        with self.get_connection_context() as conn:
            with conn.cursor() as cur:
                # Asset results table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS asset_results (
                        id SERIAL PRIMARY KEY,
                        asset_name VARCHAR(255) NOT NULL,
                        run_id VARCHAR(255),
                        tenant_id VARCHAR(128) NOT NULL,
                        materialization_time TIMESTAMP DEFAULT NOW(),
                        data JSONB,
                        status VARCHAR(50) DEFAULT 'success',
                        error_message TEXT,
                        execution_time_ms INTEGER,
                        UNIQUE(asset_name, run_id)
                    )
                """)
                cur.execute("""
                    ALTER TABLE asset_results
                    ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(128)
                """)
                cur.execute("""
                    UPDATE asset_results
                    SET tenant_id = LOWER(BTRIM(data->>'tenant_id'))
                    WHERE (tenant_id IS NULL OR BTRIM(tenant_id) = '')
                      AND data IS NOT NULL
                      AND NULLIF(BTRIM(data->>'tenant_id'), '') IS NOT NULL
                """)
                cur.execute("""
                    UPDATE asset_results
                    SET tenant_id = %s
                    WHERE tenant_id IS NULL OR BTRIM(tenant_id) = ''
                """, (LEGACY_UNSCOPED_TENANT_ID,))
                cur.execute("""
                    ALTER TABLE asset_results
                    ALTER COLUMN tenant_id SET NOT NULL
                """)
                
                # Index for fast lookups
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_asset_results_name 
                    ON asset_results(asset_name)
                """)
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_asset_results_time 
                    ON asset_results(materialization_time DESC)
                """)
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_asset_results_tenant_id
                    ON asset_results(tenant_id)
                """)
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_asset_results_tenant_asset_time
                    ON asset_results(tenant_id, asset_name, materialization_time DESC)
                """)
                
                conn.commit()
                logger.info("Database schema initialized")
    
    def test_connection(self) -> bool:
        """Test the database connection."""
        try:
            with self.get_connection_context() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    return True
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            return False
    
    def execute(self, query: str, params: tuple = None):
        """Execute a query."""
        with self.get_connection_context() as conn:
            with conn.cursor() as cur:
                if params:
                    cur.execute(query, params)
                else:
                    cur.execute(query)
                
                if query.strip().upper().startswith('SELECT'):
                    rows = cur.fetchall()
                    return [dict(r) for r in rows]
                else:
                    conn.commit()
                    return []
    
    def execute_one(self, query: str, params: tuple = None):
        """Execute a query and return a single result."""
        results = self.execute(query, params)
        return results[0] if results else None
    
    def insert(self, query: str, params: tuple = None):
        """Insert and return last row id."""
        with self.get_connection_context() as conn:
            with conn.cursor() as cur:
                if params:
                    cur.execute(query, params)
                else:
                    cur.execute(query)
                conn.commit()
                return cur.lastrowid


# Singleton instance
_db = None

def get_database() -> Database:
    """Get the database singleton."""
    global _db
    if _db is None:
        _db = Database()
        _db.init_schema()
    return _db
