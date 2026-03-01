"""
Database connection and schema management for Dagster asset results.
Uses SQLite for persistent storage (simple, no setup required).
"""

import os
import sqlite3
import json
import logging
from datetime import datetime
from contextlib import contextmanager
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class Database:
    """SQLite database connection manager."""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), 
                '..',
                'data', 
                'dagster_assets.db'
            )
        self.db_path = os.path.abspath(db_path)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
    
    def _connect(self):
        """Create a new connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        conn = self._connect()
        try:
            yield conn
        finally:
            conn.close()
    
    def init_schema(self):
        """Initialize the database schema."""
        with self.get_connection() as conn:
            cur = conn.cursor()
            
            # Asset results table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS asset_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    asset_name TEXT NOT NULL,
                    run_id TEXT,
                    materialization_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    data TEXT,
                    status TEXT DEFAULT 'success',
                    error_message TEXT,
                    execution_time_ms INTEGER,
                    UNIQUE(asset_name, run_id)
                )
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
            
            conn.commit()
            logger.info(f"Database schema initialized at {self.db_path}")
    
    def test_connection(self) -> bool:
        """Test the database connection."""
        try:
            with self.get_connection() as conn:
                cur = conn.cursor()
                cur.execute("SELECT 1")
                return True
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            return False
    
    def execute(self, query: str, params: tuple = None) -> List[Dict[str, Any]]:
        """Execute a query and return results as list of dicts."""
        with self.get_connection() as conn:
            cur = conn.cursor()
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
    
    def execute_one(self, query: str, params: tuple = None) -> Optional[Dict[str, Any]]:
        """Execute a query and return a single result."""
        results = self.execute(query, params)
        return results[0] if results else None
    
    def insert(self, query: str, params: tuple = None) -> int:
        """Insert and return last row id."""
        with self.get_connection() as conn:
            cur = conn.cursor()
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
