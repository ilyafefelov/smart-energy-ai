"""
Asset service - integrates Dagster with PostgreSQL for result storage.
"""

import os
import json
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any

from dagster import DagsterInstance

from .database import Database, get_database
from .models import AssetResult

logger = logging.getLogger(__name__)


class AssetService:
    """Service for managing Dagster asset results."""
    
    def __init__(self, database: Optional[Database] = None):
        self.db = database or get_database()
        
        # Use persistent DAGSTER_HOME
        dagster_home = os.path.abspath("data/dagster_home")
        os.environ["DAGSTER_HOME"] = dagster_home
        
        self.instance = DagsterInstance.get()
    
    def get_recent_runs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent materialization runs."""
        return self.db.execute("""
            SELECT asset_name, run_id, materialization_time, status, 
                   execution_time_ms, error_message
            FROM asset_results
            ORDER BY materialization_time DESC
            LIMIT %s
        """, (limit,))
    
    def get_asset_result(self, asset_name: str, limit: int = 1) -> Optional[AssetResult]:
        """Get the most recent result for an asset."""
        row = self.db.execute_one("""
            SELECT asset_name, run_id, materialization_time, data, 
                   status, error_message, execution_time_ms
            FROM asset_results
            WHERE asset_name = %s
            ORDER BY materialization_time DESC
            LIMIT 1
        """, (asset_name,))
        
        if row:
            return AssetResult(
                asset_name=row['asset_name'],
                run_id=row['run_id'],
                materialization_time=row['materialization_time'],
                data=row['data'] if isinstance(row['data'], dict) else json.loads(row['data']),
                status=row['status'],
                error_message=row['error_message'],
                execution_time_ms=row['execution_time_ms']
            )
        return None
    
    def get_all_asset_results(self, asset_name: str, limit: int = 10) -> List[AssetResult]:
        """Get all recent results for an asset."""
        rows = self.db.execute("""
            SELECT asset_name, run_id, materialization_time, data,
                   status, error_message, execution_time_ms
            FROM asset_results
            WHERE asset_name = %s
            ORDER BY materialization_time DESC
            LIMIT %s
        """, (asset_name, limit))
        
        return [
            AssetResult(
                asset_name=r['asset_name'],
                run_id=r['run_id'],
                materialization_time=r['materialization_time'],
                data=r['data'] if isinstance(r['data'], dict) else json.loads(r['data']),
                status=r['status'],
                error_message=r['error_message'],
                execution_time_ms=r['execution_time_ms']
            )
            for r in rows
        ]
    
    def store_asset_result(
        self,
        asset_name: str,
        run_id: str,
        data: Dict[str, Any],
        status: str = "success",
        error_message: Optional[str] = None,
        execution_time_ms: Optional[int] = None
    ) -> bool:
        """Store an asset result in the database."""
        try:
            self.db.execute("""
                INSERT INTO asset_results 
                (asset_name, run_id, materialization_time, data, status, error_message, execution_time_ms)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (asset_name, run_id) 
                DO UPDATE SET 
                    data = EXCLUDED.data,
                    status = EXCLUDED.status,
                    error_message = EXCLUDED.error_message,
                    execution_time_ms = EXCLUDED.execution_time_ms
            """, (
                asset_name,
                run_id,
                datetime.now(),
                json.dumps(data),
                status,
                error_message,
                execution_time_ms
            ))
            logger.info(f"Stored result for asset: {asset_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to store result: {e}")
            return False
    
    def list_assets(self) -> List[str]:
        """List all tracked assets."""
        rows = self.db.execute("""
            SELECT DISTINCT asset_name 
            FROM asset_results
            ORDER BY asset_name
        """)
        return [r['asset_name'] for r in rows]
    
    def get_asset_summary(self) -> Dict[str, Any]:
        """Get summary of all assets."""
        rows = self.db.execute("""
            SELECT 
                asset_name,
                COUNT(*) as run_count,
                MAX(materialization_time) as last_run,
                MIN(CASE WHEN status = 'success' THEN materialization_time END) as first_success,
                MAX(CASE WHEN status = 'success' THEN materialization_time END) as last_success,
                AVG(execution_time_ms) as avg_execution_time_ms
            FROM asset_results
            GROUP BY asset_name
            ORDER BY asset_name
        """)
        return {r['asset_name']: dict(r) for r in rows}


# Singleton instance
_service = None

def get_asset_service() -> AssetService:
    """Get the asset service singleton."""
    global _service
    if _service is None:
        _service = AssetService()
    return _service
