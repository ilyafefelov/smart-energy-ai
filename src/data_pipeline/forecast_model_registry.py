"""Forecast model registry for DAM price forecast candidates."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Callable, Mapping


PRICE_FORECAST_MODEL_ENV = "SMART_ENERGY_PRICE_FORECAST_MODEL"
DEFAULT_FORECAST_MODEL_NAME = "random_forest_dam_24h"
GRADIENT_BOOSTING_FORECAST_MODEL_NAME = "gradient_boosting_dam_24h"
NBEATSX_FORECAST_MODEL_NAME = "nbeatsx_dam_24h"
FORECAST_PROMOTION_METADATA_NAME = "forecast_model_promotion.json"
FORECAST_MODEL_OUTPUT_DIR = Path("projects") / "smart-energy-ai" / "models"
FORECAST_BENCHMARK_PROMOTION_SOURCE = "forecast_value_benchmark_asset"
FORECAST_PROMOTION_GATE_VERSION = "forecast_value_scorecard_v1"

ForecastEstimatorFactory = Callable[[], object]
ForecastReadinessCheck = Callable[[], object]


@dataclass(frozen=True)
class ForecastModelSpec:
    model_name: str
    model_family: str
    forecast_horizon_hours: int
    build_estimator: ForecastEstimatorFactory
    readiness_check: ForecastReadinessCheck | None = None


def _build_random_forest_regressor():
    from sklearn.ensemble import RandomForestRegressor

    return RandomForestRegressor(
        n_estimators=300,
        max_depth=14,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1,
    )


def _build_gradient_boosting_regressor():
    from sklearn.ensemble import GradientBoostingRegressor

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
        readiness_check=None,
    ),
    GRADIENT_BOOSTING_FORECAST_MODEL_NAME: ForecastModelSpec(
        model_name=GRADIENT_BOOSTING_FORECAST_MODEL_NAME,
        model_family="gradient_boosting_regressor",
        forecast_horizon_hours=24,
        build_estimator=_build_gradient_boosting_regressor,
        readiness_check=None,
    ),
    NBEATSX_FORECAST_MODEL_NAME: ForecastModelSpec(
        model_name=NBEATSX_FORECAST_MODEL_NAME,
        model_family="nbeatsx_neuralforecast",
        forecast_horizon_hours=24,
        build_estimator=_build_nbeatsx_adapter,
        readiness_check=_load_neuralforecast_components,
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


def get_forecast_model_readiness(model_name: str | None = None) -> dict[str, object]:
    model_spec = get_forecast_model_spec(model_name)
    readiness_reason = None
    ready = True

    if model_spec.readiness_check is not None:
        try:
            model_spec.readiness_check()
        except ModuleNotFoundError as exc:
            ready = False
            readiness_reason = str(exc)

    return {
        "model_name": model_spec.model_name,
        "model_family": model_spec.model_family,
        "forecast_horizon_hours": model_spec.forecast_horizon_hours,
        "ready": ready,
        "readiness_reason": readiness_reason,
    }


def build_promoted_forecast_model_metadata(
    benchmark_row: Mapping[str, object],
    *,
    promoted_at_utc: str,
) -> dict[str, object]:
    model_name = str(benchmark_row.get("model_name") or "").strip()
    if not model_name:
        raise ValueError("Promotion metadata requires a benchmark row with a model_name.")

    model_spec = get_forecast_model_spec(model_name)
    if benchmark_row.get("promotion_decision") != "promoted":
        raise ValueError(
            f"Forecast model '{model_name}' cannot be promoted without a promoted benchmark decision."
        )
    if benchmark_row.get("benchmark_candidate_status") != "validated":
        raise ValueError(
            f"Forecast model '{model_name}' cannot be promoted without a validated benchmark row."
        )
    if benchmark_row.get("promotion_eligible") is not True:
        raise ValueError(
            f"Forecast model '{model_name}' cannot be promoted without passing the promotion gate."
        )

    readiness = get_forecast_model_readiness(model_name)
    if readiness["ready"] is not True:
        raise ValueError(
            f"Forecast model '{model_name}' is not runtime-ready: {readiness['readiness_reason']}"
        )

    return {
        "model_name": model_spec.model_name,
        "model_family": str(benchmark_row.get("model_family") or model_spec.model_family),
        "forecast_horizon_hours": int(
            benchmark_row.get("forecast_horizon_hours") or model_spec.forecast_horizon_hours
        ),
        "benchmark_value_capture_ratio": benchmark_row.get("benchmark_value_capture_ratio"),
        "benchmark_rmse": benchmark_row.get("benchmark_rmse"),
        "benchmark_mae": benchmark_row.get("benchmark_mae"),
        "benchmark_dispatch_comparison_mode": benchmark_row.get(
            "benchmark_dispatch_comparison_mode"
        ),
        "benchmark_conservative_dispatch_source": benchmark_row.get(
            "benchmark_conservative_dispatch_source"
        ),
        "benchmark_conservative_value_capture_ratio": benchmark_row.get(
            "benchmark_conservative_value_capture_ratio"
        ),
        "benchmark_point_vs_conservative_value_capture_delta": benchmark_row.get(
            "benchmark_point_vs_conservative_value_capture_delta"
        ),
        "benchmark_uncertainty_source": benchmark_row.get("benchmark_uncertainty_source"),
        "benchmark_avg_uncertainty_spread_eur_mwh": benchmark_row.get(
            "benchmark_avg_uncertainty_spread_eur_mwh"
        ),
        "benchmark_max_uncertainty_spread_eur_mwh": benchmark_row.get(
            "benchmark_max_uncertainty_spread_eur_mwh"
        ),
        "benchmark_candidate_status": "validated",
        "benchmark_candidate_ready": True,
        "benchmark_candidate_skip_reason": None,
        "benchmark_candidate_rank": benchmark_row.get("benchmark_candidate_rank"),
        "benchmark_incumbent_baseline": benchmark_row.get("benchmark_incumbent_baseline"),
        "promotion_eligible": True,
        "promotion_decision": "promoted",
        "promotion_decision_reason": benchmark_row.get("promotion_decision_reason"),
        "promotion_gate_version": FORECAST_PROMOTION_GATE_VERSION,
        "promotion_source": FORECAST_BENCHMARK_PROMOTION_SOURCE,
        "promoted_at_utc": promoted_at_utc,
        "model_ready": True,
        "model_readiness_reason": readiness["readiness_reason"],
    }


def get_forecast_promotion_metadata_path() -> Path:
    return FORECAST_MODEL_OUTPUT_DIR / FORECAST_PROMOTION_METADATA_NAME


def _is_valid_promoted_forecast_metadata(metadata: Mapping[str, object]) -> bool:
    promoted_model_name = metadata.get("model_name")
    if not isinstance(promoted_model_name, str):
        return False
    if promoted_model_name not in _FORECAST_MODEL_REGISTRY:
        return False
    if metadata.get("promotion_source") != FORECAST_BENCHMARK_PROMOTION_SOURCE:
        return False
    if metadata.get("promotion_gate_version") != FORECAST_PROMOTION_GATE_VERSION:
        return False
    if metadata.get("benchmark_candidate_status") != "validated":
        return False
    if metadata.get("benchmark_candidate_ready") is not True:
        return False
    if metadata.get("promotion_eligible") is not True:
        return False
    if metadata.get("promotion_decision") != "promoted":
        return False
    if metadata.get("model_ready") is not True:
        return False

    readiness = get_forecast_model_readiness(promoted_model_name)
    if readiness["ready"] is not True:
        return False

    return True


def load_promoted_forecast_metadata() -> dict[str, object] | None:
    metadata_path = get_forecast_promotion_metadata_path()
    if not metadata_path.exists():
        return None

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if not isinstance(metadata, dict):
        return None

    if not _is_valid_promoted_forecast_metadata(metadata):
        return None

    return dict(metadata)


def load_promoted_forecast_model_name() -> str | None:
    metadata = load_promoted_forecast_metadata()
    if metadata is None:
        return None
    return str(metadata["model_name"])


def resolve_forecast_model_version(
    model_name: str,
    promoted_metadata: Mapping[str, object] | None = None,
) -> str:
    if promoted_metadata and promoted_metadata.get("model_name") == model_name:
        explicit_version = str(promoted_metadata.get("model_version") or "").strip()
        if explicit_version:
            return explicit_version

        promoted_at = str(promoted_metadata.get("promoted_at_utc") or "").strip()
        if promoted_at:
            return f"promotion:{promoted_at}"

        promotion_source = str(promoted_metadata.get("promotion_source") or "").strip()
        if promotion_source:
            return f"promotion:{promotion_source}:{model_name}"

    return f"registry:{model_name}"


def resolve_active_forecast_model_name() -> str:
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
    "FORECAST_BENCHMARK_PROMOTION_SOURCE",
    "DEFAULT_FORECAST_MODEL_NAME",
    "FORECAST_MODEL_OUTPUT_DIR",
    "FORECAST_PROMOTION_GATE_VERSION",
    "FORECAST_PROMOTION_METADATA_NAME",
    "GRADIENT_BOOSTING_FORECAST_MODEL_NAME",
    "NBEATSX_FORECAST_MODEL_NAME",
    "NBEATSxForecastAdapter",
    "PRICE_FORECAST_MODEL_ENV",
    "ForecastModelSpec",
    "build_promoted_forecast_model_metadata",
    "get_forecast_promotion_metadata_path",
    "get_forecast_model_spec",
    "get_forecast_model_readiness",
    "load_promoted_forecast_metadata",
    "list_forecast_model_specs",
    "load_promoted_forecast_model_name",
    "resolve_forecast_model_version",
    "resolve_active_forecast_model_name",
    "write_promoted_forecast_model_metadata",
]