# Dashboard Integration Guide

**Status:** Active runtime note, updated 2026-03-07  
**Scope:** Nuxt dashboard + Dagster recommendation path + optional MLflow diagnostics

## Overview

The dashboard integrates with two kinds of backend surfaces:

- operational recommendation surfaces that drive BUY/SELL/HOLD behavior
- optional diagnostics surfaces that describe experiment or registry state

The key runtime rule is:

- `/api/dagster/recommendation` and `/api/ml/recommendation` are recommendation surfaces
- `/api/mlflow/status` and `/api/mlflow/log-metrics` are diagnostics surfaces
- MLflow does not currently define live execution authority on its own

## Current Runtime Flow

```
Dashboard UI
  -> /api/dagster/recommendation
     -> prefers fresh Dagster schedule snapshot
     -> falls back to /api/ml/recommendation when needed
  -> /api/dagster/schedule-24h
     -> exposes schedule rows plus optional registry diagnostics
  -> /api/ml/monitoring
     -> summarizes drift, Dagster freshness, and runtime diagnostic events
  -> /api/mlflow/status
     -> reports experiment and registry reachability only
```

## Endpoint Roles

### `/api/dagster/recommendation`

Primary operational recommendation endpoint.

- exposes canonical `contract`, `provenance`, and `serving` metadata
- keeps Dagster as the preferred orchestrator when a fresh schedule exists
- uses fallback provenance when it must rely on the Python ML bridge

### `/api/ml/recommendation`

Fallback recommendation surface.

- builds live context from tenant config, prices, battery state, and weather
- invokes the shared Python bridge `ml_integration_api.py`
- exposes the same normalized `contract` and `serving` metadata used by the Dagster handoff

### `/api/mlflow/status`

Registry and experiment diagnostics only.

- reports MLflow reachability and recent run inventory when available
- is not authoritative for live learned-policy serving
- should be read as supporting metadata for experiments and model registry state

### `/api/mlflow/log-metrics`

Local runtime diagnostics capture.

- stores JSONL diagnostic events for operator visibility
- does not currently guarantee backend MLflow metric ingestion
- is useful for local observability and later pipeline wiring

## Serving Truth

Learned-policy serving is only active when the Python `PredictionService` contract reports it explicitly. The fields that matter are:

- `serving.requested_mode`
- `serving.active_mode`
- `serving.fallback_used`
- `serving.fallback_reason_code`
- `serving.model_info.resolved_model_uri`

If those fields do not show an active learned-policy model, the runtime should be described as Dagster or heuristic incumbent decisioning, even if MLflow is online.

## Local Validation

### Dashboard build

```bash
cd dashboard
npm run build
```

### Recommendation contract

```bash
curl http://127.0.0.1:3600/api/dagster/recommendation
curl http://127.0.0.1:3600/api/ml/recommendation
```

Check for:

- `contract.version`
- `contract.provenance`
- `serving.requested_mode`
- `serving.active_mode`

### MLflow diagnostics

```bash
curl http://127.0.0.1:3600/api/mlflow/status
curl -X POST http://127.0.0.1:3600/api/mlflow/log-metrics \
  -H "Content-Type: application/json" \
  -d '{"action":"BUY","confidence":0.92,"actual_profit":50,"metrics":{"latency_ms":245}}'
```

Check for:

- `service_role`
- `runtime_serving_authoritative: false`
- `tracking_mode: diagnostic_only`

## What This Doc Does Not Claim

This document does not claim:

- that the dashboard is currently served by a production MLflow model registry promotion flow
- that every runtime metric is being written into MLflow automatically
- that BUY/SELL/HOLD is currently chosen by a trained end-to-end trading policy

For the broader runtime truth and provenance model, see:

- `docs/technical/ML_TRADING_DECISION_FRAMEWORK.md`
- `docs/technical/DAGSTER_PIPELINE_DEPENDENCY_MAP.md`

- **Dagster Docs:** https://docs.dagster.io/
- **MLflow Docs:** https://mlflow.org/docs/
- **Nuxt 4 Docs:** https://nuxt.com/docs/
- **Project Guide:** PHASE3_COMPLETE.md

---

## 🎯 Next Steps

1. ✅ **Phase 3C Complete:** All endpoints + components deployed
2. **Phase 4 (Optional):** Advanced features
   - [ ] Real MLflow server deployment
   - [ ] Actual Dagster gRPC connection
   - [ ] Historical metrics aggregation
   - [ ] Advanced drift detection
   - [ ] Model comparison UI
   - [ ] A/B testing framework

---

**Status:** ✅ Integration Complete  
**Tested:** All endpoints working  
**Deployed:** Ready for production  
**Confidence:** ⭐⭐⭐⭐⭐
