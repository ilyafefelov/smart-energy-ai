"""Stable lineage helpers for forecast and optimization runtime contracts."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any, Mapping, Sequence


def _normalize_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, float):
        return round(value, 6)
    if isinstance(value, Mapping):
        return {str(key): _normalize_value(item) for key, item in sorted(value.items())}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_normalize_value(item) for item in value]
    return value


def _stable_digest(payload: Mapping[str, Any]) -> str:
    normalized = _normalize_value(payload)
    encoded = json.dumps(normalized, sort_keys=True, separators=(",", ":"))
    return hashlib.sha1(encoded.encode("utf-8")).hexdigest()


def _timestamp_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    text = str(value).strip()
    return text or None


def _coerce_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        numeric = float(value)
    except Exception:
        return None
    if numeric != numeric:
        return None
    return numeric


def _sorted_forecast_rows(forecast_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows = [dict(row) for row in forecast_rows]
    if not rows:
        return rows
    return sorted(rows, key=lambda row: _timestamp_text(row.get("forecast_timestamp")) or "")


def _resolve_sequence(rows: Sequence[Mapping[str, Any]], *candidate_keys: str) -> list[float | None]:
    values: list[float | None] = []
    for row in rows:
        numeric: float | None = None
        for key in candidate_keys:
            numeric = _optional_float(row.get(key))
            if numeric is not None:
                break
        values.append(numeric)
    return values


def build_forecast_lineage(
    forecast_rows: Sequence[Mapping[str, Any]],
    *,
    model_name: str | None = None,
    model_family: str | None = None,
    model_version: str | None = None,
    source_max_timestamp: Any = None,
    latency_ms: int | None = None,
    freshness_minutes: float | None = None,
) -> dict[str, Any]:
    """Build a deterministic forecast lineage contract from forecast output rows."""

    rows = _sorted_forecast_rows(forecast_rows)
    first_row = rows[0] if rows else {}
    last_row = rows[-1] if rows else {}

    resolved_model_name = str(
        model_name or first_row.get("model_name") or ""
    ).strip() or None
    resolved_model_family = str(
        model_family or first_row.get("model_family") or ""
    ).strip() or None
    resolved_model_version = str(
        model_version or first_row.get("forecast_model_version") or ""
    ).strip() or None
    if resolved_model_version is None and resolved_model_name is not None:
        resolved_model_version = f"registry:{resolved_model_name}"

    window_start_text = _timestamp_text(first_row.get("forecast_timestamp"))
    window_end_text = _timestamp_text(last_row.get("forecast_timestamp"))
    source_max_dt = _coerce_datetime(source_max_timestamp)
    window_start_dt = _coerce_datetime(first_row.get("forecast_timestamp"))

    resolved_freshness_minutes = freshness_minutes
    if resolved_freshness_minutes is None and source_max_dt is not None and window_start_dt is not None:
        resolved_freshness_minutes = round(
            (window_start_dt - source_max_dt).total_seconds() / 60.0,
            3,
        )

    digest_payload = {
        "model_name": resolved_model_name,
        "model_family": resolved_model_family,
        "model_version": resolved_model_version,
        "forecast_window_start_utc": window_start_text,
        "forecast_window_end_utc": window_end_text,
        "forecast_horizon_hours": int(first_row.get("forecast_horizon_hours") or len(rows)),
        "scenario_low_price_eur_mwh": _resolve_sequence(rows, "scenario_low_price_eur_mwh", "lower_bound_eur_mwh"),
        "scenario_base_price_eur_mwh": _resolve_sequence(rows, "scenario_base_price_eur_mwh", "predicted_price_eur_mwh"),
        "scenario_high_price_eur_mwh": _resolve_sequence(rows, "scenario_high_price_eur_mwh", "upper_bound_eur_mwh"),
    }
    forecast_run_id = f"forecast-{_stable_digest(digest_payload)[:16]}"

    resolved_latency_ms = int(latency_ms) if latency_ms is not None else first_row.get("forecast_latency_ms")
    if resolved_latency_ms is not None:
        resolved_latency_ms = int(resolved_latency_ms)

    return {
        "forecast_run_id": forecast_run_id,
        "forecast_model_name": resolved_model_name,
        "forecast_model_family": resolved_model_family,
        "forecast_model_version": resolved_model_version,
        "forecast_window_start_utc": window_start_text,
        "forecast_window_end_utc": window_end_text,
        "forecast_latency_ms": resolved_latency_ms,
        "forecast_freshness_minutes": resolved_freshness_minutes,
    }


def build_optimization_run_id(
    *,
    forecast_run_id: str | None,
    client_id: str,
    algorithm: str,
    horizon_mode: str,
    optimization_inputs: Mapping[str, Any],
    load_forecast: Sequence[float],
    solar_forecast: Sequence[float],
) -> str:
    """Build a deterministic optimization run identifier from the active inputs."""

    digest_payload = {
        "forecast_run_id": forecast_run_id,
        "client_id": client_id,
        "algorithm": algorithm,
        "forecast_horizon_mode": horizon_mode,
        "optimization_inputs": dict(optimization_inputs),
        "load_forecast": [round(float(value), 6) for value in load_forecast],
        "solar_forecast": [round(float(value), 6) for value in solar_forecast],
    }
    return f"optimization-{_stable_digest(digest_payload)[:16]}"


__all__ = [
    "build_forecast_lineage",
    "build_optimization_run_id",
]