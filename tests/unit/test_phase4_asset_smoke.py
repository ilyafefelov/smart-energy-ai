import importlib.util
import json
import sys
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _ensure_energy_ml_package() -> types.ModuleType:
    package = sys.modules.get("energy_ml")
    if package is None:
        package = types.ModuleType("energy_ml")
        package.__path__ = [str(ROOT / "energy_ml")]
        sys.modules["energy_ml"] = package
    return package


def _load_energy_ml_module(module_name: str, relative_path: str):
    _ensure_energy_ml_package()
    module_path = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


CONFIG_MODELS = _load_energy_ml_module("energy_ml.config_models", "energy_ml/config_models.py")
BatteryConfig = CONFIG_MODELS.BatteryConfig
GenerationConfig = CONFIG_MODELS.GenerationConfig
LoadProfileConfig = CONFIG_MODELS.LoadProfileConfig
UkraineTariffConfig = CONFIG_MODELS.UkraineTariffConfig
UserProfile = CONFIG_MODELS.UserProfile


def _dagster_stub() -> types.ModuleType:
    module = types.ModuleType("dagster")

    def asset(*args, **kwargs):
        if args and callable(args[0]) and len(args) == 1 and not kwargs:
            return args[0]

        def decorator(func):
            return func

        return decorator

    class AssetIn:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

    module.asset = asset
    module.AssetIn = AssetIn
    return module


def _load_asset_module(module_name: str, relative_path: str):
    _ensure_energy_ml_package()
    module_path = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    previous = sys.modules.get("dagster")
    sys.modules["dagster"] = _dagster_stub()
    try:
        spec.loader.exec_module(module)
    finally:
        if previous is None:
            sys.modules.pop("dagster", None)
        else:
            sys.modules["dagster"] = previous
    return module


def _make_user_profile(profile_type: str = "standard") -> UserProfile:
    if profile_type == "24_7":
        load_profile = LoadProfileConfig.create_24_7_profile(peak_load_kw=12.0)
    else:
        load_profile = LoadProfileConfig.create_standard_work_profile(peak_load_kw=12.0)

    return UserProfile(
        user_id="test-user",
        profile_name="Test Profile",
        battery=BatteryConfig(
            type="LFP",
            capacity_kwh=20.0,
            efficiency=0.94,
            max_charge_rate_kw=5.0,
            max_discharge_rate_kw=5.0,
        ),
        load_profile=load_profile,
        generation=GenerationConfig(solar_capacity_kw=5.0, wind_capacity_kw=0.0),
        tariff=UkraineTariffConfig(),
    )


def test_battery_degradation_asset_writes_expected_json(tmp_path, monkeypatch):
    module = _load_asset_module(
        "battery_models_asset_under_test",
        "energy_ml/assets/battery_models.py",
    )
    monkeypatch.setattr(module, "OUTPUT_DIR", tmp_path)

    result = module.battery_degradation_costs(_make_user_profile())

    output_file = tmp_path / "degradation_costs_LFP.json"
    assert output_file.exists()
    saved = json.loads(output_file.read_text(encoding="utf-8"))
    assert saved["battery_type"] == "LFP"
    assert saved["one_year"]["cycles"] == 365
    assert result["fifty_year"]["cycles"] == 365 * 50


def test_load_profile_asset_writes_sanitized_artifact_path(tmp_path, monkeypatch):
    module = _load_asset_module(
        "load_profiles_asset_under_test",
        "energy_ml/assets/load_profiles.py",
    )
    monkeypatch.chdir(tmp_path)

    result_path = Path(module.simulate_load_profile(_make_user_profile(profile_type="24_7")))

    assert result_path.exists()
    assert result_path.name == "load_profile_24_7.json"
    saved = json.loads(result_path.read_text(encoding="utf-8"))
    assert saved["metadata"]["profile_type"] == "24_7"
    assert saved["generation"]["annual_energy_kwh"] >= 0.0
    assert "self_consumption" in saved


def test_tariff_optimization_asset_uses_battery_efficiency_fallback(tmp_path, monkeypatch):
    module = _load_asset_module(
        "tariff_optimization_asset_under_test",
        "energy_ml/assets/tariff_optimization.py",
    )
    monkeypatch.setattr(module, "OUTPUT_DIR", tmp_path)

    result = module.tariff_optimization_analysis(_make_user_profile())

    output_file = tmp_path / "tariff_analysis_2026.json"
    assert output_file.exists()
    saved = json.loads(output_file.read_text(encoding="utf-8"))
    assert saved["annual_costs"]["total_cost_uah"] > 0
    assert saved["battery_optimization"]["savings_percent"] >= 0
    assert result["battery_optimization"]["battery_capacity_kwh"] == 20.0