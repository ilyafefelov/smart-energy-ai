"""Forecast model registry for DAM price forecast candidates."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
from typing import Callable, Mapping

from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor


PRICE_FORECAST_MODEL_ENV = "SMART_ENERGY_PRICE_FORECAST_MODEL"
DEFAULT_FORECAST_MODEL_NAME = "random_forest_dam_24h"
GRADIENT_BOOSTING_FORECAST_MODEL_NAME = "gradient_boosting_dam_24h"
NBEATSX_FORECAST_MODEL_NAME = "nbeatsx_dam_24h"
FORECAST_PROMOTION_METADATA_NAME = "forecast_model_promotion.json"
FORECAST_MODEL_OUTPUT_DIR = Path("projects") / "smart-energy-ai" / "models"

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


def _build_gradient_boosting_regressor() -> GradientBoostingRegressor:
    return GradientBoostingRegressor(
        n_estimators=250,
        learning_rate=0.05,
        max_depth=3,
        min_samples_leaf=2,
        subsample=0.9,
        random_state=42,
        loss="squared_error",
    )


def _load_neuralforecast_components():
    try:
        from neuralforecast import NeuralForecast
        from neuralforecast.models import NBEATSx
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "The 'nbeatsx_dam_24h' forecast candidate requires the optional 'neuralforecast' "
            "dependency. Install it before selecting this model."
        ) from exc

    return NeuralForecast, NBEATSx


class NBEATSxForecastAdapter:
    def __init__(self, *, forecast_horizon_hours: int = 24, input_size: int = 48) -> None:
        self._forecast_horizon_hours = forecast_horizon_hours
        self._input_size = input_size
        self._feature_cols: list[str] = []
        self._forecaster = None

    def fit_frame(self, train_df, feature_cols, target_col) -> None:
        NeuralForecast, NBEATSx = _load_neuralforecast_components()

        self._feature_cols = list(feature_cols)
        train_pd = (
            train_df.select(["timestamp", target_col, *self._feature_cols])
            .rename({"timestamp": "ds", target_col: "y"})
            .to_pandas()
        )
        train_pd["unique_id"] = "dam_ukraine"

        model = NBEATSx(
            h=self._forecast_horizon_hours,
            input_size=self._input_size,
            futr_exog_list=self._feature_cols,
            exclude_insample_y=False,
            scaler_type="robust",
            max_steps=100,
            val_check_steps=25,
            early_stop_patience_steps=5,
            random_seed=42,
            alias=NBEATSX_FORECAST_MODEL_NAME,
        )
        self._forecaster = NeuralForecast(models=[model], freq="h")

        val_size = self._forecast_horizon_hours if len(train_pd) > self._forecast_horizon_hours * 2 else 0
        self._forecaster.fit(df=train_pd, val_size=val_size)

    def predict_frame(self, df, feature_cols):
        if self._forecaster is None:
            raise RuntimeError("NBEATSxForecastAdapter must be fit before predict_frame().")

        prediction_cols = self._feature_cols or list(feature_cols)
        future_pd = df.select(["timestamp", *prediction_cols]).rename({"timestamp": "ds"}).to_pandas()
        future_pd["unique_id"] = "dam_ukraine"

        prediction_df = self._forecaster.predict(futr_df=future_pd)
        value_columns = [
            column for column in prediction_df.columns if column not in {"unique_id", "ds"}
        ]
        return prediction_df[value_columns[0]].to_numpy(dtype=float)


def _build_nbeatsx_adapter() -> NBEATSxForecastAdapter:
    return NBEATSxForecastAdapter()


_FORECAST_MODEL_REGISTRY: Mapping[str, ForecastModelSpec] = {
    DEFAULT_FORECAST_MODEL_NAME: ForecastModelSpec(
        model_name=DEFAULT_FORECAST_MODEL_NAME,
        model_family="random_forest_regressor",
        forecast_horizon_hours=24,
        build_estimator=_build_random_forest_regressor,
    ),
    GRADIENT_BOOSTING_FORECAST_MODEL_NAME: ForecastModelSpec(
        model_name=GRADIENT_BOOSTING_FORECAST_MODEL_NAME,
        model_family="gradient_boosting_regressor",
        forecast_horizon_hours=24,
        build_estimator=_build_gradient_boosting_regressor,
    ),
    NBEATSX_FORECAST_MODEL_NAME: ForecastModelSpec(
        model_name=NBEATSX_FORECAST_MODEL_NAME,
        model_family="nbeatsx_neuralforecast",
        forecast_horizon_hours=24,
        build_estimator=_build_nbeatsx_adapter,
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


def get_forecast_promotion_metadata_path() -> Path:
    return FORECAST_MODEL_OUTPUT_DIR / FORECAST_PROMOTION_METADATA_NAME


def load_promoted_forecast_model_name() -> str | None:
    metadata_path = get_forecast_promotion_metadata_path()
    if not metadata_path.exists():
        return None

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    promoted_model_name = metadata.get("model_name")
    if not isinstance(promoted_model_name, str):
        return None
    if promoted_model_name not in _FORECAST_MODEL_REGISTRY:
        return None
    return promoted_model_name


def resolve_active_forecast_model_name() -> str:
    env_override = os.getenv(PRICE_FORECAST_MODEL_ENV)
    if env_override:
        return env_override

    promoted_model_name = load_promoted_forecast_model_name()
    if promoted_model_name:
        return promoted_model_name

    return DEFAULT_FORECAST_MODEL_NAME


def write_promoted_forecast_model_metadata(metadata: Mapping[str, object]) -> Path:
    metadata_path = get_forecast_promotion_metadata_path()
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(json.dumps(dict(metadata), indent=2), encoding="utf-8")
    return metadata_path


__all__ = [
    "DEFAULT_FORECAST_MODEL_NAME",
    "FORECAST_MODEL_OUTPUT_DIR",
    "FORECAST_PROMOTION_METADATA_NAME",
    "GRADIENT_BOOSTING_FORECAST_MODEL_NAME",
    "NBEATSX_FORECAST_MODEL_NAME",
    "NBEATSxForecastAdapter",
    "PRICE_FORECAST_MODEL_ENV",
    "ForecastModelSpec",
    "get_forecast_promotion_metadata_path",
    "get_forecast_model_spec",
    "list_forecast_model_specs",
    "load_promoted_forecast_model_name",
    "resolve_active_forecast_model_name",
    "write_promoted_forecast_model_metadata",
]