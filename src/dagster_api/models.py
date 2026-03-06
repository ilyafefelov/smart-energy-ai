"""
Data models for asset results.
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Optional, Dict, List
import json


@dataclass
class AssetResult:
    """Represents the result of a materialized asset."""
    asset_name: str
    run_id: str
    tenant_id: Optional[str]
    materialization_time: datetime
    data: Dict[str, Any]
    status: str = "success"
    error_message: Optional[str] = None
    execution_time_ms: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        d = asdict(self)
        d['materialization_time'] = self.materialization_time.isoformat()
        return d
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'AssetResult':
        """Create from dictionary."""
        if isinstance(d.get('materialization_time'), str):
            d['materialization_time'] = datetime.fromisoformat(d['materialization_time'])
        return cls(**d)


@dataclass
class AssetMetadata:
    """Metadata about an asset."""
    asset_name: str
    description: str
    created_at: datetime
    last_updated: datetime
    schema: Dict[str, Any]
