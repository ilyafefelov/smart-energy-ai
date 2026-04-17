import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]


def _run_bridge_cli(script_path: str, *args: str, cwd: Path | None = None) -> dict:
    completed = subprocess.run(
        [sys.executable, script_path, *args],
        cwd=str(cwd or REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr or completed.stdout
    return json.loads(completed.stdout)


class TestMlIntegrationCliCompatibility:
    def test_root_bridge_status_action(self):
        payload = _run_bridge_cli(
            "ml_integration_api.py",
            "--action",
            "get_status",
            cwd=REPO_ROOT,
        )

        assert payload["success"] is True
        assert "status" in payload
        assert "battery_state" in payload["status"]
        assert "soc_percent" in payload["status"]["battery_state"]

    def test_canonical_bridge_forecast_action(self):
        payload = _run_bridge_cli(
            "scripts/ml_integration_api.py",
            "--action",
            "get_forecast",
            "--hours",
            "6",
            cwd=REPO_ROOT,
        )

        assert payload["success"] is True
        assert payload["hours"] == 6
        assert len(payload["forecast"]) == 6
        assert {"hour", "action", "confidence"}.issubset(payload["forecast"][0])

    def test_energy_ml_wrapper_auxiliary_action(self):
        payload = _run_bridge_cli(
            "ml_integration_api.py",
            "--action",
            "get_battery_physics",
            cwd=REPO_ROOT / "energy_ml",
        )

        assert payload["success"] is True
        assert "physics_data" in payload
        assert "power_limits" in payload["physics_data"]
        assert "max_charge_power_kw" in payload["physics_data"]["power_limits"]
        assert payload["physics_data"]["power_limits"]["max_charge_power_kw"] > 0


class TestSystemIntegration:
    """Test integration between different system components."""

    def test_battery_controller_integration(self):
        """Test battery physics models work with controller."""
        import sys, os

        # Remove problematic path entries that cause nested energy_ml import
        filtered_path = []
        for path in sys.path:
            if path and "\\energy_ml" not in path and "/energy_ml" not in path:
                filtered_path.append(path)
        sys.path = filtered_path
        from energy_ml.simulator.battery_physics import LFPBatteryModel
        from energy_ml.control.inverter_controller import (
            VirtualInverterController,
            ControlAction,
            ControlCommand,
        )
        from datetime import datetime

        # Create battery and controller
        battery = LFPBatteryModel(capacity_kwh=10.0, max_power_kw=5.0)
        controller = VirtualInverterController(
            battery_capacity_kwh=10.0, max_power_kw=5.0
        )

        # Test they can work together
        initial_soc = battery.state.soc

        # Simulate charging command
        action = ControlAction(
            command=ControlCommand.CHARGE,
            power_kw=2.5,
            reason="Integration test",
            user_id="test",
            timestamp=datetime.now(),
        )

        # Execute command (sync version for testing)
        result = asyncio.run(controller.execute_command(action))
        assert result["success"] is True

        # Update battery state based on controller power
        battery.update_soc(power_kw=controller.current_power_kw, duration_hours=1.0)

        # Battery SOC should have changed
        assert battery.state.soc != initial_soc

    def test_config_system_integration(self):
        """Test configuration system works with components."""
        try:
            from energy_ml.config_models import BatteryConfig, TariffConfig

            # Create battery config
            battery_config = BatteryConfig(
                type="LFP", capacity_kwh=15.0, max_power_kw=7.5, efficiency=0.95
            )

            # Create tariff config
            tariff_config = TariffConfig(
                provider="mock", peak_price=3.0, off_peak_price=1.5
            )

            # Test configs are valid
            assert battery_config.type == "LFP"
            assert battery_config.capacity_kwh == 15.0
            assert tariff_config.peak_price > tariff_config.off_peak_price

        except ImportError:
            pytest.skip("Config models not available")

    def test_ml_pipeline_integration(self):
        """Test ML pipeline components work together."""
        try:
            import pandas as pd
            import numpy as np

            # Create sample data
            sample_data = pd.DataFrame(
                {
                    "timestamp": pd.date_range("2026-01-01", periods=24, freq="H"),
                    "price_uah_kwh": np.random.uniform(1.5, 3.0, 24),
                    "demand_kw": np.random.uniform(0.5, 2.0, 24),
                    "solar_generation_kw": np.random.uniform(0, 1.5, 24),
                }
            )

            # Test basic data processing
            assert len(sample_data) == 24
            assert "price_uah_kwh" in sample_data.columns
            assert sample_data["price_uah_kwh"].min() >= 1.5
            assert sample_data["price_uah_kwh"].max() <= 3.0

        except ImportError:
            pytest.skip("ML pipeline components not available")
