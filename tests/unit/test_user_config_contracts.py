import importlib.util
from pathlib import Path

import pytest


MODULE_PATH = Path(__file__).resolve().parents[2] / "energy_ml" / "user_config.py"
SPEC = importlib.util.spec_from_file_location("user_config_under_test", MODULE_PATH)
USER_CONFIG_MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC is not None and SPEC.loader is not None
SPEC.loader.exec_module(USER_CONFIG_MODULE)

CONFIG_MODELS_PATH = Path(__file__).resolve().parents[2] / "energy_ml" / "config_models.py"
CONFIG_MODELS_SPEC = importlib.util.spec_from_file_location("config_models_under_test", CONFIG_MODELS_PATH)
CONFIG_MODELS_MODULE = importlib.util.module_from_spec(CONFIG_MODELS_SPEC)
assert CONFIG_MODELS_SPEC is not None and CONFIG_MODELS_SPEC.loader is not None
CONFIG_MODELS_SPEC.loader.exec_module(CONFIG_MODELS_MODULE)

ConfigurationManager = USER_CONFIG_MODULE.ConfigurationManager
ConfigurationManagerError = USER_CONFIG_MODULE.ConfigurationManagerError
UserConfigModel = USER_CONFIG_MODULE.UserConfigModel
LoadProfileConfig = CONFIG_MODELS_MODULE.LoadProfileConfig


def test_load_config_missing_file_returns_defaults_with_source(tmp_path: Path) -> None:
    manager = ConfigurationManager(config_dir=tmp_path)

    result = manager.load_config()

    assert result.success is True
    assert result.source == "defaults"
    assert result.config is not None
    assert result.config.battery_type == "LFP"
    assert result.warnings


def test_load_config_invalid_file_returns_failure_without_defaults(tmp_path: Path) -> None:
    manager = ConfigurationManager(config_dir=tmp_path)
    manager.config_file.write_text("{invalid json", encoding="utf-8")

    result = manager.load_config()

    assert result.success is False
    assert result.source == "invalid"
    assert result.config is None
    assert result.errors

    with pytest.raises(ConfigurationManagerError):
        manager.load_config_or_raise()


def test_validation_methods_share_common_result_contract(tmp_path: Path) -> None:
    manager = ConfigurationManager(config_dir=tmp_path)

    battery_result = manager.validate_battery_config("InvalidType", 0.0, 1.2)
    load_result = manager.validate_load_profile("invalid", 0.0)
    complete_result = manager.validate_complete_config(UserConfigModel())

    assert battery_result.success is False
    assert battery_result.valid is False
    assert isinstance(battery_result.errors, list)
    assert isinstance(battery_result.warnings, list)

    assert load_result.success is False
    assert load_result.valid is False
    assert isinstance(load_result.errors, list)
    assert isinstance(load_result.warnings, list)

    assert complete_result.success is True
    assert complete_result.valid is True
    assert complete_result.config is not None


def test_save_and_trigger_results_use_shared_envelope(tmp_path: Path) -> None:
    manager = ConfigurationManager(config_dir=tmp_path)
    config = UserConfigModel(battery_capacity_kwh=12.0)

    save_result = manager.save_config(config)
    trigger_result = manager.trigger_ml_recalculation(config)
    history_entry = (tmp_path / "config_history.jsonl").read_text(encoding="utf-8").strip().splitlines()[-1]
    trigger_payload = (tmp_path / "recalculation_trigger.json").read_text(encoding="utf-8")

    assert save_result.success is True
    assert save_result.data is not None
    assert save_result.config is not None
    assert save_result.errors == []

    assert trigger_result.success is True
    assert trigger_result.trigger_id
    assert trigger_result.trigger_state == "triggered"
    assert trigger_result.errors == []
    assert USER_CONFIG_MODULE.json.loads(history_entry)["timestamp"].endswith("+00:00")
    assert USER_CONFIG_MODULE.json.loads(trigger_payload)["timestamp"].endswith("+00:00")


def test_load_profile_uses_single_canonical_machine_token() -> None:
    user_config = UserConfigModel(load_profile_type="24/7")
    runtime_profile = LoadProfileConfig.create_24_7_profile(peak_load_kw=20.0)
    legacy_profile = LoadProfileConfig(
        profile_type="24/7",
        name="Legacy Continuous",
        description="Legacy token should normalize",
        hourly_coefficients={hour: 0.8 for hour in range(24)},
        peak_load_kw=20.0,
    )

    assert user_config.load_profile_type == "24_7"
    assert runtime_profile.profile_type == "24_7"
    assert legacy_profile.profile_type == "24_7"


def test_battery_specifications_return_serializable_cost_values(tmp_path: Path) -> None:
    manager = ConfigurationManager(config_dir=tmp_path)

    default_specs = manager.get_battery_specifications("LFP")
    sized_specs = manager.get_battery_specifications("LFP", capacity_kwh=12.0)

    assert callable(default_specs["degradation_cost_uah_per_cycle"]) is False
    assert callable(sized_specs["degradation_cost_uah_per_cycle"]) is False
    assert default_specs["degradation_cost_uah_per_cycle"] == pytest.approx(13000 / 8000)
    assert sized_specs["degradation_cost_uah_per_cycle"] == pytest.approx(12.0 * 13000 / 8000)
    assert sized_specs["degradation_cost_uah_per_cycle_per_kwh"] == pytest.approx(13000 / 8000)


def test_arbitrage_potential_uses_materialized_degradation_cost(tmp_path: Path) -> None:
    manager = ConfigurationManager(config_dir=tmp_path)
    config = UserConfigModel(
        battery_type="LFP",
        battery_capacity_kwh=10.0,
        battery_efficiency=0.95,
        tariff_peak_rate_uah_kwh=12.5,
        tariff_off_peak_rate_uah_kwh=8.0,
    )

    arbitrage = manager.calculate_arbitrage_potential(config)

    assert arbitrage["daily_degradation_cost"] == pytest.approx(round(10.0 * 13000 / 8000, 2))
    assert arbitrage["daily_profit_net"] < arbitrage["daily_arbitrage_gross"]


def test_resolve_config_supports_input_payload_and_validation_failures(tmp_path: Path) -> None:
    manager = ConfigurationManager(config_dir=tmp_path)

    resolved = manager.resolve_config({"battery_capacity_kwh": 15.0, "load_profile_type": "24/7"})
    invalid = manager.resolve_config({"battery_capacity_kwh": 0.0})

    assert resolved.success is True
    assert resolved.source == "input"
    assert resolved.config is not None
    assert resolved.config.battery_capacity_kwh == 15.0
    assert resolved.config.load_profile_type == "24_7"

    assert invalid.success is False
    assert invalid.source == "invalid"
    assert invalid.config is None
    assert invalid.errors


def test_validate_complete_config_collects_errors_and_operational_warnings(tmp_path: Path) -> None:
    manager = ConfigurationManager(config_dir=tmp_path)
    config = UserConfigModel(
        battery_type="LFP",
        battery_capacity_kwh=10.0,
        battery_c_rate_discharge=0.2,
        load_peak_kw=12.0,
        tariff_peak_hours_start=23,
        tariff_peak_hours_end=6,
        tariff_peak_rate_uah_kwh=7.0,
        tariff_off_peak_rate_uah_kwh=8.0,
        ml_lookback_hours=24,
        ml_forecast_horizon_hours=24,
    )

    object.__setattr__(config, "ml_lookback_hours", 12)

    result = manager.validate_complete_config(config)

    assert result.success is False
    assert "Peak hours start must be before peak hours end" in result.errors
    assert any("Peak rate should be higher" in warning for warning in result.warnings)
    assert any("Battery max discharge" in warning for warning in result.warnings)
    assert any("ML lookback hours should be much larger" in warning for warning in result.warnings)


def test_load_profile_templates_expose_full_day_coefficients() -> None:
    manager = ConfigurationManager()

    templates = manager.get_load_profile_templates()

    assert set(templates) == {"standard", "multi-shift", "24_7", "custom"}
    assert len(templates["24_7"]["hourly_coefficients"]) == 24
    assert len(templates["standard"]["hourly_coefficients"]) == 24


def test_deprecated_battery_templates_stay_aligned_with_canonical_specs(tmp_path: Path) -> None:
    manager = ConfigurationManager(config_dir=tmp_path)

    templates = manager.get_battery_templates()

    for battery_type, template in templates.items():
        specs = manager.get_battery_specifications(battery_type)

        assert template["name"] == specs["name"]
        assert template["efficiency"] == specs["efficiency"]
        assert template["description"] == specs["description"]


def test_deprecated_profile_templates_stay_aligned_with_canonical_profiles() -> None:
    manager = ConfigurationManager()

    templates = manager.get_profile_templates()
    canonical_templates = manager.get_load_profile_templates()

    for profile_type, template in templates.items():
        canonical = canonical_templates[profile_type]

        assert template["name"] == canonical["name"]
        assert template["peak_load_kw"] == canonical["peak_kw"]
        assert template["description"] == canonical["description"]