#!/usr/bin/env python
"""
CLI for Dagster Asset API.

Usage:
    python -m src.dagster_api.cli list           # List all stored assets
    python -m src.dagster_api.cli summary         # Show asset summary
    python -m src.dagster_api.cli get <asset>    # Get latest result for asset
    python -m src.dagster_api.cli run <asset>    # Run asset via CLI and store result
    python -m src.dagster_api.cli run-all        # Run all assets and store results
"""

import sys
import json
from src.dagster_api.asset_service import get_asset_service


def list_assets():
    """List all stored assets."""
    service = get_asset_service()
    assets = service.list_assets()
    if not assets:
        print("No assets stored yet. Run 'python -m dagster asset materialize' first!")
    else:
        print("Stored assets:")
        for a in assets:
            print(f"  - {a}")


def show_summary():
    """Show asset summary."""
    service = get_asset_service()
    summary = service.get_asset_summary()
    if not summary:
        print("No data yet.")
        return
    
    print("Asset Summary:")
    print("=" * 60)
    for name, data in summary.items():
        print(f"\n📊 {name}")
        print(f"   Runs: {data['run_count']}")
        print(f"   Last run: {data['last_run']}")
        print(f"   Avg time: {data['avg_execution_time_ms']:.0f}ms" if data['avg_execution_time_ms'] else "   Avg time: N/A")
        print(f"   Status: {'✅ OK' if data['last_run'] == data['last_success'] else '⚠️ Issues'}")


def get_asset(name: str):
    """Get latest result for an asset."""
    service = get_asset_service()
    result = service.get_asset_result(name)
    if result:
        print(f"Asset: {result.asset_name}")
        print(f"Run ID: {result.run_id}")
        print(f"Time: {result.materialization_time}")
        print(f"Status: {result.status}")
        print(f"Execution time: {result.execution_time_ms}ms")
        print(f"\nData:")
        print(json.dumps(result.data, indent=2))
    else:
        print(f"No result found for: {name}")


def run_asset(name: str):
    """Trigger an asset materialization and store result."""
    import subprocess
    import time
    
    service = get_asset_service()
    start = time.time()
    
    # Run via dagster CLI
    result = subprocess.run(
        ["python", "-m", "dagster", "asset", "materialize", 
         "--select", name, "-m", "src.assets"],
        capture_output=True,
        text=True
    )
    
    execution_time_ms = int((time.time() - start) * 1000)
    run_id = f"run_{int(start)}"
    
    success = result.returncode == 0
    
    # Store result
    service.store_asset_result(
        asset_name=name,
        run_id=run_id,
        data={"output": result.stdout[-1000:] if result.stdout else ""},
        status="success" if success else "failed",
        error_message=result.stderr[-500:] if result.stderr else None,
        execution_time_ms=execution_time_ms
    )
    
    print(f"Status: {'✅ Success' if success else '❌ Failed'}")
    print(f"Execution time: {execution_time_ms}ms")


def run_all():
    """Run all assets and store results."""
    assets = [
        'market_data_asset',
        'weather_asset',
        'client_state_asset',
        'feature_matrix_asset',
        'price_forecast_asset',
        'optimization_schedule_asset',
        'optimization_schedule_milp_asset',
        'accuracy_benchmark_asset',
        'engine_benchmark_asset',
        'mlflow_tracking_asset'
    ]
    
    for asset in assets:
        print(f"\n{'='*40}")
        print(f"Running: {asset}")
        print('='*40)
        run_asset(asset)
        print()


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    
    cmd = sys.argv[1]
    
    if cmd == "list":
        list_assets()
    elif cmd == "summary":
        show_summary()
    elif cmd == "get":
        if len(sys.argv) < 3:
            print("Usage: get <asset_name>")
        else:
            get_asset(sys.argv[2])
    elif cmd == "run":
        if len(sys.argv) < 3:
            print("Usage: run <asset_name>")
        else:
            run_asset(sys.argv[2])
    elif cmd == "run-all":
        run_all()
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)


if __name__ == "__main__":
    main()
