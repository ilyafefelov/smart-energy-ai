import pytest

from src.data_pipeline.forecast_model_registry import (
    DEFAULT_FORECAST_MODEL_NAME,
    get_forecast_model_spec,
    list_forecast_model_specs,
)


def test_forecast_model_registry_exposes_random_forest_baseline() -> None:
    model_spec = get_forecast_model_spec()

    assert model_spec.model_name == DEFAULT_FORECAST_MODEL_NAME
    assert model_spec.model_family == "random_forest_regressor"
    assert model_spec.forecast_horizon_hours == 24
    assert model_spec.build_estimator().__class__.__name__ == "RandomForestRegressor"
    assert [spec.model_name for spec in list_forecast_model_specs()] == [
        DEFAULT_FORECAST_MODEL_NAME,
    ]


def test_forecast_model_registry_raises_clear_error_for_unknown_model() -> None:
    with pytest.raises(KeyError) as exc_info:
        get_forecast_model_spec("missing-model")

    assert "Available models" in str(exc_info.value)