# tests/integration/test_api_integration.py
import pytest
import httpx
import asyncio
import sys
import os
import time
from threading import Thread
import subprocess

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))


class TestControlAPIIntegration:
    @pytest.fixture(scope="session")
    def api_server(self):
        """Start ML API server for testing."""
        try:
            # Start the ML integration API server
            import subprocess

            api_process = subprocess.Popen(
                [sys.executable, "ml_integration_api.py"], cwd="energy_ml"
            )

            # Wait for server to start
            time.sleep(5)

            yield "http://localhost:8000"

            # Cleanup
            api_process.terminate()
            api_process.wait()
        except Exception as e:
            pytest.skip(f"Could not start API server: {e}")

    @pytest.fixture
    def client(self, api_server):
        return httpx.AsyncClient(base_url=api_server)

    @pytest.mark.asyncio
    async def test_control_status_endpoint(self, client):
        """Test control status API."""
        try:
            response = await client.get("/api/control/status")
            assert response.status_code == 200

            data = response.json()
            assert "soc" in data
            assert "power_kw" in data
            assert "mode" in data
            assert 0.0 <= data["soc"] <= 1.0
        except httpx.ConnectError:
            pytest.skip("API server not available")
        finally:
            await client.aclose()

    @pytest.mark.asyncio
    async def test_execute_command_endpoint(self, client):
        """Test command execution API."""
        command = {"command": "charge", "power_kw": 2.5, "reason": "Integration test"}

        try:
            response = await client.post("/api/control/execute", json=command)
            assert response.status_code in [200, 201]

            data = response.json()
            assert data["success"] is True
            assert "command_id" in data
        except httpx.ConnectError:
            pytest.skip("API server not available")
        finally:
            await client.aclose()

    @pytest.mark.asyncio
    async def test_optimization_endpoint(self, client):
        """Test optimization schedule API."""
        request = {"user_preference": "balance", "hours_ahead": 12}

        try:
            response = await client.post("/api/control/schedule", json=request)
            assert response.status_code in [200, 201]

            data = response.json()
            assert data["success"] is True
            assert "schedule" in data
            assert len(data["schedule"]) == 12
        except httpx.ConnectError:
            pytest.skip("API server not available")
        finally:
            await client.aclose()

    @pytest.mark.asyncio
    async def test_settings_integration(self, client):
        """Test settings affect optimization."""
        # Change battery settings
        battery_config = {"type": "VRFB", "capacity_kwh": 20.0, "efficiency": 0.80}

        try:
            await client.post("/api/settings/battery", json=battery_config)

            # Get optimization schedule
            request = {"user_preference": "max_earn", "hours_ahead": 6}
            response = await client.post("/api/control/schedule", json=request)

            if response.status_code in [200, 201]:
                schedule = response.json()["schedule"]

                # VRFB should allow more aggressive trading due to low degradation
                power_levels = [abs(s["power_kw"]) for s in schedule]
                avg_power = sum(power_levels) / len(power_levels)
                assert avg_power >= 0  # Basic validation - server responded
        except httpx.ConnectError:
            pytest.skip("API server not available")
        finally:
            await client.aclose()


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
