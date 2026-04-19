# API Reference

This document is the supervisor-facing reference for the active dashboard and backend API surface exposed from `dashboard/server/api/`.

It documents the current runtime as it exists today:

- Preferred application surfaces are the tenant-aware route groups under `/api/config`, `/api/control`, `/api/dagster`, `/api/ml`, `/api/optimization`, `/api/settings`, and the supporting operational groups such as `/api/battery`, `/api/prices`, and `/api/renewable`.
- Root rollups such as `/api/battery`, `/api/prices`, and `/api/metrics` remain part of the current runtime and are documented here as compatibility or dashboard-facing summary surfaces rather than new backend design targets.
- Detailed settings import and export examples remain in [API_DOCUMENTATION_IMPORT_EXPORT.md](API_DOCUMENTATION_IMPORT_EXPORT.md); this reference keeps that subset linked instead of duplicating the full examples.

## Integration Rules

### Base and tenant resolution

- Base path: `/api`
- Preferred tenant selector: `x-tenant-id` request header
- Common alternate selectors: `tenantId` query parameter and `tenantId` request-body field
- Current tenant resolution is handled inside the dashboard server utilities and many route groups normalize tenant context before delegating to Python or Dagster-owned logic.

### Handler-style note

- `GET`, `POST`, and `DELETE` below come directly from Nitro method-specific file names such as `*.get.ts`, `*.post.ts`, and `*.delete.ts`.
- `GENERIC` means the route is implemented in a plain `*.ts` handler. Some of these are read-style GET endpoints, while others branch on request method or act as command-style endpoints.

### Backend ownership anchors

- Canonical Python ML bridge owner: `src/data_pipeline/ml_bridge_service.py`
- Thin compatibility CLI wrapper: `scripts/ml_integration_api.py`
- Thin root compatibility wrapper: `ml_integration_api.py`
- Canonical Dagster code location: `src/definitions.py`

### Recommendation authority rule

- `/api/dagster/recommendation` is the current default operational recommendation authority for dashboard decisioning, auto-mode execution, and schedule-backed UI flows.
- `/api/ml/recommendation` is the live-context Python bridge surface used for fallback, transparency, and ML-specific enrichment fields.
- Some UI slices still call `/api/ml/recommendation` directly because it exposes payload families such as `savings_estimate`, `battery_impact`, `feature_provenance`, and `inference_lineage` that are not yet surfaced in the Dagster route.
- Do not introduce a third recommendation authority endpoint. If a neutral alias is ever needed later, it should resolve to the Dagster-backed route rather than creating another source of truth.

## Route Inventory

| Group         | Method       | Route                                         | Purpose                                                                | Notes                                                                                                 |
| ------------- | ------------ | ------------------------------------------------------------------ | ---------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| Platform      | `GET`      | `/api/health`                                                    | Lightweight dashboard readiness probe.                                 | Preferred health endpoint for local startup checks.                                                   |
| Platform      | `GET`      | `/api/tenants`                                                   | Enumerate known tenants for dashboard selection.                       | Derived from current tenant configuration surfaces.                                                   |
| Config        | `GET`      | `/api/config/current`                                            | Load the current effective tenant configuration.                       | Preferred read path for config-aware dashboard pages.                                                 |
| Config        | `POST`     | `/api/config/save`                                               | Persist updated tenant configuration.                                  | Save-side logic can trigger recalculation when significant changes are detected.                      |
| Config        | `GET`      | `/api/config/templates`                                          | Return available configuration templates or presets.                   | Used by settings flows and onboarding helpers.                                                        |
| Settings      | `GENERIC`  | `/api/settings/load`                                             | Load persisted settings payloads.                                      | Older settings surface still used by parts of the dashboard.                                          |
| Settings      | `GENERIC`  | `/api/settings/save`                                             | Persist settings payloads.                                             | Compatibility-facing settings save surface.                                                           |
| Settings      | `GENERIC`  | `/api/settings/import`                                           | Import settings bundle.                                                | See[API_DOCUMENTATION_IMPORT_EXPORT.md](API_DOCUMENTATION_IMPORT_EXPORT.md).                             |
| Settings      | `GENERIC`  | `/api/settings/export`                                           | Export settings bundle.                                                | See[API_DOCUMENTATION_IMPORT_EXPORT.md](API_DOCUMENTATION_IMPORT_EXPORT.md).                             |
| Settings      | `POST`     | `/api/settings/battery`                                          | Update tenant battery settings.                                        | Specialized settings mutation endpoint.                                                               |
| Settings      | `POST`     | `/api/settings/load-profile`                                     | Update tenant load-profile settings.                                   | Specialized settings mutation endpoint.                                                               |
| Dagster       | `GET`      | `/api/dagster/assets`                                            | Expose Dagster asset status and recent materialization state.          | Dashboard observability surface over `src/definitions.py`.                                          |
| Dagster       | `GET`      | `/api/dagster/recommendation`                                    | Return the active recommendation with freshness and fallback metadata. | Enforces a 15-minute snapshot freshness gate before using Dagster snapshots directly.                 |
| Dagster       | `GET`      | `/api/dagster/schedule-24h`                                      | Return the active 24-hour optimization schedule snapshot.              | Primary schedule consumption path for the dashboard.                                                  |
| Dagster       | `POST`     | `/api/dagster/trigger`                                           | Trigger Dagster materialization or refresh flows.                      | Operational control surface, not the default user-facing path.                                        |
| ML            | `GET`      | `/api/ml/recommendation`                                         | Return a live-context ML recommendation for the selected tenant.       | Includes lineage and model-input metadata when available.                                             |
| ML            | `GET`      | `/api/ml/pipeline-health`                                        | Report Python pipeline, component, and dependency health.              | Used to expose degradation rather than only hard-failure state.                                       |
| ML            | `POST`     | `/api/ml/recalculate`                                            | Request a recalculation or refresh of ML outputs.                      | Command-style route.                                                                                  |
| ML            | `GET`      | `/api/ml/recalculate-status`                                     | Report recalculation progress or staleness.                            | Companion status surface for recalculation workflows.                                                 |
| ML            | `GENERIC`  | `/api/ml/predict`                                                | Compatibility prediction bridge into the Python ML runtime.            | Legacy-facing bridge surface backed by the root Python wrapper.                                       |
| ML            | `GENERIC`  | `/api/ml/monitoring`                                             | Return ML monitoring and drift diagnostics when available.             | Read-style operational surface.                                                                       |
| Optimization  | `GET`      | `/api/optimization/strategy`                                     | Read the active optimization strategy.                                 | Strategy values are tenant-aware.                                                                     |
| Optimization  | `POST`     | `/api/optimization/strategy`                                     | Update the active optimization strategy.                               | Configuration mutation surface.                                                                       |
| Control       | `POST`     | `/api/control/execute`                                           | Execute an immediate control command.                                  | Used by simulator-backed manual control flows.                                                        |
| Control       | `GET`      | `/api/control/history`                                           | Read recent control command history.                                   | Observability and troubleshooting surface.                                                            |
| Control       | `GET`      | `/api/control/physics`                                           | Read control or battery physics metadata used by the control UI.       | Read-style helper surface.                                                                            |
| Control       | `GET`      | `/api/control/status`                                            | Read the current control state.                                        | Key source for command provenance in the battery UI.                                                  |
| Control       | `POST`     | `/api/control/schedule`                                          | Create a scheduled control command.                                    | Scheduling mutation surface.                                                                          |
| Control       | `GET`      | `/api/control/scheduled`                                         | List scheduled control commands.                                       | Companion read path for scheduled commands.                                                           |
| Control       | `DELETE`   | `/api/control/schedule/:id`                                      | Delete a scheduled control command.                                    | Route file `control/schedule/[id].delete.ts`.                                                       |
| Battery       | `GET/POST` | `/api/battery/simulate`                                          | Read or mutate the simulator-backed battery state.                     | The current handler branches on method and powers the interactive battery UI.                         |
| Battery       | `GET`      | `/api/battery/status`                                            | Return current battery status.                                         | Read-style battery snapshot endpoint.                                                                 |
| Physics       | `GET`      | `/api/physics/battery`                                           | Return battery physics characteristics and derived limits.             | Physics reference surface separate from the simulator state.                                          |
| Billing       | `GET`      | `/api/billing/draft`                                             | Produce a draft billing or settlement view.                            | Tenant-aware financial helper.                                                                        |
| Prices        | `GENERIC`  | `/api/prices/current`                                            | Return the current price view used by dashboard and ML flows.          | Read-style route that can bridge to OREE-backed data.                                                 |
| Renewable     | `GENERIC`  | `/api/renewable/forecast`                                        | Return the general renewable forecast surface used by the dashboard.   | Preferred dashboard contract.                                                                         |
| Renewable     | `GET`      | `/api/renewable/ml-forecast`                                     | Return the ML-backed renewable forecast lane.                          | Separate from the general forecast surface so GET precedence stays explicit.                          |
| Metrics       | `GET`      | `/api/metrics/dashboard`                                         | Return dashboard summary metrics.                                      | Main metrics route for the dashboard.                                                                 |
| History       | `GENERIC`  | `/api/history`                                                   | Return financial and operational history.                              | Canonical dashboard financial telemetry surface.                                                      |
| MLflow        | `GENERIC`  | `/api/mlflow/status`                                             | Return MLflow connectivity and availability status.                    | Should degrade with `success: true` and `mlflow_connected: false` when MLflow is offline locally. |
| MLflow        | `GENERIC`  | `/api/mlflow/log-metrics`                                        | Log metrics into MLflow from dashboard-triggered flows.                | Command or integration surface.                                                                       |
| Retraining    | `GENERIC`  | `/api/retraining/start`                                          | Start a retraining workflow.                                           | Command surface.                                                                                      |
| Retraining    | `GENERIC`  | `/api/retraining/progress`                                       | Read retraining progress.                                              | Read-style companion surface.                                                                         |
| Retraining    | `GENERIC`  | `/api/retraining/cancel`                                         | Cancel an active retraining workflow.                                  | Command surface.                                                                                      |
| Compatibility | `GENERIC`  | `/api/battery`                                                   | Dashboard-facing battery rollup.                                       | Keep documented as a compatibility summary surface.                                                   |
| Compatibility | `GENERIC`  | `/api/prices`                                                    | Dashboard-facing prices rollup.                                        | Keep documented as a compatibility summary surface.                                                   |
| Compatibility | `GENERIC`  | `/api/metrics`                                                   | Dashboard-facing metrics rollup.                                       | Keep documented as a compatibility summary surface.                                                   |

## Key Runtime Contracts

### `GET /api/dagster/recommendation`

Primary purpose:
Return the current optimization recommendation and its provenance to the dashboard.

Important contract notes:

- Treats Dagster snapshots as fresh only when the latest snapshot age is less than or equal to 15 minutes.
- Falls back to deterministic ML or simulation-backed logic when the Dagster snapshot is stale or unavailable.
- Current payload families include recommendation content, `strategy_context`, and `source_metadata` describing freshness, fallback path, and snapshot origin.

### `GET /api/dagster/schedule-24h`

Primary purpose:
Expose the active 24-hour optimization schedule for charts, tables, and export flows.

Important contract notes:

- Schedule rows are aligned to the Gold optimization schedule assets owned by Dagster.
- Consumers should expect lineage-bearing fields such as `forecast_run_id`, `optimization_run_id`, algorithm metadata, and schedule economics.
- The schedule is the preferred dashboard source of truth for optimizer output when present.

### `GET /api/ml/recommendation`

Primary purpose:
Serve a live-context recommendation from the Python ML bridge.

Important contract notes:

- The bridge is backed by `src/data_pipeline/ml_bridge_service.py` and compatibility wrappers rather than by ad hoc dashboard logic.
- Current payloads can include `feature_provenance`, `model_inputs`, `inference_lineage`, and drift or monitoring details when the Python runtime exposes them.
- This route is used as a fallback and as a transparency or enrichment surface when comparing ML output to Dagster-driven recommendation flows.
- It is not the default execution-authority endpoint for auto-mode or schedule-backed recommendation flows.

### `POST /api/control/execute`

Primary purpose:
Execute a manual or automatic control command against the current tenant context.

Important contract notes:

- Common command fields include tenant identifier, command name, requested power, reason, and user identifier.
- The response surface carries resolved command information, decision source, and source metadata so the UI can show why the command path was selected.

### `POST /api/control/schedule` and `DELETE /api/control/schedule/:id`

Primary purpose:
Create and remove scheduled control commands.

Important contract notes:

- These routes are the dashboard scheduling surface rather than the optimizer schedule output.
- They complement `GET /api/control/scheduled` for displaying queued command plans.

### `GET /api/config/current` and `POST /api/config/save`

Primary purpose:
Load and persist tenant configuration used by simulation, ML, and optimization paths.

Important contract notes:

- This pair is the preferred configuration read and write surface for the current dashboard application.
- They coexist with the broader `/api/settings/*` family, which remains important for import, export, and compatibility flows.

### `GENERIC /api/history`

Primary purpose:
Expose financial and operational history to dashboard analytics.

Important contract notes:

- This is the canonical dashboard telemetry surface for history and economics.
- Downstream analytics pages should derive saved-funds, earned-funds, and regime-aware summaries from this route rather than adding a competing history endpoint.

### `GENERIC /api/mlflow/status`

Primary purpose:
Report MLflow availability without making local dashboard readiness brittle.

Important contract notes:

- Local offline MLflow is an expected degraded mode.
- The route should report success with an explicit disconnected flag rather than turning the dashboard unhealthy when MLflow is unavailable locally.

## Representative Payload Examples

These examples are representative request and response shapes derived from the current route handlers. They are intentionally compact: they show the fields a client should expect to anchor on, not every optional field that may appear in a full runtime payload.

### `GET /api/config/current`

Example request:

```http
GET /api/config/current?tenantId=client_001_kyiv_mall HTTP/1.1
Host: localhost:3600
x-tenant-id: client_001_kyiv_mall
Accept: application/json
```

Representative response:

```json
{
	"success": true,
	"tenant": {
		"id": "client_001_kyiv_mall",
		"name": "Kyiv Shopping Mall"
	},
	"data": {
		"battery_type": "LFP",
		"battery_capacity_kwh": 280,
		"load_profile_type": "standard",
		"optimization_strategy": "balanced",
		"has_solar": true,
		"solar_capacity_kw": 150,
		"market_regime_override": "auto"
	},
	"metadata": {
		"config_scope": "tenant",
		"config_file_exists": true,
		"last_modified": "2026-04-19T00:11:32.000Z",
		"battery_specs": {
			"full_name": "Lithium Iron Phosphate",
			"expected_cycles": 8000,
			"efficiency_typical": 0.95
		},
		"arbitrage_metrics": {
			"daily_profit_net_uah": 975.41,
			"annual_profit_uah": 356024,
			"usable_capacity_kwh": 252,
			"price_spread_uah": 4.5
		}
	},
	"timestamp": "2026-04-19T01:15:00.000Z"
}
```

### `POST /api/config/save`

Example request:

```http
POST /api/config/save HTTP/1.1
Host: localhost:3600
Content-Type: application/json
x-tenant-id: client_001_kyiv_mall

{
	"tenantId": "client_001_kyiv_mall",
	"battery_capacity_kwh": 280,
	"load_profile_type": "multi-shift",
	"optimization_strategy": "balanced",
	"has_solar": true,
	"solar_capacity_kw": 150,
	"market_regime_override": "auto"
}
```

Representative response:

```json
{
	"success": true,
	"tenant": {
		"id": "client_001_kyiv_mall",
		"name": "Kyiv Shopping Mall"
	},
	"data": {
		"battery_capacity_kwh": 280,
		"load_profile_type": "multi-shift",
		"optimization_strategy": "balanced",
		"has_solar": true,
		"solar_capacity_kw": 150,
		"last_updated": "2026-04-19T01:16:05.000Z",
		"version": "1.0"
	},
	"validation": {
		"errors": [],
		"warnings": []
	},
	"recalculation": {
		"triggered": true,
		"result": {
			"status": "queued"
		}
	},
	"message": "Configuration saved successfully"
}
```

### `GET /api/dagster/recommendation`

Example request:

```http
GET /api/dagster/recommendation?tenantId=client_001_kyiv_mall HTTP/1.1
Host: localhost:3600
x-tenant-id: client_001_kyiv_mall
Accept: application/json
```

Representative response:

```json
{
	"status": "success",
	"timestamp": "2026-04-19T01:18:00.000Z",
	"tenant": {
		"id": "client_001_kyiv_mall",
		"name": "Kyiv Shopping Mall"
	},
	"recommendation": {
		"action": "SELL",
		"action_kw": 12.5,
		"confidence": 0.84,
		"confidence_percent": 84,
		"rationale": "High-price window detected and reserve floor remains safe.",
		"normalized_action": {
			"action": "SELL",
			"power_kw": 12.5,
			"strategy_adjusted": false
		},
		"policy_compliance": {
			"veto_applied": false,
			"market_regime": "market_premium"
		}
	},
	"current_state": {
		"price_uah_kwh": 10.8,
		"battery_soc_percent": 62,
		"time": "01:18:00"
	},
	"schedule_24h": {
		"schedule": [
			{
				"hour": 0,
				"hour_offset": 0,
				"recommended_action": "SELL",
				"expected_profit_uah": 123.4,
				"forecast_run_id": "forecast-bcfa3fbe846fa963",
				"optimization_run_id": "optimization-a27f8e52"
			}
		]
	},
	"strategy_context": {
		"optimization_strategy": "balanced",
		"load_profile_type": "standard"
	},
	"source_metadata": {
		"recommendation_source": "dagster",
		"dagster_snapshot_is_fresh": true,
		"dagster_snapshot_age_minutes": 4.1,
		"dagster_snapshot_max_age_minutes": 15,
		"dagster_forecast_run_id": "forecast-bcfa3fbe846fa963",
		"dagster_optimization_run_id": "optimization-a27f8e52",
		"fallback_used": false
	}
}
```

### `GET /api/dagster/schedule-24h`

Example request:

```http
GET /api/dagster/schedule-24h?tenantId=client_001_kyiv_mall HTTP/1.1
Host: localhost:3600
x-tenant-id: client_001_kyiv_mall
Accept: application/json
```

Representative response:

```json
{
	"status": "success",
	"timestamp": "2026-04-19T01:19:00.000Z",
	"tenant": {
		"id": "client_001_kyiv_mall",
		"name": "Kyiv Shopping Mall"
	},
	"registry_diagnostics": {
		"available": false,
		"service_role": "registry_and_experiment_diagnostics",
		"latest_run_name": null,
		"recent_runs_count": 0,
		"authoritative_for_runtime_serving": false
	},
	"schedule": [
		{
			"hour": 0,
			"hour_offset": 0,
			"time": "2026-04-19T00:00:00+00:00",
			"recommended_action": "SELL",
			"expected_profit_uah": 123.4
		}
	],
	"summary": {
		"total_expected_profit": 7902.38,
		"average_hourly_profit": 329.27,
		"buy_hours": 6,
		"sell_hours": 8,
		"discharge_hours": 0,
		"hold_hours": 10
	},
	"source_metadata": {
		"tenant_filter_applied": true,
		"mlflow_registry_diagnostics_available": false
	}
}
```

### `GET /api/ml/recommendation`

Example request:

```http
GET /api/ml/recommendation?tenantId=client_001_kyiv_mall HTTP/1.1
Host: localhost:3600
x-tenant-id: client_001_kyiv_mall
Accept: application/json
```

Representative response:

```json
{
	"success": true,
	"contract": {
		"version": "learned_policy_migration_v1",
		"normalized_action": {
			"action": "BUY",
			"power_kw": 8
		},
		"strategy_context": {
			"optimization_strategy": "balanced",
			"load_profile_type": "standard"
		}
	},
	"serving": {
		"requested_mode": "incumbent",
		"active_mode": "incumbent",
		"adapter": "PredictionService",
		"fallback_used": false,
		"fallback_reason_code": "none"
	},
	"data": {
		"action": "BUY",
		"confidence": 0.79,
		"reasoning": "Current tariff window favors charge accumulation before the evening peak.",
		"daily_forecast": [
			{
				"hour": 0,
				"action": "BUY",
				"price_uah_mwh": 10800,
				"reasoning": "Off-peak charge window"
			}
		],
		"savings_estimate": {
			"daily_uah": 512.4,
			"monthly_uah": 15372,
			"annual_uah": 186694
		},
		"battery_impact": {
			"current_soc": 62,
			"health_impact": 0.0003,
			"cycles_remaining": 5000
		},
		"model_info": {
			"version": "Phase4F-v1.0",
			"confidence_level": "Medium",
			"serving_mode": "incumbent",
			"requested_serving_mode": "incumbent",
			"serving_adapter": "PredictionService",
			"resolved_model_uri": null
		},
		"feature_provenance": {
			"config_source": "tenant_config",
			"price_source": "prices_current_api",
			"weather_source": "open-meteo",
			"battery_source": "simulator",
			"tenant_id": "client_001_kyiv_mall"
		},
		"inference_lineage": {
			"tenant_id": "client_001_kyiv_mall",
			"training_reference": {
				"mlflow_connected": false,
				"source": "runtime_incumbent_or_registry_diagnostics"
			},
			"serving_reference": {
				"requested_mode": "incumbent",
				"active_mode": "incumbent",
				"fallback_used": false
			}
		}
	}
}
```

### `POST /api/control/execute`

Example request:

```http
POST /api/control/execute HTTP/1.1
Host: localhost:3600
Content-Type: application/json
x-tenant-id: client_001_kyiv_mall

{
	"tenantId": "client_001_kyiv_mall",
	"command": "charge",
	"power_kw": 5,
	"reason": "Supervisor demo manual charge command",
	"user_id": "dashboard_demo"
}
```

Representative response:

```json
{
	"success": true,
	"tenant": {
		"id": "client_001_kyiv_mall",
		"name": "Kyiv Shopping Mall"
	},
	"command_id": "cmd_20260419T011930Z_client_001_kyiv_mall",
	"requested_command": "charge",
	"resolved_command": "charge",
	"decision_source": "manual",
	"executed_at": "2026-04-19T01:19:30.000Z",
	"source": "simulation",
	"source_metadata": {
		"tenant_filter_applied": true,
		"fallback_reason_code": "python_script_missing",
		"execution_status": "executed",
		"optimization_history_reconciled": false
	},
	"decision_snapshot": {
		"version": "control_execution_v1"
	}
}
```

### `GET /api/battery/simulate` and `POST /api/battery/simulate`

Example read request:

```http
GET /api/battery/simulate?tenantId=client_001_kyiv_mall HTTP/1.1
Host: localhost:3600
x-tenant-id: client_001_kyiv_mall
Accept: application/json
```

Representative read response:

```json
{
	"success": true,
	"tenant": {
		"id": "client_001_kyiv_mall",
		"name": "Kyiv Shopping Mall"
	},
	"battery": {
		"soc": 0.62,
		"socPercentage": 62,
		"power": 0,
		"commandedPower": 0,
		"voltage": 400,
		"current": 0,
		"health": 98.5,
		"capacity": 280,
		"optimization_strategy": "balanced",
		"manualMode": false,
		"autoOptimization": true,
		"execution_mode": "auto_recommendation",
		"active_command": "hold",
		"decision_source": "dagster",
		"source": "control_status_backed_simulator",
		"lastUpdated": "2026-04-19T01:20:00.000Z"
	},
	"specs": {
		"typeName": "Lithium Iron Phosphate",
		"efficiency": 0.95,
		"roundTripEfficiency": 0.9025,
		"nominalVoltage": 400
	},
	"source_metadata": {
		"tenant_filter_applied": true,
		"control_status_source": "control_execute",
		"renewable_model_source": "local_deterministic_estimate"
	}
}
```

Example write request:

```http
POST /api/battery/simulate HTTP/1.1
Host: localhost:3600
Content-Type: application/json
x-tenant-id: client_001_kyiv_mall

{
	"tenantId": "client_001_kyiv_mall",
	"action": "setPower",
	"power": 4,
	"reason": "Supervisor demo charge step"
}
```

Representative write response:

```json
{
	"success": true,
	"tenant": {
		"id": "client_001_kyiv_mall",
		"name": "Kyiv Shopping Mall"
	},
	"message": "Power set to 4kW",
	"powerCommand": 4,
	"requested_command": "charge",
	"resolved_command": "charge",
	"decision_source": "manual",
	"execution_mode": "manual_command",
	"source": "control_execute",
	"source_metadata": {
		"tenant_filter_applied": true
	}
}
```

## Python Bridge Mapping

The dashboard API does not own forecasting or recommendation logic by itself. The canonical Python bridge service in `src/data_pipeline/ml_bridge_service.py` currently anchors these actions:

- `get_recommendation`
- `get_forecast`
- `get_pipeline_status`
- `get_optimization_strategy`
- `set_optimization_strategy`
- `get_battery_physics`
- `get_renewable_forecast`

Those bridge functions are exposed to the dashboard through the thin wrappers in `scripts/ml_integration_api.py` and `ml_integration_api.py`, and then consumed by the relevant `/api/ml/*`, `/api/optimization/*`, `/api/physics/*`, and renewable endpoints.

## Preferred Integration Guidance

- Prefer the Dagster-backed recommendation and schedule surfaces for optimizer-facing UI views.
- Keep `/api/dagster/recommendation` as the operational recommendation default, and treat `/api/ml/recommendation` as the live bridge, fallback, and ML-explainability surface until the Dagster route exposes the same enrichment payloads.
- Prefer `x-tenant-id` over ad hoc query-only tenant selection when designing new clients.
- Treat root rollups such as `/api/battery`, `/api/prices`, and `/api/metrics` as existing compatibility surfaces rather than as the target shape for future backend organization.
- Reuse [API_DOCUMENTATION_IMPORT_EXPORT.md](API_DOCUMENTATION_IMPORT_EXPORT.md) for the detailed settings import and export flow instead of copying its examples into new docs.
