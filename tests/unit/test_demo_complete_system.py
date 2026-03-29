import asyncio
import importlib.util
import sys
import types
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _load_demo_module():
    module_path = ROOT / "energy_ml/demo_complete_system.py"
    spec = importlib.util.spec_from_file_location("demo_complete_system_under_test", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None

    class ControlCommand(Enum):
        CHARGE = "charge"
        HOLD = "hold"
        DISCHARGE = "discharge"
        AUTO = "auto"

    class ControlMode(Enum):
        AUTO = "auto"

    @dataclass
    class ControlAction:
        command: ControlCommand
        power_kw: float
        reason: str
        user_id: str
        timestamp: datetime

    class VirtualInverterController:
        def __init__(self, battery_capacity_kwh, max_power_kw, initial_soc):
            self.battery_capacity_kwh = battery_capacity_kwh
            self.max_power_kw = max_power_kw
            self.current_soc = initial_soc
            self.command_history = []

        async def execute_command(self, action):
            self.command_history.append(
                {
                    "timestamp": action.timestamp.isoformat(),
                    "command": action.command.value,
                    "power_kw": action.power_kw,
                    "reason": action.reason,
                }
            )
            return {
                "new_soc": self.current_soc,
                "power_kw": action.power_kw,
                "estimated_completion": None,
            }

    controller_pkg = types.ModuleType("control")
    controller_mod = types.ModuleType("control.inverter_controller")
    controller_mod.VirtualInverterController = VirtualInverterController
    controller_mod.ControlCommand = ControlCommand
    controller_mod.ControlAction = ControlAction
    controller_mod.ControlMode = ControlMode
    controller_pkg.inverter_controller = controller_mod

    class _BatteryModel:
        def __init__(self):
            self.state = types.SimpleNamespace(soc=0.5, temperature_c=25.0)

        def calculate_degradation(self, power_kw, hours):
            return 0.0004

        def get_efficiency(self, power_kw, soc):
            return 0.94

        def get_max_power(self, soc, mode):
            return 5.0

    simulator_pkg = types.ModuleType("simulator")
    simulator_mod = types.ModuleType("simulator.battery_physics")
    simulator_mod.create_battery_model = lambda *args, **kwargs: _BatteryModel()
    simulator_mod.BATTERY_CONFIGS = {}
    simulator_mod.LFPBatteryModel = _BatteryModel
    simulator_mod.LeadAcidBatteryModel = _BatteryModel
    simulator_mod.VRFBBatteryModel = _BatteryModel
    simulator_pkg.battery_physics = simulator_mod

    class UserPreference(Enum):
        MAX_EARN = "max_earn"
        BALANCE = "balance"
        MAX_BATTERY_SAFE = "max_battery_safe"
        MAX_CHARGE = "max_charge"

    class UserPreferenceEngine:
        def __init__(self, model):
            self.model = model

        def get_preference_description(self, pref):
            return {
                "description": pref.value,
                "ideal_for": "tests",
                "weights": {
                    "profit_weight": 0.4,
                    "safety_weight": 0.4,
                    "efficiency_weight": 0.2,
                },
            }

        def optimize_schedule(self, preference, hours_ahead=6):
            return [
                {
                    "hour": hour,
                    "action": "hold",
                    "power_kw": 0.0,
                    "soc_after": 0.5,
                    "expected_profit": 0.0,
                }
                for hour in range(hours_ahead)
            ]

    class ScheduleOptimizer:
        def __init__(self, model):
            self.model = model

        def create_peak_shaving_schedule(self, peak_hours, shaving_power):
            return {"summary": {"total_profit_eur": 4.2, "total_energy_cycled_kwh": 6.0}}

        def create_backup_schedule(self, target_soc):
            return {"summary": {"final_soc_pct": target_soc * 100, "charge_hours": 2}}

    optimizer_pkg = types.ModuleType("optimizer")
    optimizer_mod = types.ModuleType("optimizer.multi_objective")
    optimizer_mod.UserPreferenceEngine = UserPreferenceEngine
    optimizer_mod.ScheduleOptimizer = ScheduleOptimizer
    optimizer_mod.UserPreference = UserPreference
    optimizer_pkg.multi_objective = optimizer_mod

    previous = {
        "control": sys.modules.get("control"),
        "control.inverter_controller": sys.modules.get("control.inverter_controller"),
        "simulator": sys.modules.get("simulator"),
        "simulator.battery_physics": sys.modules.get("simulator.battery_physics"),
        "optimizer": sys.modules.get("optimizer"),
        "optimizer.multi_objective": sys.modules.get("optimizer.multi_objective"),
    }
    sys.modules["control"] = controller_pkg
    sys.modules["control.inverter_controller"] = controller_mod
    sys.modules["simulator"] = simulator_pkg
    sys.modules["simulator.battery_physics"] = simulator_mod
    sys.modules["optimizer"] = optimizer_pkg
    sys.modules["optimizer.multi_objective"] = optimizer_mod
    try:
        spec.loader.exec_module(module)
    finally:
        for name, original in previous.items():
            if original is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original
    return module


DEMO = _load_demo_module()


def test_print_status_formats_nested_values(capsys):
    DEMO.print_status({"battery": {"soc": 75, "mode": "auto"}, "state": "ready"})

    captured = capsys.readouterr().out
    assert "battery:" in captured
    assert "  soc: 75" in captured
    assert "state: ready" in captured


def test_demo_integration_prints_pipeline_metadata(capsys):
    DEMO.demo_integration()

    captured = capsys.readouterr().out
    assert "ML PIPELINE INTEGRATION" in captured
    assert "commands_executed: 15" in captured
    assert "profit_today_eur: 12.45" in captured


def test_main_returns_zero_when_demo_steps_complete(monkeypatch, capsys):
    async def fake_demo_control_system():
        return object()

    monkeypatch.setattr(DEMO, "demo_control_system", fake_demo_control_system)
    monkeypatch.setattr(DEMO, "demo_physics_simulator", lambda: {"LFP": object()})
    monkeypatch.setattr(DEMO, "demo_user_preferences", lambda controller, models: None)
    monkeypatch.setattr(DEMO, "demo_custom_scenarios", lambda: None)
    monkeypatch.setattr(DEMO, "demo_integration", lambda: None)

    result = asyncio.run(DEMO.main())

    assert result == 0
    captured = capsys.readouterr().out
    assert "DEMONSTRATION COMPLETE" in captured