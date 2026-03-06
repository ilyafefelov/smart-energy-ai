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


def _normalize_tenant_id(value: Optional[str]) -> Optional[str]:
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower()
    return normalized or None


def _resolve_required_tenant_id(value: Optional[str]) -> Optional[str]:
    tenant_id = _normalize_tenant_id(value) or _normalize_tenant_id(os.getenv("ENERGY_ML_TENANT_ID"))
    if tenant_id:
        return tenant_id

    logger.warning("Tenant-scoped Dagster reads require tenant_id; returning no rows")
    return None


class AssetService:
    """Service for managing Dagster asset results."""
    
    def __init__(self, database: Optional[Database] = None):
        self.db = database or get_database()
        
        # Use persistent DAGSTER_HOME
        dagster_home = os.path.abspath("data/dagster_home")
        os.environ["DAGSTER_HOME"] = dagster_home
        
        self.instance = DagsterInstance.get()
    
    def get_recent_runs(self, limit: int = 10, tenant_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get recent materialization runs."""
        normalized_tenant_id = _resolve_required_tenant_id(tenant_id)
        if not normalized_tenant_id:
            return []

        return self.db.execute("""
            SELECT asset_name, run_id, tenant_id, materialization_time, status,
                   execution_time_ms, error_message
            FROM asset_results
            WHERE tenant_id = %s
            ORDER BY materialization_time DESC
            LIMIT %s
        """, (normalized_tenant_id, limit))
    
    def get_asset_result(self, asset_name: str, tenant_id: Optional[str] = None, limit: int = 1) -> Optional[AssetResult]:
        """Get the most recent result for an asset."""
        normalized_tenant_id = _resolve_required_tenant_id(tenant_id)
        if not normalized_tenant_id:
            return None

        row = self.db.execute_one("""
            SELECT asset_name, run_id, tenant_id, materialization_time, data,
                   status, error_message, execution_time_ms
            FROM asset_results
            WHERE asset_name = %s
              AND tenant_id = %s
            ORDER BY materialization_time DESC
            LIMIT %s
        """, (asset_name, normalized_tenant_id, limit))
        
        if row:
            return AssetResult(
                asset_name=row['asset_name'],
                run_id=row['run_id'],
                tenant_id=row.get('tenant_id'),
                materialization_time=row['materialization_time'],
                data=row['data'] if isinstance(row['data'], dict) else json.loads(row['data']),
                status=row['status'],
                error_message=row['error_message'],
                execution_time_ms=row['execution_time_ms']
            )
        return None
    
    def get_all_asset_results(self, asset_name: str, limit: int = 10, tenant_id: Optional[str] = None) -> List[AssetResult]:
        """Get all recent results for an asset."""
        normalized_tenant_id = _resolve_required_tenant_id(tenant_id)
        if not normalized_tenant_id:
            return []

        rows = self.db.execute("""
            SELECT asset_name, run_id, tenant_id, materialization_time, data,
                   status, error_message, execution_time_ms
            FROM asset_results
            WHERE asset_name = %s
              AND tenant_id = %s
            ORDER BY materialization_time DESC
            LIMIT %s
        """, (asset_name, normalized_tenant_id, limit))
        
        return [
            AssetResult(
                asset_name=r['asset_name'],
                run_id=r['run_id'],
                tenant_id=r.get('tenant_id'),
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
        tenant_id: Optional[str] = None,
        status: str = "success",
        error_message: Optional[str] = None,
        execution_time_ms: Optional[int] = None
    ) -> bool:
        """Store an asset result in the database."""
        try:
            normalized_tenant_id = _normalize_tenant_id(
                tenant_id or data.get("tenant_id") or os.getenv("ENERGY_ML_TENANT_ID")
            )
            if not normalized_tenant_id:
                logger.error(
                    "Refusing to store unscoped asset result for %s; tenant_id is required",
                    asset_name,
                )
                return False
            self.db.execute("""
                INSERT INTO asset_results 
                (asset_name, run_id, tenant_id, materialization_time, data, status, error_message, execution_time_ms)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (asset_name, run_id) 
                DO UPDATE SET 
                    tenant_id = EXCLUDED.tenant_id,
                    data = EXCLUDED.data,
                    status = EXCLUDED.status,
                    error_message = EXCLUDED.error_message,
                    execution_time_ms = EXCLUDED.execution_time_ms
            """, (
                asset_name,
                run_id,
                normalized_tenant_id,
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
    
    def list_assets(self, tenant_id: Optional[str] = None) -> List[str]:
        """List all tracked assets."""
        normalized_tenant_id = _resolve_required_tenant_id(tenant_id)
        if not normalized_tenant_id:
            return []

        rows = self.db.execute("""
            SELECT DISTINCT asset_name 
            FROM asset_results
            WHERE tenant_id = %s
            ORDER BY asset_name
        """, (normalized_tenant_id,))
        return [r['asset_name'] for r in rows]
    
    def get_asset_summary(self, tenant_id: Optional[str] = None) -> Dict[str, Any]:
        """Get summary of all assets."""
        normalized_tenant_id = _resolve_required_tenant_id(tenant_id)
        if not normalized_tenant_id:
            return {}

        rows = self.db.execute("""
            SELECT 
                asset_name,
                COUNT(*) as run_count,
                MAX(materialization_time) as last_run,
                MIN(CASE WHEN status = 'success' THEN materialization_time END) as first_success,
                MAX(CASE WHEN status = 'success' THEN materialization_time END) as last_success,
                AVG(execution_time_ms) as avg_execution_time_ms
            FROM asset_results
            WHERE tenant_id = %s
            GROUP BY asset_name
            ORDER BY asset_name
        """, (normalized_tenant_id,))
        return {r['asset_name']: dict(r) for r in rows}


# Singleton instance
_service = None

def get_asset_service() -> AssetService:
    """Get the asset service singleton."""
    global _service
    if _service is None:
        _service = AssetService()
    return _service
