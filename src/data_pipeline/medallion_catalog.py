"""Helpers for rendering supervisor-facing medallion catalog artifacts."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

import yaml

from src.data_pipeline.dagster_schedule_loader import (
    _find_latest_asset_file,
    _load_pickled_asset,
    _to_rows,
)


TIMESTAMP_CANDIDATES = (
    "timestamp",
    "forecast_timestamp",
    "analysis_timestamp",
    "fetched_at",
    "logged_at",
    "benchmark_timestamp",
    "battery_state_updated_at",
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _file_modified_iso(path: Path) -> str:
    try:
        modified_at = path.stat().st_mtime
    except OSError:
        return _utc_now_iso()
    return datetime.fromtimestamp(modified_at, tz=timezone.utc).replace(microsecond=0).isoformat()


def _safe_float(value: Any) -> float | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if numeric != numeric:
        return None
    return numeric


def _safe_int(value: Any) -> int | None:
    numeric = _safe_float(value)
    if numeric is None:
        return None
    if not float(numeric).is_integer():
        return None
    return int(numeric)


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _first_present(mapping: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        value = mapping.get(key)
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return value
    return None


def _materialization_status(snapshot: Mapping[str, Any]) -> str:
    status = _optional_text(snapshot.get("status")) or "unknown"
    rows = snapshot.get("rows")
    if status == "materialized" and isinstance(rows, list) and not rows:
        return "materialized_empty"
    return status


def _normalize_name(value: str) -> str:
    return " ".join(part.capitalize() for part in value.replace("_", " ").split())


def _format_number(value: float | int | None, digits: int = 2) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, int):
        return str(value)
    return f"{value:.{digits}f}"


def _format_bytes(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024.0:.1f} KB"
    if size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024.0 * 1024.0):.1f} MB"
    return f"{size_bytes / (1024.0 * 1024.0 * 1024.0):.1f} GB"


def _parse_timestamp(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    text = str(value).strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _format_timestamp(value: Any) -> str | None:
    parsed = _parse_timestamp(value)
    if parsed is None:
        return None
    return parsed.replace(microsecond=0).isoformat()


def _max_timestamp(values: Iterable[Any]) -> str | None:
    timestamps = [parsed for parsed in (_parse_timestamp(value) for value in values) if parsed is not None]
    if not timestamps:
        return None
    return max(timestamps).replace(microsecond=0).isoformat()


def _list_files(path: Path) -> list[Path]:
    if not path.exists():
        return []
    if path.is_file():
        return [path]
    return [candidate for candidate in path.rglob("*") if candidate.is_file() and candidate.name != ".gitkeep"]


def _storage_stats(project_root: Path, storage_path: str) -> dict[str, Any]:
    resolved_path = (project_root / storage_path).resolve()
    files = _list_files(resolved_path)
    if not resolved_path.exists():
        return {
            "path": storage_path,
            "status": "missing",
            "exists": False,
            "file_count": 0,
            "size_bytes": 0,
            "size_human": "0 B",
            "latest_modified_utc": None,
            "sample_files": [],
        }

    latest_modified_utc = _max_timestamp(candidate.stat().st_mtime for candidate in files)
    size_bytes = sum(candidate.stat().st_size for candidate in files)

    return {
        "path": storage_path,
        "status": "present",
        "exists": True,
        "file_count": len(files),
        "size_bytes": size_bytes,
        "size_human": _format_bytes(size_bytes),
        "latest_modified_utc": latest_modified_utc,
        "sample_files": [str(candidate.relative_to(project_root)).replace("\\", "/") for candidate in files[:3]],
    }


def _latest_asset_rows(project_root: Path, asset_name: str) -> dict[str, Any]:
    located = _find_latest_asset_file(project_root, asset_name)
    if located is None:
        return {
            "status": "not_materialized",
            "asset_name": asset_name,
            "asset_file": None,
            "dagster_home": None,
            "rows": [],
        }

    asset_file, dagster_home = located
    try:
        payload = _load_pickled_asset(asset_file)
        rows = [dict(row) for row in _to_rows(payload)]
    except Exception as exc:
        return {
            "status": "load_error",
            "asset_name": asset_name,
            "asset_file": str(asset_file),
            "dagster_home": str(dagster_home),
            "rows": [],
            "error": str(exc),
        }

    return {
        "status": "materialized",
        "asset_name": asset_name,
        "asset_file": str(asset_file),
        "dagster_home": str(dagster_home),
        "rows": rows,
    }


def _row_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    latest_timestamp = None
    for field_name in TIMESTAMP_CANDIDATES:
        field_values = [row.get(field_name) for row in rows if row.get(field_name) is not None]
        latest_timestamp = _max_timestamp(field_values)
        if latest_timestamp is not None:
            break

    client_ids = sorted({str(row.get("client_id") or "").strip() for row in rows if _optional_text(row.get("client_id"))})
    run_ids = sorted({str(row.get("forecast_run_id") or "").strip() for row in rows if _optional_text(row.get("forecast_run_id"))})
    optimization_ids = sorted({str(row.get("optimization_run_id") or "").strip() for row in rows if _optional_text(row.get("optimization_run_id"))})

    return {
        "row_count": len(rows),
        "client_count": len(client_ids),
        "client_ids_preview": client_ids[:3],
        "latest_row_timestamp": latest_timestamp,
        "forecast_run_ids_preview": run_ids[:3],
        "optimization_run_ids_preview": optimization_ids[:3],
    }


def load_manifest(manifest_path: str | Path) -> dict[str, Any]:
    manifest_file = Path(manifest_path).resolve()
    with manifest_file.open("r", encoding="utf-8") as handle:
        manifest = yaml.safe_load(handle) or {}
    if not isinstance(manifest, dict):
        raise ValueError("Manifest root must be a mapping")
    datasets = manifest.get("datasets")
    if not isinstance(datasets, list) or not datasets:
        raise ValueError("Manifest must define a non-empty datasets list")
    manifest["datasets"] = [dict(dataset) for dataset in datasets]
    manifest["_manifest_path"] = str(manifest_file)
    manifest["_project_root"] = str(manifest_file.parents[2])
    return manifest


def _layer_order(manifest: Mapping[str, Any]) -> list[str]:
    layers = manifest.get("layers") or {}
    if isinstance(layers, Mapping):
        return [str(layer_name) for layer_name in layers.keys()]
    return ["bronze", "silver", "gold"]


def _enrich_dataset(project_root: Path, dataset: Mapping[str, Any]) -> dict[str, Any]:
    enriched = dict(dataset)
    storage_path = str(dataset.get("storage_path") or dataset.get("storage_surface") or "")
    enriched["storage_stats"] = _storage_stats(project_root, storage_path) if storage_path else {
        "path": None,
        "status": "missing",
        "exists": False,
        "file_count": 0,
        "size_bytes": 0,
        "size_human": "0 B",
        "latest_modified_utc": None,
        "sample_files": [],
    }

    asset_name = _optional_text(dataset.get("dagster_asset"))
    if asset_name is None or asset_name == "create_all_assets":
        asset_snapshot = {
            "status": "not_applicable",
            "asset_name": asset_name,
            "asset_file": None,
            "dagster_home": None,
            "rows": [],
        }
    else:
        asset_snapshot = _latest_asset_rows(project_root, asset_name)
    asset_rows = asset_snapshot.get("rows", [])
    enriched["asset_snapshot"] = asset_snapshot
    enriched["row_summary"] = _row_summary(asset_rows)
    freshness_snapshot = enriched["row_summary"].get("latest_row_timestamp") or enriched["storage_stats"].get("latest_modified_utc")
    enriched["freshness_snapshot_utc"] = freshness_snapshot
    return enriched


def _layer_stats(datasets: list[dict[str, Any]]) -> dict[str, Any]:
    total_size_bytes = sum(int(dataset["storage_stats"].get("size_bytes") or 0) for dataset in datasets)
    latest_observed_update = _max_timestamp(
        dataset.get("freshness_snapshot_utc") for dataset in datasets if dataset.get("freshness_snapshot_utc")
    )
    return {
        "dataset_count": len(datasets),
        "storage_present_count": sum(1 for dataset in datasets if dataset["storage_stats"].get("exists")),
        "materialized_count": sum(1 for dataset in datasets if dataset["asset_snapshot"].get("status") == "materialized"),
        "file_count": sum(int(dataset["storage_stats"].get("file_count") or 0) for dataset in datasets),
        "size_bytes": total_size_bytes,
        "size_human": _format_bytes(total_size_bytes),
        "latest_observed_update_utc": latest_observed_update,
    }


def _load_customers(project_root: Path) -> list[dict[str, Any]]:
    customers_path = project_root / "customers.yaml"
    if not customers_path.exists():
        return []
    with customers_path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    customers = payload.get("customers") if isinstance(payload, Mapping) else None
    if not isinstance(customers, list):
        return []
    return [dict(customer) for customer in customers if isinstance(customer, Mapping)]


def _select_case_study_customer(customers: list[dict[str, Any]], requested_id: str | None) -> dict[str, Any] | None:
    if not customers:
        return None
    if requested_id:
        for customer in customers:
            if str(customer.get("id") or "").strip() == requested_id:
                selected = dict(customer)
                selected["selection_reason"] = "explicit_cli_selection"
                return selected
    selected = dict(customers[0])
    selected["selection_reason"] = "manifest_default_first_customer"
    return selected


def _customer_energy_metrics(customer: Mapping[str, Any]) -> dict[str, Any]:
    energy_system = customer.get("energy_system") if isinstance(customer.get("energy_system"), Mapping) else {}
    economic_params = customer.get("economic_params") if isinstance(customer.get("economic_params"), Mapping) else {}
    battery_capacity_kwh = _safe_float(energy_system.get("battery_capacity_kwh")) or 0.0
    solar_capacity_kw = _safe_float(energy_system.get("solar_capacity_kw")) or 0.0
    peak_load_kw = _safe_float(energy_system.get("peak_load_kw")) or 0.0
    storage_hours = battery_capacity_kwh / peak_load_kw if peak_load_kw else None
    solar_coverage_ratio = solar_capacity_kw / peak_load_kw if peak_load_kw else None
    return {
        "client_id": _optional_text(customer.get("id")),
        "client_name": _optional_text(customer.get("name")),
        "client_type": _optional_text(customer.get("type")),
        "battery_capacity_kwh": battery_capacity_kwh,
        "solar_capacity_kw": solar_capacity_kw,
        "peak_load_kw": peak_load_kw,
        "storage_hours": storage_hours,
        "solar_coverage_ratio": solar_coverage_ratio,
        "electricity_tariff": _safe_float(economic_params.get("electricity_tariff")),
        "feed_in_tariff": _safe_float(economic_params.get("feed_in_tariff")),
    }


def _fleet_summary(project_root: Path, customers: list[dict[str, Any]]) -> dict[str, Any]:
    asset_snapshot = _latest_asset_rows(project_root, "multi_client_analytics")
    rows = asset_snapshot.get("rows", [])
    if rows:
        sorted_storage = sorted(rows, key=lambda row: _safe_float(row.get("storage_rank")) or 9999.0)
        sorted_solar = sorted(rows, key=lambda row: _safe_float(row.get("solar_rank")) or 9999.0)
        return {
            "status": "materialized_asset",
            "source_surface": "multi_client_analytics",
            "provenance": "simulated",
            "client_count": len(rows),
            "top_storage_client": _optional_text(sorted_storage[0].get("client_id")) if sorted_storage else None,
            "top_solar_client": _optional_text(sorted_solar[0].get("client_id")) if sorted_solar else None,
            "latest_update_utc": _row_summary(rows).get("latest_row_timestamp"),
        }

    metrics = [_customer_energy_metrics(customer) for customer in customers]
    if not metrics:
        return {
            "status": "missing",
            "source_surface": "customers.yaml",
            "provenance": "simulated",
            "client_count": 0,
            "top_storage_client": None,
            "top_solar_client": None,
            "latest_update_utc": None,
        }

    sorted_storage = sorted(metrics, key=lambda row: row.get("storage_hours") or -1.0, reverse=True)
    sorted_solar = sorted(metrics, key=lambda row: row.get("solar_coverage_ratio") or -1.0, reverse=True)
    return {
        "status": "customers_yaml_fallback",
        "source_surface": "customers.yaml",
        "provenance": "simulated",
        "client_count": len(metrics),
        "top_storage_client": sorted_storage[0].get("client_id") if sorted_storage else None,
        "top_solar_client": sorted_solar[0].get("client_id") if sorted_solar else None,
        "latest_update_utc": None,
    }


def _asset_source_mode(project_root: Path, asset_name: str, *, fallback_tokens: tuple[str, ...], simulated_tokens: tuple[str, ...] = ()) -> dict[str, Any]:
    snapshot = _latest_asset_rows(project_root, asset_name)
    rows = snapshot.get("rows", [])
    if not rows:
        return {
            "asset_name": asset_name,
            "status": snapshot.get("status"),
            "provenance": "unknown",
            "evidence": None,
        }

    text_values = []
    for row in rows[:50]:
        for key in ("source", "state_source", "telemetry_classification", "state_source_detail"):
            value = _optional_text(row.get(key))
            if value:
                text_values.append(value.lower())

    for token in fallback_tokens:
        if any(token in value for value in text_values):
            return {
                "asset_name": asset_name,
                "status": snapshot.get("status"),
                "provenance": "fallback-derived",
                "evidence": token,
            }
    for token in simulated_tokens:
        if any(token in value for value in text_values):
            return {
                "asset_name": asset_name,
                "status": snapshot.get("status"),
                "provenance": "simulated",
                "evidence": token,
            }
    return {
        "asset_name": asset_name,
        "status": snapshot.get("status"),
        "provenance": "real",
        "evidence": text_values[0] if text_values else None,
    }


def _load_json_file(project_root: Path, relative_path: str) -> Any:
    path = project_root / relative_path
    if not path.exists() or not path.is_file():
        return None
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _schedule_totals(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {
            "row_count": 0,
            "client_count": 0,
            "purchase_cost_eur": None,
            "export_revenue_eur": None,
            "degradation_penalty_eur": None,
            "net_cost_eur": None,
            "forecast_run_ids": [],
            "optimization_run_ids": [],
        }

    purchase_cost = 0.0
    export_revenue = 0.0
    degradation_penalty = 0.0
    net_cost = 0.0
    client_ids: set[str] = set()
    forecast_ids: set[str] = set()
    optimization_ids: set[str] = set()
    seen_total_cost_by_client: dict[str, float] = {}

    for row in rows:
        client_id = _optional_text(row.get("client_id")) or "default"
        client_ids.add(client_id)
        forecast_id = _optional_text(row.get("forecast_run_id"))
        optimization_id = _optional_text(row.get("optimization_run_id"))
        if forecast_id:
            forecast_ids.add(forecast_id)
        if optimization_id:
            optimization_ids.add(optimization_id)

        purchase_cost += _safe_float(row.get("purchase_cost_eur")) or 0.0
        export_revenue += _safe_float(row.get("export_revenue_eur")) or 0.0
        degradation_penalty += _safe_float(row.get("degradation_penalty_eur")) or 0.0
        total_net_cost = _safe_float(row.get("total_net_cost_eur"))
        if total_net_cost is not None and client_id not in seen_total_cost_by_client:
            seen_total_cost_by_client[client_id] = total_net_cost

    if seen_total_cost_by_client:
        net_cost = sum(seen_total_cost_by_client.values())
    else:
        net_cost = sum((_safe_float(row.get("net_cost_eur")) or 0.0) for row in rows)

    return {
        "row_count": len(rows),
        "client_count": len(client_ids),
        "purchase_cost_eur": round(purchase_cost, 6),
        "export_revenue_eur": round(export_revenue, 6),
        "degradation_penalty_eur": round(degradation_penalty, 6),
        "net_cost_eur": round(net_cost, 6),
        "forecast_run_ids": sorted(forecast_ids),
        "optimization_run_ids": sorted(optimization_ids),
    }


def build_catalog_payload(manifest_path: str | Path, case_study_tenant: str | None = None) -> dict[str, Any]:
    manifest = load_manifest(manifest_path)
    project_root = Path(manifest["_project_root"])
    manifest_file = Path(manifest["_manifest_path"])
    customers = _load_customers(project_root)
    case_study_customer = _select_case_study_customer(customers, case_study_tenant)

    layers: list[dict[str, Any]] = []
    for layer_name in _layer_order(manifest):
        layer_meta = dict((manifest.get("layers") or {}).get(layer_name) or {})
        datasets = [
            _enrich_dataset(project_root, dataset)
            for dataset in manifest["datasets"]
            if str(dataset.get("layer")) == layer_name
        ]
        layers.append(
            {
                "layer": layer_name,
                "title": _normalize_name(layer_name),
                "narrative": layer_meta.get("narrative"),
                "storage_surface": layer_meta.get("storage_surface"),
                "stats": _layer_stats(datasets),
                "datasets": datasets,
            }
        )

    fleet_view = _fleet_summary(project_root, customers)
    source_modes = {
        "market": _asset_source_mode(project_root, "market_data_asset", fallback_tokens=("synthetic",)),
        "weather": _asset_source_mode(project_root, "weather_asset", fallback_tokens=("synthetic",)),
        "client_state": _asset_source_mode(
            project_root,
            "client_state_asset",
            fallback_tokens=("config_fallback", "fallback"),
            simulated_tokens=("simulator", "simulator_backed"),
        ),
    }

    case_study = None
    if case_study_customer is not None:
        metrics = _customer_energy_metrics(case_study_customer)
        case_study = {
            "client_id": metrics["client_id"],
            "client_name": metrics["client_name"],
            "selection_reason": case_study_customer.get("selection_reason"),
            "metrics": [
                {
                    "name": "battery_capacity_kwh",
                    "value": metrics["battery_capacity_kwh"],
                    "provenance": "simulated",
                    "surface": "customers.yaml",
                },
                {
                    "name": "solar_capacity_kw",
                    "value": metrics["solar_capacity_kw"],
                    "provenance": "simulated",
                    "surface": "customers.yaml",
                },
                {
                    "name": "peak_load_kw",
                    "value": metrics["peak_load_kw"],
                    "provenance": "simulated",
                    "surface": "customers.yaml",
                },
                {
                    "name": "storage_hours",
                    "value": metrics["storage_hours"],
                    "provenance": "simulated",
                    "surface": fleet_view["source_surface"],
                },
                {
                    "name": "solar_coverage_ratio",
                    "value": metrics["solar_coverage_ratio"],
                    "provenance": "simulated",
                    "surface": fleet_view["source_surface"],
                },
                {
                    "name": "market_input_mode",
                    "value": source_modes["market"]["provenance"],
                    "provenance": source_modes["market"]["provenance"],
                    "surface": "market_data_asset",
                },
                {
                    "name": "weather_input_mode",
                    "value": source_modes["weather"]["provenance"],
                    "provenance": source_modes["weather"]["provenance"],
                    "surface": "weather_asset",
                },
                {
                    "name": "client_state_mode",
                    "value": source_modes["client_state"]["provenance"],
                    "provenance": source_modes["client_state"]["provenance"],
                    "surface": "client_state_asset",
                },
            ],
        }

    return {
        "generated_at_utc": _file_modified_iso(manifest_file),
        "manifest": manifest,
        "project_root": str(project_root),
        "runtime_entrypoint": manifest.get("runtime_entrypoint"),
        "logical_overlay_only": bool(manifest.get("logical_overlay_only", True)),
        "layers": layers,
        "fleet_view": fleet_view,
        "case_study": case_study,
        "source_modes": source_modes,
    }


def build_gold_summary(manifest_path: str | Path, case_study_tenant: str | None = None) -> dict[str, Any]:
    catalog = build_catalog_payload(manifest_path, case_study_tenant=case_study_tenant)
    manifest = catalog["manifest"]
    project_root = Path(catalog["project_root"])

    benchmark_snapshot = _latest_asset_rows(project_root, "forecast_value_benchmark_asset")
    benchmark_rows = benchmark_snapshot.get("rows", [])
    benchmark_status = _materialization_status(benchmark_snapshot)
    skipped_candidate_count = sum(
        1
        for row in benchmark_rows
        if _optional_text(row.get("benchmark_candidate_status")) == "skipped"
    )
    evaluated_candidate_count = sum(
        1
        for row in benchmark_rows
        if _optional_text(row.get("benchmark_candidate_status")) != "skipped"
    )
    model_vs_model = {
        "status": benchmark_status,
        "system_of_record": "forecast_value_benchmark_asset",
        "provenance": "benchmarked",
        "candidate_count": len(benchmark_rows),
        "evaluated_candidate_count": evaluated_candidate_count,
        "skipped_candidate_count": skipped_candidate_count,
        "promotion_gate_versions": sorted(
            {
                version
                for version in (_optional_text(row.get("promotion_gate_version")) for row in benchmark_rows)
                if version is not None
            }
        ),
        "top_candidates": [
            {
                "model_name": _optional_text(row.get("model_name")),
                "model_family": _optional_text(row.get("model_family")),
                "candidate_status": _optional_text(row.get("benchmark_candidate_status")),
                "benchmark_rmse": _safe_float(
                    _first_present(row, "benchmark_rmse", "metric_benchmark_rmse", "eval_rmse", "metric_eval_rmse")
                ),
                "benchmark_mae": _safe_float(
                    _first_present(row, "benchmark_mae", "metric_benchmark_mae", "eval_mae", "metric_eval_mae")
                ),
                "benchmark_value_capture_ratio": _safe_float(
                    _first_present(
                        row,
                        "benchmark_value_capture_ratio",
                        "metric_benchmark_value_capture_ratio",
                        "eval_value_capture_ratio",
                        "metric_eval_value_capture_ratio",
                    )
                ),
                "benchmark_conservative_value_capture_ratio": _safe_float(
                    _first_present(
                        row,
                        "benchmark_conservative_value_capture_ratio",
                        "metric_benchmark_conservative_value_capture_ratio",
                    )
                ),
                "promotion_decision": _optional_text(
                    _first_present(row, "promotion_decision", "param_promotion_decision")
                ),
                "promotion_decision_reason": _optional_text(
                    _first_present(row, "promotion_decision_reason", "param_promotion_decision_reason")
                ),
                "skip_reason": _optional_text(
                    _first_present(row, "benchmark_candidate_skip_reason", "param_benchmark_candidate_skip_reason")
                ),
            }
            for row in benchmark_rows[:5]
        ],
        "supporting_outputs": (manifest.get("experiments") or {}).get("model_vs_model", {}).get("supporting_outputs", []),
    }

    mlflow_snapshot = _latest_asset_rows(project_root, "mlflow_tracking_asset")
    mlflow_rows = mlflow_snapshot.get("rows", [])
    mlflow_forecast_rows = [
        row
        for row in mlflow_rows
        if _optional_text(row.get("model_name"))
        or _optional_text(row.get("tag_benchmark_type")) == "forecast_value"
    ]
    mlflow_tracking = {
        "status": _materialization_status(mlflow_snapshot),
        "system_of_record": "mlflow_tracking_asset",
        "log_count": len(mlflow_rows),
        "forecast_benchmark_run_count": len(mlflow_forecast_rows),
        "latest_timestamp": _max_timestamp(
            _first_present(row, "timestamp", "fetched_at") for row in mlflow_rows
        ),
        "experiment_names": sorted(
            {
                experiment_name
                for experiment_name in (_optional_text(row.get("experiment_name")) for row in mlflow_rows)
                if experiment_name is not None
            }
        ),
        "forecast_runs": [
            {
                "run_name": _optional_text(row.get("run_name")),
                "experiment_name": _optional_text(row.get("experiment_name")),
                "model_name": _optional_text(row.get("model_name")),
                "benchmark_rmse": _safe_float(
                    _first_present(row, "metric_benchmark_rmse", "metric_eval_rmse")
                ),
                "benchmark_mae": _safe_float(
                    _first_present(row, "metric_benchmark_mae", "metric_eval_mae")
                ),
                "benchmark_value_capture_ratio": _safe_float(
                    _first_present(row, "metric_benchmark_value_capture_ratio", "metric_eval_value_capture_ratio")
                ),
                "promotion_decision": _optional_text(row.get("param_promotion_decision")),
            }
            for row in mlflow_forecast_rows[:5]
        ],
    }

    forecast_snapshot = _latest_asset_rows(project_root, "price_forecast_asset")
    baseline_snapshot = _latest_asset_rows(project_root, "optimization_schedule_asset")
    milp_snapshot = _latest_asset_rows(project_root, "optimization_schedule_milp_asset")
    forecast_rows = forecast_snapshot.get("rows", [])
    baseline_rows = baseline_snapshot.get("rows", [])
    milp_rows = milp_snapshot.get("rows", [])

    run_vs_run = {
        "forecast": {
            "status": forecast_snapshot.get("status"),
            **_row_summary(forecast_rows),
        },
        "baseline_schedule": {
            "status": baseline_snapshot.get("status"),
            **_schedule_totals(baseline_rows),
        },
        "milp_schedule": {
            "status": milp_snapshot.get("status"),
            **_schedule_totals(milp_rows),
        },
    }

    baseline_totals = _schedule_totals(baseline_rows)
    milp_totals = _schedule_totals(milp_rows)
    optimizer_vs_optimizer = {
        "status": "comparable" if baseline_rows and milp_rows else "partial_or_missing",
        "provenance": "real" if catalog["source_modes"]["market"]["provenance"] == "real" else "fallback-derived",
        "baseline": baseline_totals,
        "milp": milp_totals,
        "net_cost_delta_eur": None
        if baseline_totals.get("net_cost_eur") is None or milp_totals.get("net_cost_eur") is None
        else round((milp_totals["net_cost_eur"] or 0.0) - (baseline_totals["net_cost_eur"] or 0.0), 6),
    }

    trained_model_snapshot = _latest_asset_rows(project_root, "trained_model_asset")
    trained_model_rows = trained_model_snapshot.get("rows", [])
    model_metadata_snapshot = _latest_asset_rows(project_root, "model_metadata_asset")
    model_metadata_rows = model_metadata_snapshot.get("rows", [])
    model_artifacts = {
        "trained_model": {
            "status": _materialization_status(trained_model_snapshot),
            "system_of_record": "trained_model_asset",
            "row_count": len(trained_model_rows),
            "latest_logged_at": _max_timestamp(row.get("logged_at") for row in trained_model_rows),
            "model_names": sorted(
                {
                    model_name
                    for model_name in (_optional_text(row.get("model_name")) for row in trained_model_rows)
                    if model_name is not None
                }
            ),
            "run_ids": sorted(
                {
                    run_id
                    for run_id in (_optional_text(row.get("run_id")) for row in trained_model_rows)
                    if run_id is not None
                }
            ),
            "artifact_uris": [
                artifact_uri
                for artifact_uri in (_optional_text(row.get("artifact_uri")) for row in trained_model_rows)
                if artifact_uri is not None
            ][:3],
        },
        "metadata_lookup": {
            "status": _materialization_status(model_metadata_snapshot),
            "system_of_record": "model_metadata_asset",
            "row_count": len(model_metadata_rows),
            "latest_fetched_at": _max_timestamp(row.get("fetched_at") for row in model_metadata_rows),
            "successful_rows": sum(
                1 for row in model_metadata_rows if (_optional_text(row.get("status")) or "").lower() == "success"
            ),
            "error_rows": sum(
                1 for row in model_metadata_rows if (_optional_text(row.get("status")) or "").lower() not in {"", "success"}
            ),
        },
    }

    ppo_validation = _load_json_file(project_root, "data/results/ppo_validation_feb2026.json") or {}
    arbitrage_ranges = _load_json_file(project_root, "data/results/arbitrage_ranges.json") or {}
    business_metrics = {
        "provenance": "benchmarked",
        "ppo_validation": {
            "status": "available" if ppo_validation else "missing",
            "daily_baseline": ppo_validation.get("daily_baseline"),
            "daily_optimized": ppo_validation.get("daily_optimized"),
            "daily_savings": ppo_validation.get("daily_savings"),
            "improvement_pct": ppo_validation.get("improvement_pct"),
            "days_analyzed": ppo_validation.get("days_analyzed"),
        },
        "arbitrage_ranges": {
            "status": "available" if arbitrage_ranges else "missing",
            "days_analyzed": (arbitrage_ranges.get("price_statistics") or {}).get("days_analyzed"),
            "avg_daily_spread_eur": (arbitrage_ranges.get("price_statistics") or {}).get("avg_daily_spread_eur"),
            "median_daily_spread_eur": (arbitrage_ranges.get("price_statistics") or {}).get("median_daily_spread_eur"),
        },
        "schedule_totals": {
            "baseline": baseline_totals,
            "milp": milp_totals,
        },
        "reconciliation_status": {
            "status": "dagster_asset_check_surface",
            "system_of_record": "optimization_schedule_contract_checks",
            "provenance": "benchmarked",
        },
    }

    return {
        "generated_at_utc": catalog["generated_at_utc"],
        "runtime_entrypoint": catalog["runtime_entrypoint"],
        "logical_overlay_only": catalog["logical_overlay_only"],
        "layer_summary": [
            {
                "layer": layer["layer"],
                "dataset_count": layer["stats"]["dataset_count"],
                "materialized_count": layer["stats"]["materialized_count"],
                "storage_present_count": layer["stats"]["storage_present_count"],
                "latest_observed_update_utc": layer["stats"]["latest_observed_update_utc"],
            }
            for layer in catalog["layers"]
        ],
        "source_modes": catalog["source_modes"],
        "fleet_view": catalog["fleet_view"],
        "case_study": catalog["case_study"],
        "model_vs_model": model_vs_model,
        "mlflow_tracking": mlflow_tracking,
        "run_vs_run": run_vs_run,
        "optimizer_vs_optimizer": optimizer_vs_optimizer,
        "model_artifacts": model_artifacts,
        "business_metrics": business_metrics,
        "limitations": ((manifest.get("presentation_defaults") or {}).get("limitations") or []),
    }


def _dataset_runtime_snapshot(dataset: Mapping[str, Any]) -> str:
    storage = dataset["storage_stats"]
    row_summary = dataset["row_summary"]
    parts = [
        f"storage={storage.get('status')} ({storage.get('file_count')} files, {storage.get('size_human')})",
    ]
    latest_modified = storage.get("latest_modified_utc")
    if latest_modified:
        parts.append(f"latest_file={latest_modified}")
    if dataset["asset_snapshot"].get("status") == "materialized":
        parts.append(f"asset_rows={row_summary.get('row_count')}")
        latest_row = row_summary.get("latest_row_timestamp")
        if latest_row:
            parts.append(f"latest_row={latest_row}")
    else:
        parts.append(f"asset_status={dataset['asset_snapshot'].get('status')}")
    return "; ".join(parts)


def render_catalog_markdown(catalog: Mapping[str, Any]) -> str:
    lines = [
        "# Bronze/Silver/Gold Dataset Catalog",
        "",
        f"Generated from the medallion manifest and current local runtime surfaces at {catalog['generated_at_utc']}.",
        "",
        "This catalog is rendered from the canonical manifest, current folder state, and the latest Dagster materializations when they are available locally.",
        "",
        "## Layer Summary",
        "",
        "| Layer | Datasets | Materialized | Storage Present | Files | Size | Latest Observed Update |",
        "| --- | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for layer in catalog["layers"]:
        stats = layer["stats"]
        lines.append(
            f"| {layer['title']} | {stats['dataset_count']} | {stats['materialized_count']} | {stats['storage_present_count']} | {stats['file_count']} | {stats['size_human']} | {stats['latest_observed_update_utc'] or 'n/a'} |"
        )

    for layer in catalog["layers"]:
        lines.extend(
            [
                "",
                f"## {layer['title']}",
                "",
                f"{layer['narrative']}",
                "",
                "| Dataset | Dagster Asset | Source Kind | Fallback Mode | Freshness Field | Quality Owner | Storage Path | Runtime Snapshot |",
                "| --- | --- | --- | --- | --- | --- | --- | --- |",
            ]
        )
        for dataset in layer["datasets"]:
            lines.append(
                "| {title} | {asset} | {source_kind} | {fallback_mode} | {freshness_field} | {quality_owner} | {storage_path} | {runtime_snapshot} |".format(
                    title=dataset.get("title") or dataset.get("dataset_id"),
                    asset=dataset.get("dagster_asset") or "n/a",
                    source_kind=dataset.get("source_kind") or "n/a",
                    fallback_mode=dataset.get("fallback_mode") or "n/a",
                    freshness_field=dataset.get("freshness_field") or "n/a",
                    quality_owner=dataset.get("quality_owner") or "n/a",
                    storage_path=dataset.get("storage_path") or dataset.get("storage_surface") or "n/a",
                    runtime_snapshot=_dataset_runtime_snapshot(dataset),
                )
            )

    fleet_view = catalog.get("fleet_view") or {}
    lines.extend(
        [
            "",
            "## Fleet View",
            "",
            f"- Source surface: {fleet_view.get('source_surface') or 'n/a'}",
            f"- Status: {fleet_view.get('status') or 'n/a'}",
            f"- Client count: {fleet_view.get('client_count') or 0}",
            f"- Top storage client: {fleet_view.get('top_storage_client') or 'n/a'} ({fleet_view.get('provenance') or 'unknown'})",
            f"- Top solar client: {fleet_view.get('top_solar_client') or 'n/a'} ({fleet_view.get('provenance') or 'unknown'})",
        ]
    )

    case_study = catalog.get("case_study")
    lines.extend(["", "## Case Study View", ""])
    if case_study is None:
        lines.append("No case-study tenant could be resolved from customers.yaml.")
    else:
        lines.append(
            f"Selected tenant: `{case_study['client_id']}` ({case_study['client_name']}) via `{case_study['selection_reason']}`."
        )
        lines.append("")
        lines.append("| Metric | Value | Provenance | Surface |")
        lines.append("| --- | ---: | --- | --- |")
        for metric in case_study["metrics"]:
            value = metric["value"]
            if isinstance(value, str):
                rendered_value = value
            else:
                rendered_value = _format_number(_safe_float(value), digits=3)
            lines.append(
                f"| {metric['name']} | {rendered_value} | {metric['provenance']} | {metric['surface']} |"
            )

    lines.extend(
        [
            "",
            "## Limitations",
            "",
            "- This catalog is a logical overlay on the current Dagster runtime, not a physical medallion warehouse rewrite.",
            "- Storage paths are presentation anchors; actual Dagster materialization can still route through the configured IO manager.",
            "- Missing Dagster materializations are rendered honestly as absent local evidence rather than backfilled with invented numbers.",
        ]
    )
    return "\n".join(lines) + "\n"


def render_experiments_markdown(catalog: Mapping[str, Any], summary: Mapping[str, Any]) -> str:
    model_vs_model = summary["model_vs_model"]
    mlflow_tracking = summary.get("mlflow_tracking") or {}
    run_vs_run = summary["run_vs_run"]
    optimizer_vs_optimizer = summary["optimizer_vs_optimizer"]
    model_artifacts = summary.get("model_artifacts") or {}
    business_metrics = summary["business_metrics"]
    case_study = summary.get("case_study")
    fleet_view = summary.get("fleet_view") or {}

    lines = [
        "# Experiments And Results Scorecard",
        "",
        f"Generated from current runtime evidence at {summary['generated_at_utc']}.",
        "",
        "This scorecard reuses existing Dagster benchmark, MLflow, optimization lineage, reconciliation, and fleet-analytics surfaces instead of creating a second observability plane.",
        "",
        "## Model-vs-Model",
        "",
        f"- System of record: `{model_vs_model['system_of_record']}`",
        f"- Status: `{model_vs_model['status']}`",
        f"- Provenance: `{model_vs_model['provenance']}`",
        f"- Candidate rows: `{model_vs_model['candidate_count']}` total, `{model_vs_model.get('evaluated_candidate_count', 0)}` evaluated, `{model_vs_model.get('skipped_candidate_count', 0)}` skipped.",
        f"- MLflow tracking surface: `{mlflow_tracking.get('status') or 'not_materialized'}` with `{mlflow_tracking.get('log_count') or 0}` logged runs and latest timestamp `{mlflow_tracking.get('latest_timestamp') or 'n/a'}`.",
    ]
    if model_vs_model["top_candidates"]:
        lines.extend(
            [
                "",
                "| Model | Family | Candidate Status | RMSE | MAE | Value Capture | Conservative Value Capture | Promotion | Reason |",
                "| --- | --- | --- | ---: | ---: | ---: | ---: | --- | --- |",
            ]
        )
        for candidate in model_vs_model["top_candidates"]:
            lines.append(
                f"| {candidate.get('model_name') or 'n/a'} | {candidate.get('model_family') or 'n/a'} | {candidate.get('candidate_status') or 'n/a'} | {_format_number(candidate.get('benchmark_rmse'))} | {_format_number(candidate.get('benchmark_mae'))} | {_format_number(candidate.get('benchmark_value_capture_ratio'), 3)} | {_format_number(candidate.get('benchmark_conservative_value_capture_ratio'), 3)} | {candidate.get('promotion_decision') or 'n/a'} | {candidate.get('skip_reason') or candidate.get('promotion_decision_reason') or 'n/a'} |"
            )
    else:
        lines.append("- No local benchmark rows were materialized; the benchmark asset remains the declared system of record.")
    if mlflow_tracking.get("forecast_runs"):
        lines.extend(
            [
                "",
                "### MLflow Support",
                "",
                "| Run | Experiment | Model | RMSE | MAE | Value Capture | Promotion |",
                "| --- | --- | --- | ---: | ---: | ---: | --- |",
            ]
        )
        for row in mlflow_tracking["forecast_runs"]:
            lines.append(
                f"| {row.get('run_name') or 'n/a'} | {row.get('experiment_name') or 'n/a'} | {row.get('model_name') or 'n/a'} | {_format_number(row.get('benchmark_rmse'))} | {_format_number(row.get('benchmark_mae'))} | {_format_number(row.get('benchmark_value_capture_ratio'), 3)} | {row.get('promotion_decision') or 'n/a'} |"
            )

    lines.extend(
        [
            "",
            "## Run-vs-Run",
            "",
            f"- Forecast status: `{run_vs_run['forecast']['status']}` with {run_vs_run['forecast']['row_count']} rows and latest timestamp `{run_vs_run['forecast']['latest_row_timestamp'] or 'n/a'}`.",
            f"- Baseline schedule status: `{run_vs_run['baseline_schedule']['status']}` with forecast runs {run_vs_run['baseline_schedule']['forecast_run_ids'] or []}.",
            f"- MILP schedule status: `{run_vs_run['milp_schedule']['status']}` with forecast runs {run_vs_run['milp_schedule']['forecast_run_ids'] or []}.",
            f"- Trained model surface: `{(model_artifacts.get('trained_model') or {}).get('status') or 'not_materialized'}` with `{(model_artifacts.get('trained_model') or {}).get('row_count') or 0}` rows and latest logged-at `{(model_artifacts.get('trained_model') or {}).get('latest_logged_at') or 'n/a'}`.",
            f"- Model metadata surface: `{(model_artifacts.get('metadata_lookup') or {}).get('status') or 'not_materialized'}` with `{(model_artifacts.get('metadata_lookup') or {}).get('row_count') or 0}` rows and latest fetched-at `{(model_artifacts.get('metadata_lookup') or {}).get('latest_fetched_at') or 'n/a'}`.",
            "",
            "## Optimizer-vs-Optimizer",
            "",
            f"- Comparison status: `{optimizer_vs_optimizer['status']}`",
            f"- Provenance: `{optimizer_vs_optimizer['provenance']}`",
            "",
            "| Optimizer | Clients | Rows | Purchase Cost EUR | Export Revenue EUR | Degradation Penalty EUR | Net Cost EUR |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
            f"| Baseline DP | {optimizer_vs_optimizer['baseline']['client_count']} | {optimizer_vs_optimizer['baseline']['row_count']} | {_format_number(optimizer_vs_optimizer['baseline']['purchase_cost_eur'])} | {_format_number(optimizer_vs_optimizer['baseline']['export_revenue_eur'])} | {_format_number(optimizer_vs_optimizer['baseline']['degradation_penalty_eur'])} | {_format_number(optimizer_vs_optimizer['baseline']['net_cost_eur'])} |",
            f"| MILP | {optimizer_vs_optimizer['milp']['client_count']} | {optimizer_vs_optimizer['milp']['row_count']} | {_format_number(optimizer_vs_optimizer['milp']['purchase_cost_eur'])} | {_format_number(optimizer_vs_optimizer['milp']['export_revenue_eur'])} | {_format_number(optimizer_vs_optimizer['milp']['degradation_penalty_eur'])} | {_format_number(optimizer_vs_optimizer['milp']['net_cost_eur'])} |",
            "",
            f"Net-cost delta (MILP - Baseline): `{_format_number(optimizer_vs_optimizer['net_cost_delta_eur'])}` EUR.",
            "",
            "## Business Metrics",
            "",
            f"- PPO validation status: `{business_metrics['ppo_validation']['status']}` with daily savings `{_format_number(_safe_float(business_metrics['ppo_validation']['daily_savings']))}` and improvement `{_format_number(_safe_float(business_metrics['ppo_validation']['improvement_pct']))}`%.",
            f"- Arbitrage range status: `{business_metrics['arbitrage_ranges']['status']}` with median daily spread `{_format_number(_safe_float(business_metrics['arbitrage_ranges']['median_daily_spread_eur']))}` EUR.",
            f"- Reconciliation status source: `{business_metrics['reconciliation_status']['system_of_record']}` ({business_metrics['reconciliation_status']['status']}).",
            "",
            "## Fleet View",
            "",
            f"- Source surface: `{fleet_view.get('source_surface') or 'n/a'}`",
            f"- Status: `{fleet_view.get('status') or 'n/a'}`",
            f"- Client count: `{fleet_view.get('client_count') or 0}`",
            f"- Top storage client: `{fleet_view.get('top_storage_client') or 'n/a'}` tagged `{fleet_view.get('provenance') or 'unknown'}`.",
            f"- Top solar client: `{fleet_view.get('top_solar_client') or 'n/a'}` tagged `{fleet_view.get('provenance') or 'unknown'}`.",
            "",
            "## Case Study View",
            "",
        ]
    )
    if case_study is None:
        lines.append("No case-study tenant could be resolved.")
    else:
        lines.append(
            f"Selected tenant `{case_study['client_id']}` ({case_study['client_name']}) using `{case_study['selection_reason']}`."
        )
        lines.append("")
        lines.append("| Metric | Value | Provenance | Surface |")
        lines.append("| --- | ---: | --- | --- |")
        for metric in case_study["metrics"]:
            value = metric["value"]
            rendered_value = value if isinstance(value, str) else _format_number(_safe_float(value), digits=3)
            lines.append(
                f"| {metric['name']} | {rendered_value} | {metric['provenance']} | {metric['surface']} |"
            )

    lines.extend(
        [
            "",
            "## Limitations And Deferrals",
            "",
            "- This scorecard packages current runtime evidence; it does not claim a production warehouse or a completed backend re-root.",
            "- Synthetic market or weather fallback can legitimately affect Gold outputs during local runs, and that provenance is surfaced instead of hidden.",
            "- MLflow-backed and benchmark-backed evidence can be absent locally if those Dagster jobs have not been materialized in the current environment.",
        ]
    )
    return "\n".join(lines) + "\n"


def render_preview_markdown(catalog: Mapping[str, Any], summary: Mapping[str, Any]) -> str:
    lines = [
        "# Medallion Preview",
        "",
        f"Generated at {catalog['generated_at_utc']} from the supervisor medallion manifest.",
        "",
        "## Layer Snapshot",
        "",
        "| Layer | Datasets | Materialized | Latest Update |",
        "| --- | ---: | ---: | --- |",
    ]
    for layer in catalog["layers"]:
        stats = layer["stats"]
        lines.append(
            f"| {layer['title']} | {stats['dataset_count']} | {stats['materialized_count']} | {stats['latest_observed_update_utc'] or 'n/a'} |"
        )
    lines.extend(
        [
            "",
            "## Provenance Snapshot",
            "",
            f"- Market input mode: `{catalog['source_modes']['market']['provenance']}`",
            f"- Weather input mode: `{catalog['source_modes']['weather']['provenance']}`",
            f"- Client-state mode: `{catalog['source_modes']['client_state']['provenance']}`",
            "",
            "## Fleet And Case Study",
            "",
            f"- Fleet source: `{catalog['fleet_view']['source_surface']}` with status `{catalog['fleet_view']['status']}` and {catalog['fleet_view']['client_count']} clients.",
        ]
    )
    case_study = catalog.get("case_study")
    if case_study is not None:
        lines.append(
            f"- Case study tenant: `{case_study['client_id']}` ({case_study['client_name']}) via `{case_study['selection_reason']}`."
        )
    lines.extend(
        [
            "",
            "## Experiment Snapshot",
            "",
            f"- Model-vs-model status: `{summary['model_vs_model']['status']}` from `{summary['model_vs_model']['system_of_record']}`.",
            f"- Optimizer-vs-optimizer status: `{summary['optimizer_vs_optimizer']['status']}`.",
            f"- PPO validation status: `{summary['business_metrics']['ppo_validation']['status']}`.",
        ]
    )
    return "\n".join(lines) + "\n"


def render_output(
    manifest_path: str | Path,
    *,
    output_format: str,
    output_path: str | Path,
    case_study_tenant: str | None = None,
    include_experiments: bool = False,
) -> str:
    catalog = build_catalog_payload(manifest_path, case_study_tenant=case_study_tenant)
    summary = build_gold_summary(manifest_path, case_study_tenant=case_study_tenant)
    output_name = Path(output_path).name.lower()

    if output_format == "json":
        return json.dumps(summary, indent=2, sort_keys=True)

    if include_experiments or "scorecard" in output_name or "experiments" in output_name:
        return render_experiments_markdown(catalog, summary)
    if "catalog" in output_name:
        return render_catalog_markdown(catalog)
    return render_preview_markdown(catalog, summary)


def write_output(output_path: str | Path, content: str) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


__all__ = [
    "build_catalog_payload",
    "build_gold_summary",
    "load_manifest",
    "render_catalog_markdown",
    "render_experiments_markdown",
    "render_output",
    "render_preview_markdown",
    "write_output",
]