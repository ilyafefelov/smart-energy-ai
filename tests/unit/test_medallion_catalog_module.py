from __future__ import annotations

import os
from datetime import datetime, timezone
import json
from pathlib import Path

import yaml

from src.data_pipeline import medallion_catalog


def test_load_manifest_and_build_catalog_payload(tmp_path: Path, monkeypatch) -> None:
    project_root = tmp_path / "repo"
    (project_root / "artifacts" / "medallion").mkdir(parents=True)
    (project_root / "data" / "raw").mkdir(parents=True)
    (project_root / "data" / "results").mkdir(parents=True)
    (project_root / "data" / "raw" / "market.json").write_text("{}", encoding="utf-8")
    (project_root / "data" / "results" / "summary.json").write_text("{}", encoding="utf-8")
    (project_root / "customers.yaml").write_text(
        yaml.safe_dump(
            {
                "customers": [
                    {
                        "id": "tenant-alpha",
                        "name": "Alpha Site",
                        "type": "commercial",
                        "energy_system": {
                            "battery_capacity_kwh": 120.0,
                            "solar_capacity_kw": 60.0,
                            "peak_load_kw": 80.0,
                        },
                        "economic_params": {
                            "electricity_tariff": 0.12,
                            "feed_in_tariff": 0.08,
                        },
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    manifest_path = project_root / "artifacts" / "medallion" / "medallion_dataset_manifest.yaml"
    manifest_path.write_text(
        yaml.safe_dump(
            {
                "runtime_entrypoint": "src/definitions.py",
                "logical_overlay_only": True,
                "layers": {
                    "bronze": {"narrative": "Bronze layer", "storage_surface": "data/raw"},
                    "gold": {"narrative": "Gold layer", "storage_surface": "data/results"},
                },
                "datasets": [
                    {
                        "dataset_id": "market_data_asset",
                        "title": "Market",
                        "layer": "bronze",
                        "dagster_asset": "market_data_asset",
                        "storage_path": "data/raw/market.json",
                        "source_kind": "real_with_synthetic_fallback",
                        "fallback_mode": "synthetic_market_on_source_failure",
                        "freshness_field": "timestamp",
                        "quality_owner": "market_validation",
                    },
                    {
                        "dataset_id": "gold_summary",
                        "title": "Gold Summary",
                        "layer": "gold",
                        "dagster_asset": "optimization_schedule_asset",
                        "storage_path": "data/results/summary.json",
                        "source_kind": "optimization_output",
                        "fallback_mode": "empty_schedule_when_forecast_missing",
                        "freshness_field": "forecast_freshness_minutes",
                        "quality_owner": "optimization_schedule_contract_checks",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    fixed_manifest_time = datetime(2026, 4, 19, 2, 15, 0, tzinfo=timezone.utc).timestamp()
    os.utime(manifest_path, (fixed_manifest_time, fixed_manifest_time))
    expected_generated_at = datetime.fromtimestamp(
        manifest_path.stat().st_mtime,
        tz=timezone.utc,
    ).replace(microsecond=0).isoformat()

    def fake_latest_asset_rows(project_root_arg: Path, asset_name: str):
        if asset_name == "market_data_asset":
            return {
                "status": "materialized",
                "asset_name": asset_name,
                "asset_file": str(project_root_arg / ".tmp_dagster_home" / asset_name),
                "dagster_home": str(project_root_arg / ".tmp_dagster_home"),
                "rows": [
                    {"timestamp": "2026-04-19T00:00:00+00:00", "source": "OREE"},
                    {"timestamp": "2026-04-19T01:00:00+00:00", "source": "OREE"},
                ],
            }
        if asset_name == "optimization_schedule_asset":
            return {
                "status": "materialized",
                "asset_name": asset_name,
                "asset_file": str(project_root_arg / ".tmp_dagster_home" / asset_name),
                "dagster_home": str(project_root_arg / ".tmp_dagster_home"),
                "rows": [
                    {
                        "client_id": "tenant-alpha",
                        "forecast_run_id": "forecast-1",
                        "optimization_run_id": "opt-1",
                        "forecast_freshness_minutes": 15.0,
                        "purchase_cost_eur": 10.0,
                        "export_revenue_eur": 2.0,
                        "degradation_penalty_eur": 0.3,
                        "total_net_cost_eur": 8.3,
                    }
                ],
            }
        if asset_name == "multi_client_analytics":
            return {
                "status": "materialized",
                "asset_name": asset_name,
                "asset_file": str(project_root_arg / ".tmp_dagster_home" / asset_name),
                "dagster_home": str(project_root_arg / ".tmp_dagster_home"),
                "rows": [
                    {
                        "client_id": "tenant-alpha",
                        "storage_rank": 1,
                        "solar_rank": 1,
                        "analysis_timestamp": "2026-04-19T00:00:00+00:00",
                    }
                ],
            }
        return {
            "status": "not_materialized",
            "asset_name": asset_name,
            "asset_file": None,
            "dagster_home": None,
            "rows": [],
        }

    monkeypatch.setattr(medallion_catalog, "_latest_asset_rows", fake_latest_asset_rows)

    catalog = medallion_catalog.build_catalog_payload(manifest_path)

    assert catalog["runtime_entrypoint"] == "src/definitions.py"
    assert catalog["generated_at_utc"] == expected_generated_at
    assert len(catalog["layers"]) == 2
    assert catalog["layers"][0]["stats"]["materialized_count"] == 1
    assert catalog["fleet_view"]["status"] == "materialized_asset"
    assert catalog["case_study"]["client_id"] == "tenant-alpha"
    assert catalog["source_modes"]["market"]["provenance"] == "real"


def test_build_gold_summary_and_renderers(tmp_path: Path, monkeypatch) -> None:
    project_root = tmp_path / "repo"
    (project_root / "artifacts" / "medallion").mkdir(parents=True)
    (project_root / "data" / "results").mkdir(parents=True)
    (project_root / "customers.yaml").write_text(
        yaml.safe_dump(
            {
                "customers": [
                    {
                        "id": "tenant-alpha",
                        "name": "Alpha Site",
                        "type": "commercial",
                        "energy_system": {
                            "battery_capacity_kwh": 120.0,
                            "solar_capacity_kw": 60.0,
                            "peak_load_kw": 80.0,
                        },
                        "economic_params": {
                            "electricity_tariff": 0.12,
                            "feed_in_tariff": 0.08,
                        },
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (project_root / "data" / "results" / "ppo_validation_feb2026.json").write_text(
        json.dumps({"daily_savings": 123.4, "improvement_pct": 17.5, "days_analyzed": 7}),
        encoding="utf-8",
    )
    (project_root / "data" / "results" / "arbitrage_ranges.json").write_text(
        json.dumps({"price_statistics": {"median_daily_spread_eur": 44.2, "days_analyzed": 10}}),
        encoding="utf-8",
    )

    manifest_path = project_root / "artifacts" / "medallion" / "medallion_dataset_manifest.yaml"
    manifest_path.write_text(
        yaml.safe_dump(
            {
                "runtime_entrypoint": "src/definitions.py",
                "logical_overlay_only": True,
                "presentation_defaults": {"limitations": ["logical_overlay_not_storage_rewrite"]},
                "layers": {
                    "gold": {"narrative": "Gold layer", "storage_surface": "data/results"},
                },
                "datasets": [
                    {
                        "dataset_id": "optimization_schedule_asset",
                        "title": "Optimization Schedule",
                        "layer": "gold",
                        "dagster_asset": "optimization_schedule_asset",
                        "storage_path": "data/results",
                        "source_kind": "optimization_output",
                        "fallback_mode": "empty_schedule_when_forecast_missing",
                        "freshness_field": "forecast_freshness_minutes",
                        "quality_owner": "optimization_schedule_contract_checks",
                    }
                ],
                "experiments": {
                    "model_vs_model": {"supporting_outputs": ["data/results/arbitrage_ranges.json"]}
                },
            }
        ),
        encoding="utf-8",
    )

    def fake_latest_asset_rows(project_root_arg: Path, asset_name: str):
        rows_by_asset = {
            "market_data_asset": [{"timestamp": "2026-04-19T00:00:00+00:00", "source": "SYNTHETIC"}],
            "weather_asset": [{"timestamp": "2026-04-19T00:00:00+00:00", "source": "OPEN_METEO"}],
            "client_state_asset": [{"timestamp": "2026-04-19T00:00:00+00:00", "state_source": "simulator_backed_telemetry"}],
            "forecast_value_benchmark_asset": [
                {
                    "model_name": "rf_v1",
                    "model_family": "random_forest",
                    "benchmark_rmse": 5.1,
                    "benchmark_mae": 4.0,
                    "benchmark_value_capture_ratio": 0.91,
                    "benchmark_conservative_value_capture_ratio": 0.83,
                    "promotion_decision": "promote",
                }
            ],
            "price_forecast_asset": [
                {
                    "forecast_timestamp": "2026-04-19T00:00:00+00:00",
                    "forecast_run_id": "forecast-1",
                    "forecast_model_version": "v1",
                }
            ],
            "optimization_schedule_asset": [
                {
                    "client_id": "tenant-alpha",
                    "forecast_run_id": "forecast-1",
                    "optimization_run_id": "opt-dp",
                    "purchase_cost_eur": 10.0,
                    "export_revenue_eur": 1.5,
                    "degradation_penalty_eur": 0.2,
                    "total_net_cost_eur": 8.7,
                }
            ],
            "optimization_schedule_milp_asset": [
                {
                    "client_id": "tenant-alpha",
                    "forecast_run_id": "forecast-1",
                    "optimization_run_id": "opt-milp",
                    "purchase_cost_eur": 9.5,
                    "export_revenue_eur": 1.7,
                    "degradation_penalty_eur": 0.25,
                    "total_net_cost_eur": 8.05,
                }
            ],
        }
        return {
            "status": "materialized" if asset_name in rows_by_asset else "not_materialized",
            "asset_name": asset_name,
            "asset_file": str(project_root_arg / ".tmp_dagster_home" / asset_name) if asset_name in rows_by_asset else None,
            "dagster_home": str(project_root_arg / ".tmp_dagster_home") if asset_name in rows_by_asset else None,
            "rows": rows_by_asset.get(asset_name, []),
        }

    monkeypatch.setattr(medallion_catalog, "_latest_asset_rows", fake_latest_asset_rows)

    summary = medallion_catalog.build_gold_summary(manifest_path)
    catalog = medallion_catalog.build_catalog_payload(manifest_path)
    catalog_markdown = medallion_catalog.render_catalog_markdown(catalog)
    experiments_markdown = medallion_catalog.render_experiments_markdown(catalog, summary)
    preview_markdown = medallion_catalog.render_preview_markdown(catalog, summary)
    json_render = medallion_catalog.render_output(
        manifest_path,
        output_format="json",
        output_path=project_root / "artifacts" / "medallion" / "gold_experiment_summary.json",
    )

    assert summary["model_vs_model"]["candidate_count"] == 1
    assert summary["optimizer_vs_optimizer"]["status"] == "comparable"
    assert summary["business_metrics"]["ppo_validation"]["daily_savings"] == 123.4
    assert "# Bronze/Silver/Gold Dataset Catalog" in catalog_markdown
    assert "# Experiments And Results Scorecard" in experiments_markdown
    assert "## Reuse And Regeneration" in experiments_markdown
    assert "| Surface | Status | Rows | Latest Timestamp | Run Identifiers | Notes |" in experiments_markdown
    assert "| Metric | Status | Value | Units | System Of Record |" in experiments_markdown
    assert "# Medallion Preview" in preview_markdown
    assert '"daily_savings": 123.4' in json_render