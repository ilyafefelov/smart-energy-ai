import importlib.util
import builtins
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import types


def load_script_module(module_name, relative_path, control_module=None, simulator_module=None):
    module_path = Path(__file__).resolve().parents[2] / relative_path

    if control_module is not None:
        control_package = types.ModuleType("control")
        control_package.__path__ = [str(module_path.parents[1] / "control")]
        sys.modules["control"] = control_package
        sys.modules["control.inverter_controller"] = control_module

    if simulator_module is not None:
        simulator_package = types.ModuleType("simulator")
        simulator_package.__path__ = [str(module_path.parents[1] / "simulator")]
        sys.modules["simulator"] = simulator_package
        sys.modules["simulator.battery_physics"] = simulator_module

    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def build_control_module(execute_result=None, execute_error=None, status_result=None, status_error=None):
    module = types.ModuleType("control.inverter_controller")

    class ControlCommand(str):
        def __new__(cls, value):
            return str.__new__(cls, value)

    class ControlAction:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    class Controller:
        def __init__(self):
            self.last_command_time = kwargs_last_command_time.get("value")

        async def execute_command(self, action):
            if execute_error is not None:
                raise execute_error
            return dict(execute_result or {"success": True, "accepted_power_kw": action.power_kw})

        def get_status(self):
            if status_error is not None:
                raise status_error
            return dict(status_result or {"soc": 61, "power_kw": 0.0, "mode": "automatic", "active_command": None})

    kwargs_last_command_time = {"value": None}

    def get_controller():
        return Controller()

    module.get_controller = get_controller
    module.ControlCommand = ControlCommand
    module.ControlAction = ControlAction
    module.VirtualInverterController = object
    module.set_last_command_time = lambda value: kwargs_last_command_time.__setitem__("value", value)
    return module


def build_simulator_module():
    module = types.ModuleType("simulator.battery_physics")

    class BatteryModel:
        def __init__(self, capacity_kwh, max_power_kw):
            self.capacity_kwh = capacity_kwh
            self.max_power_kw = max_power_kw
            self.state = SimpleNamespace(
                soc=0.62,
                soh=0.96,
                temperature_c=24.5,
                cycles_completed=123.0,
                voltage=52.4,
                internal_resistance=0.018,
            )

        def calculate_degradation(self, power_kw, duration_hours):
            return 0.001

        def get_efficiency(self, power_kw, soc):
            return 0.93

        def get_max_power(self, soc, direction):
            return 4.5 if direction == "charge" else 4.0

    module.LFPBatteryModel = BatteryModel
    module.LeadAcidBatteryModel = BatteryModel
    module.VRFBBatteryModel = BatteryModel
    return module


def test_execute_control_command_outputs_success_payload(monkeypatch, capsys):
    control_module = build_control_module(execute_result={"success": True, "status": "executed"})
    module = load_script_module(
        "energy_ml.scripts.execute_control_command_test_success",
        Path("energy_ml/scripts/execute_control_command.py"),
        control_module=control_module,
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "execute_control_command.py",
            "--command",
            "charge",
            "--power",
            "3.0",
            "--reason",
            "test run",
            "--user-id",
            "tester",
        ],
    )

    exit_code = module.main()
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["success"] is True
    assert payload["status"] == "executed"
    assert payload["command_details"]["command"] == "charge"
    assert payload["command_details"]["user_id"] == "tester"


def test_execute_control_command_outputs_error_payload(monkeypatch, capsys):
    control_module = build_control_module(execute_error=RuntimeError("controller offline"))
    module = load_script_module(
        "energy_ml.scripts.execute_control_command_test_error",
        Path("energy_ml/scripts/execute_control_command.py"),
        control_module=control_module,
    )
    monkeypatch.setattr(sys, "argv", ["execute_control_command.py", "--command", "hold"])

    exit_code = module.main()
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert payload["success"] is False
    assert payload["error"] == "controller offline"
    assert payload["command_details"]["command"] == "hold"


def test_get_control_status_outputs_connected_metadata(monkeypatch, capsys):
    control_module = build_control_module(status_result={"soc": 72, "power_kw": 1.5, "mode": "manual", "active_command": "charge"})
    control_module.set_last_command_time(__import__("datetime").datetime(2026, 3, 6, 12, 30, 0))
    module = load_script_module(
        "energy_ml.scripts.get_control_status_test_success",
        Path("energy_ml/scripts/get_control_status.py"),
        control_module=control_module,
    )

    exit_code = module.main()
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["soc"] == 72
    assert payload["connection_status"] == "connected"
    assert payload["physics_enabled"] is True
    assert payload["last_command_time"] == "2026-03-06T12:30:00"


def test_get_control_status_outputs_error_payload(monkeypatch, capsys):
    control_module = build_control_module(status_error=RuntimeError("status unavailable"))
    module = load_script_module(
        "energy_ml.scripts.get_control_status_test_error",
        Path("energy_ml/scripts/get_control_status.py"),
        control_module=control_module,
    )

    exit_code = module.main()
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert payload["connection_status"] == "error"
    assert payload["system_health"] == "error"
    assert payload["error"] == "status unavailable"


def test_get_battery_physics_uses_actual_models_when_available(monkeypatch):
    control_module = build_control_module()
    simulator_module = build_simulator_module()
    module = load_script_module(
        "energy_ml.scripts.get_battery_physics_test_actual",
        Path("energy_ml/scripts/get_battery_physics.py"),
        control_module=control_module,
        simulator_module=simulator_module,
    )
    monkeypatch.setattr(module.random, "choice", lambda items: "LFP")
    monkeypatch.setattr(module.random, "uniform", lambda low, high: 2.5)

    payload = module.get_battery_physics()

    assert payload["success"] is True
    assert payload["battery_type"] == "LFP"
    assert payload["current_efficiency"] == 0.93
    assert payload["max_charge_power"] == 4.5
    assert payload["source"] == "actual_physics_model"


def test_get_battery_physics_falls_back_to_realistic_mock_when_imports_are_missing(monkeypatch):
    sys.modules.pop("simulator", None)
    sys.modules.pop("simulator.battery_physics", None)
    sys.modules.pop("control", None)
    sys.modules.pop("control.inverter_controller", None)
    module = load_script_module(
        "energy_ml.scripts.get_battery_physics_test_fallback",
        Path("energy_ml/scripts/get_battery_physics.py"),
    )

    original_import = builtins.__import__

    def patched_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name in {"simulator.battery_physics", "control.inverter_controller"}:
            raise ImportError(f"mocked missing dependency: {name}")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", patched_import)
    monkeypatch.setattr(module.random, "choices", lambda items, weights: [items[0]])
    sequence = iter([0.5, 0.25, 0.4, 0.3])
    monkeypatch.setattr(module.random, "random", lambda: next(sequence))
    monkeypatch.setattr(module.random, "uniform", lambda low, high: 1.5)

    payload = module.get_battery_physics()

    assert payload["success"] is True
    assert payload["battery_type"] == "LFP"
    assert payload["source"] == "realistic_mock_simulation"
    assert payload["state"]["soc"] == 0.6
    assert payload["state"]["temperature_c"] == 21.0
    assert payload["degradation_model"]["nominal_cycles"] == 8000