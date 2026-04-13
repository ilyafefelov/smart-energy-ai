import sys
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from energy_ml.mlops.battery_physics import BatteryPhysicsEngine


def test_unknown_chemistry_falls_back_to_lfp():
    engine = BatteryPhysicsEngine()
    config = SimpleNamespace(battery_type="Unknown-Chemistry", battery_capacity_kwh=12.0)

    result = engine.simulate_battery_behavior(config)

    assert result["chemistry"] == "LFP"
    assert result["capacity_kwh"] == 12.0
    assert result["current_state"]["voltage"] == BatteryPhysicsEngine.CHEMISTRY_PARAMS["LFP"]["nominal_voltage"]
    assert "timestamp" in result


def test_simulation_failure_returns_timestamped_error_payload(monkeypatch):
    engine = BatteryPhysicsEngine()
    config = SimpleNamespace(battery_type="Lead-Acid", battery_capacity_kwh=8.0)

    def raise_runtime_error(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(engine, "_generate_charging_curves", raise_runtime_error)

    result = engine.simulate_battery_behavior(config)

    assert result["chemistry"] == "Lead-Acid"
    assert result["error"] == "boom"
    assert "timestamp" in result