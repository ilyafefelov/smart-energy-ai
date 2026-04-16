"""Forecast model registry for DAM price forecast candidates."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping

from sklearn.ensemble import RandomForestRegressor


PRICE_FORECAST_MODEL_ENV = "SMART_ENERGY_PRICE_FORECAST_MODEL"
DEFAULT_FORECAST_MODEL_NAME = "random_forest_dam_24h"

ForecastEstimatorFactory = Callable[[], object]


@dataclass(frozen=True)
class ForecastModelSpec:
    model_name: str
    model_family: str
    forecast_horizon_hours: int
    build_estimator: ForecastEstimatorFactory


def _build_random_forest_regressor() -> RandomForestRegressor:
    return RandomForestRegressor(
        n_estimators=300,
        max_depth=14,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1,
    )


_FORECAST_MODEL_REGISTRY: Mapping[str, ForecastModelSpec] = {
    DEFAULT_FORECAST_MODEL_NAME: ForecastModelSpec(
        model_name=DEFAULT_FORECAST_MODEL_NAME,
        model_family="random_forest_regressor",
        forecast_horizon_hours=24,
        build_estimator=_build_random_forest_regressor,
    )
}


def get_forecast_model_spec(model_name: str | None = None) -> ForecastModelSpec:
    resolved_name = model_name or DEFAULT_FORECAST_MODEL_NAME
    model_spec = _FORECAST_MODEL_REGISTRY.get(resolved_name)
    if model_spec is None:
        available = ", ".join(sorted(_FORECAST_MODEL_REGISTRY))
        raise KeyError(
            f"Unknown forecast model '{resolved_name}'. Available models: {available}"
        )
    return model_spec


def list_forecast_model_specs() -> tuple[ForecastModelSpec, ...]:
    return tuple(
        _FORECAST_MODEL_REGISTRY[model_name]
        for model_name in sorted(_FORECAST_MODEL_REGISTRY)
    )


__all__ = [
    "DEFAULT_FORECAST_MODEL_NAME",
    "PRICE_FORECAST_MODEL_ENV",
    "ForecastModelSpec",
    "get_forecast_model_spec",
    "list_forecast_model_specs",
]