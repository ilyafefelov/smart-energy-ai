import json
from pathlib import Path

import pytest

from src.data_pipeline.forecast_model_registry import (
    DEFAULT_FORECAST_MODEL_NAME,
    GRADIENT_BOOSTING_FORECAST_MODEL_NAME,
    NBEATSX_FORECAST_MODEL_NAME,
    NBEATSxForecastAdapter,
    PRICE_FORECAST_MODEL_ENV,
    get_forecast_model_spec,
    get_forecast_promotion_metadata_path,
    load_promoted_forecast_metadata,
    list_forecast_model_specs,
    load_promoted_forecast_model_name,
    resolve_active_forecast_model_name,
    write_promoted_forecast_model_metadata,
)


def test_forecast_model_registry_exposes_random_forest_baseline() -> None:
    model_spec = get_forecast_model_spec()

    assert model_spec.model_name == DEFAULT_FORECAST_MODEL_NAME
    assert model_spec.model_family == "random_forest_regressor"
    assert model_spec.forecast_horizon_hours == 24
    assert model_spec.build_estimator().__class__.__name__ == "RandomForestRegressor"
    assert [spec.model_name for spec in list_forecast_model_specs()] == [
        GRADIENT_BOOSTING_FORECAST_MODEL_NAME,
        NBEATSX_FORECAST_MODEL_NAME,
        DEFAULT_FORECAST_MODEL_NAME,
    ]


def test_forecast_model_registry_exposes_gradient_boosting_candidate() -> None:
    model_spec = get_forecast_model_spec(GRADIENT_BOOSTING_FORECAST_MODEL_NAME)

    assert model_spec.model_name == GRADIENT_BOOSTING_FORECAST_MODEL_NAME
    assert model_spec.model_family == "gradient_boosting_regressor"
    assert model_spec.forecast_horizon_hours == 24
    assert model_spec.build_estimator().__class__.__name__ == "GradientBoostingRegressor"


def test_forecast_model_registry_exposes_nbeatsx_candidate() -> None:
    model_spec = get_forecast_model_spec(NBEATSX_FORECAST_MODEL_NAME)

    assert model_spec.model_name == NBEATSX_FORECAST_MODEL_NAME
    assert model_spec.model_family == "nbeatsx_neuralforecast"
    assert model_spec.forecast_horizon_hours == 24
    assert isinstance(model_spec.build_estimator(), NBEATSxForecastAdapter)


def test_nbeatsx_adapter_raises_clear_error_when_dependency_missing(monkeypatch) -> None:
    from src.data_pipeline import forecast_model_registry as registry

    adapter = registry.NBEATSxForecastAdapter()

    def _raise_missing_dependency():
        raise ModuleNotFoundError("missing neuralforecast")

    monkeypatch.setattr(registry, "_load_neuralforecast_components", _raise_missing_dependency)

    with pytest.raises(ModuleNotFoundError) as exc_info:
        adapter.fit_frame(None, [], "target_price_t_plus_24h")

    assert "neuralforecast" in str(exc_info.value)


def test_forecast_model_registry_raises_clear_error_for_unknown_model() -> None:
    with pytest.raises(KeyError) as exc_info:
        get_forecast_model_spec("missing-model")

    assert "Available models" in str(exc_info.value)


def test_forecast_model_registry_loads_promoted_model_name(tmp_path, monkeypatch) -> None:
    from src.data_pipeline import forecast_model_registry as registry

    monkeypatch.setattr(registry, "FORECAST_MODEL_OUTPUT_DIR", tmp_path)

    metadata_path = write_promoted_forecast_model_metadata(
        {
            "model_name": GRADIENT_BOOSTING_FORECAST_MODEL_NAME,
            "model_family": "gradient_boosting_regressor",
            "benchmark_value_capture_ratio": 0.81,
            "benchmark_uncertainty_source": "walk_forward_residual_std",
            "benchmark_avg_uncertainty_spread_eur_mwh": 9.0,
        }
    )

    assert metadata_path == tmp_path / registry.FORECAST_PROMOTION_METADATA_NAME
    assert load_promoted_forecast_metadata() == {
        "model_name": GRADIENT_BOOSTING_FORECAST_MODEL_NAME,
        "model_family": "gradient_boosting_regressor",
        "benchmark_value_capture_ratio": 0.81,
        "benchmark_uncertainty_source": "walk_forward_residual_std",
        "benchmark_avg_uncertainty_spread_eur_mwh": 9.0,
    }
    assert load_promoted_forecast_model_name() == GRADIENT_BOOSTING_FORECAST_MODEL_NAME


def test_forecast_model_registry_prefers_env_override_over_promoted_model(tmp_path, monkeypatch) -> None:
    from src.data_pipeline import forecast_model_registry as registry

    monkeypatch.setattr(registry, "FORECAST_MODEL_OUTPUT_DIR", tmp_path)
    write_promoted_forecast_model_metadata({"model_name": GRADIENT_BOOSTING_FORECAST_MODEL_NAME})
    monkeypatch.setenv(PRICE_FORECAST_MODEL_ENV, NBEATSX_FORECAST_MODEL_NAME)

    assert resolve_active_forecast_model_name() == NBEATSX_FORECAST_MODEL_NAME


def test_forecast_model_registry_ignores_unknown_promoted_model(tmp_path, monkeypatch) -> None:
    from src.data_pipeline import forecast_model_registry as registry

    monkeypatch.setattr(registry, "FORECAST_MODEL_OUTPUT_DIR", tmp_path)
    promotion_path = get_forecast_promotion_metadata_path()
    promotion_path.parent.mkdir(parents=True, exist_ok=True)
    promotion_path.write_text(json.dumps({"model_name": "missing-model"}), encoding="utf-8")

    assert load_promoted_forecast_metadata() is None
    assert load_promoted_forecast_model_name() is None
    assert resolve_active_forecast_model_name() == DEFAULT_FORECAST_MODEL_NAME