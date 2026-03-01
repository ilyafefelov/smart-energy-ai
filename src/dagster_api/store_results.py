"""
Store Dagster asset results to SQLite after materialization.
"""

import os
import sys
import json
import time
import logging
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.dagster_api import get_asset_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def store_asset_outputs():
    """
    Parse the Dagster run output and store results in database.
    This reads from the temp storage and extracts data.
    """
    import glob
    
    service = get_asset_service()
    
    # Find latest temp storage
    temp_dirs = sorted(glob.glob(".tmp_dagster_home_*"), key=os.path.getmtime, reverse=True)
    
    if not temp_dirs:
        logger.warning("No temp storage found")
        return
    
    latest_dir = temp_dirs[0]
    storage_path = os.path.join(latest_dir, "storage")
    
    if not os.path.exists(storage_path):
        logger.warning(f"No storage found at {storage_path}")
        return
    
    # Find all asset outputs
    asset_files = [f for f in os.listdir(storage_path) if not f.startswith('.')]
    
    for asset_file in asset_files:
        asset_name = asset_file
        run_id = f"run_{int(time.time())}"
        
        # Read the output (it's pickled, so just note it exists)
        file_path = os.path.join(storage_path, asset_file)
        file_size = os.path.getsize(file_path)
        
        # Store metadata about the output
        result_data = {
            "storage_path": file_path,
            "file_size_bytes": file_size,
            "stored_at": datetime.now().isoformat()
        }
        
        service.store_asset_result(
            asset_name=asset_name,
            run_id=run_id,
            data=result_data,
            status="success",
            execution_time_ms=None
        )
        
        logger.info(f"Stored result for: {asset_name}")


if __name__ == "__main__":
    store_asset_outputs()
