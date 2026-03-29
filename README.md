# Smart Energy AI: Autonomous Arbitrage System (UA Market 2026)

## 1. System Overview
**Smart Energy AI** is a data orchestration and decision-making system for energy arbitrage on Ukraine's Day-Ahead Market (DAM) and Intraday Market (IDM).

The system is built on the **Software-Defined Assets (SDA)** principle using Dagster. It solves the multi-objective optimization problem: maximizing profit from buying/selling electricity while accounting for physical degradation of Lithium-Ion (LFP) batteries.

Current Dagster dependency and job map:
- `docs/technical/DAGSTER_PIPELINE_DEPENDENCY_MAP.md`

Current trading decision and data provenance note:
- `docs/technical/ML_TRADING_DECISION_FRAMEWORK.md`

### Key Thesis Benchmark
The system implements **Dual-Engine Architecture** for Feature Engineering, allowing dynamic switching between:
1. **CPU-Optimized:** Rust-based Polars (for AWS Free Tier / Edge Devices)
2. **GPU-Accelerated:** NVIDIA NVTabular (for High-Performance Training on large datasets)

---

## 2. Software-Defined Assets Architecture (DAG)

The active runtime uses Dagster for market, weather, forecasting, and scheduling, with the dashboard adding a simulator-backed battery and control loop plus a Python recommendation fallback.

### Level 1: Ingestion (Sourcing)
* **`market_data_asset`**: Pull market price history and recent price signals for optimization
* **`weather_asset`**: Pull Open-Meteo weather inputs and solar-relevant forecast features
* **`client_state_asset`**: Reuse simulator-backed tenant battery state when available, while keeping config plus market and weather inputs for load and solar estimation

### Parallel dashboard telemetry loop
* **Battery state**: The dashboard persists tenant battery state and exposes it through the battery APIs
* **Control state**: Command history and control mode are derived from the persisted tenant loop when direct control services are unavailable
* **Simulation**: Battery state evolves through simulator-backed updates and command writeback, which makes it operationally live inside the app while still simulated telemetry

### Level 2: Processing (Feature Engineering)
* **`feature_matrix`**: Hybrid asset
  - **Inputs:** Raw time series
  - **Logic:** Generate lags, rolling means, calendar features
  - **Engine:** Selected via config (`execution_mode: "polars" | "nvtabular"`)

### Level 3: Intelligence (Decision)
* **`price_forecast_asset`**: RandomForest-based 24-hour price forecast trained from market history
* **`optimization_schedule_asset`** and **`optimization_schedule_milp_asset`**: Compute charge and discharge schedules from forecast prices and synthesized client state
* **Dashboard fallback path**: `dashboard/server/api/ml/recommendation.get.ts` calls `ml_integration_api.py`, which applies heuristic decision logic, optimization scoring, renewable inference, and a live-price override
  - **Current truth:** the live BUY, SELL, or HOLD result is produced by schedule normalization or heuristics, not by a trained end-to-end trading policy

---

## 3. Economic and Physical Model

The system doesn't just "trade", it manages an active asset (battery).

### 3.1. Degradation Cost (Marginal Cost of Degradation)
The cost of each cycle is calculated dynamically:

$$MC_{deg} = \frac{C_{batt\_pack}}{Total\_Throughput \cdot \eta_{roundtrip}} \cdot f(SoC, Temp, C\_rate)$$

Where:
* $C_{batt\_pack}$: Capital expenditure on battery ($/kWh)
* $f(SoC, Temp)$: Stress Factor. For LFP it increases sharply at $SoC > 90\%$ and $Temp > 35°C$

### 3.2. SEI (Solid Electrolyte Interphase) Modeling
We use the approximated model of SEI film growth to determine the "Knee Point" (sharp capacity drop after 80% SoH):

$$Q_{loss}(t) = A \cdot e^{-\frac{E_a}{RT}} \cdot t^{0.5}$$

The active schedule and heuristic decision layers should account for degradation risk when proposing charge and discharge behavior, even though the current runtime path is not driven by an Optuna study.

---

## 4. Hybrid Deployment (AWS Free Tier Strategy)

Architecture optimized for Free Tier constraints:

| Component | AWS Service | Usage Limits | Role |
|-----------|-------------|--------------|------|
| **Manager** | EC2 `t3.micro` | 750 hours/month | Dagster Webserver, Daemon, Postgres (Metadata) |
| **Compute** | AWS Lambda | 400k GB-seconds | Execute heavier batch or experimental jobs when local runtime is insufficient |
| **Storage** | S3 Standard | 5 GB | Store Pickle files (I/O Manager) and logs |
| **Edge** | Local / Simulator | N/A | Simulator-backed telemetry loop, local dashboard runtime, local GPU benchmarks |

**Lambda 15-min limit workaround:**
Instead of processing a year of data at once, Dagster splits the task into 365 Lambda invocations (per day/week), storing intermediate results in S3.

EC2 service bootstrap and operations runbook:
- `docs/deployment/EC2_DAGSTER_T3_MICRO_RUNBOOK.md`

### Local Runtime Quick Start (Windows)

Use the local launcher to run Dagster and the Nuxt dashboard together without port conflicts:

```powershell
Set-Location D:\OpenClaw-Backup\clawd\projects\smart-energy-ai
.\scripts\local\start-local-stack.ps1 -Start both
```

The launcher auto-seeds missing runtime JSON state from tracked templates under:
- `dashboard/data/seeds/`
- `energy_ml/configs/templates/`
- `energy_ml/outputs/templates/`
- `energy_ml/energy_ml/outputs/templates/`

The canonical Nuxt app is `dashboard/`. The former `nuxt_dashboard/` legacy parallel tree was archived to `archive/nuxt_dashboard_legacy_20260306/` and is no longer part of the active runtime surface.

Canonical local ports:
- Dagster: `http://127.0.0.1:3000`
- Dashboard: `http://127.0.0.1:3600`

Optional dependency install when `dashboard/node_modules` is missing:

```powershell
.\scripts\local\start-local-stack.ps1 -Start dashboard -InstallDashboardDeps
```

---

## 5. Multi-tenancy & Asset Factories

For scaling to hundreds of clients (shopping malls, offices) we use the `Asset Factory` pattern.

**Configuration (`customers.yaml`):**
```yaml
customers:
  - id: "client_001_kyiv_mall"
    battery_type: "LFP_280Ah"
    location: {lat: 50.45, lon: 30.52}
  - id: "client_002_lviv_office"
    battery_type: "NMC_LG_Chem"
    location: {lat: 49.84, lon: 24.03}
```

Dagster automatically generates isolated asset graphs for each client:
`client_001_optimization -> client_001_schedule`

## 6. Benchmarking & MLflow
For thesis and experimentation work, the repo still includes benchmark and MLflow-facing components:
- **Metric:** Processing Time (seconds) per 1M rows
- **Tracking:** MLflow Experiment `feature_eng_benchmark`
- **Tags:** `engine_type=polars` vs `engine_type=nvtabular`

These paths are useful for benchmarking and experiments, but they are not the current end-to-end live decision engine. In particular, MLflow-backed inference remains optional and falls back to mock behavior unless a real model URI is provided.
The dashboard `/api/mlflow/*` routes should be read as experiment and registry diagnostics, not as proof that the live BUY/SELL/HOLD path is currently served by a learned policy. Runtime serving authority remains the Dagster schedule path and the shared Python serving contract in `ml_integration_api.py`.

**Defensive Logic:**
Code automatically checks for GPU availability:
```python
try:
    import nvtabular as nvt
    import cupy
    HAS_GPU = True
except ImportError:
    HAS_GPU = False  # Fallback to Polars
```

---

## 7. Project Structure (V2)

```
smart-energy-ai/
├── dagster.yaml                        # Dagster deployment config
├── workspace.yaml                      # Asset location descriptions
├── customers.yaml                      # Multi-tenancy config
├── requirements.txt                    # core Python dependencies for orchestration, ML, and local runtime
├── src/
│   ├── __init__.py
│   ├── definitions.py                  # Main Dagster entry point
│   ├── assets/
│   │   ├── core/                       # General data (Prices, Weather)
│   │   │   ├── market.py
│   │   │   └── weather.py
│   │   ├── multi_tenant/               # Asset factories for clients
│   │   │   ├── telemetry.py
│   │   │   └── optimization.py
│   │   └── benchmarks/                 # Dual-Engine assets
│   │       └── feature_eng.py          # Polars vs NVTabular logic
│   ├── resources/
│   │   ├── s3_io_manager.py           # AWS S3 Integration
│   │   └── mlflow_resource.py         # MLflow logging setup
│   ├── physics/
│   │   ├── battery_lfp.py             # Degradation model class
│   │   └── economics.py               # LCOS formulas
│   └── engines/
│       ├── polars_engine.py           # CPU logic implementation
│       └── nvtabular_engine.py        # GPU logic (with try-import)
└── scripts/
    └── deploy_lambda.sh               # Docker container packaging for Lambda
```

---

## 8. Current Implementation Priorities

The current implementation focus is runtime hardening and architectural honesty rather than greenfield V2 scaffolding.

**Near-term priorities:**
1. Keep the Dagster market, weather, forecast, and schedule path stable for local and deployment validation.
2. Treat the dashboard battery and control loop as the current operational state source, while labeling it clearly as simulator-backed telemetry.
3. Keep the dashboard ML fallback path available for degraded operation without overstating it as trained production inference.
4. Align docs and operator workflows with the actual runtime surface in `dashboard/`, `src/`, and `energy_ml/`.

**Constraints:**
* Preserve local degraded-mode behavior when optional services are offline.
* Prefer documentation and validation that distinguish external backfill, simulator history, and fabricated training scaffolding.
* Keep changes consistent with the active Dagster plus Nuxt local stack.

---

## Current Runtime Snapshot (March 2026)

**What is active today:**
- ✅ Dagster market and weather ingestion feeding forecast and schedule assets
- ✅ RandomForest-based price forecasting in the active Dagster path
- ✅ Dashboard-first operator surface in `dashboard/`
- ✅ Simulator-backed tenant battery and control state persisted by the dashboard APIs
- ✅ Dashboard fallback recommendation path using heuristic Python orchestration when Dagster output is unavailable
- ✅ Local Dagster plus Nuxt runtime flow documented and runnable from the repository root

**What is not yet true in the live path:**
- ⚠️ BUY, SELL, or HOLD is not currently produced by a trained end-to-end trading model
- ⚠️ Battery telemetry is simulator-backed, not real MQTT or SCADA plant telemetry
- ⚠️ Legacy supervised ML assets still depend on synthetic history, synthetic labels, or mock-serving behavior

**Future priorities:**
- 📡 Real telemetry ingestion if and when MQTT or SCADA sources become available
- 🔁 Keep Dagster client-state aligned with the simulator-backed tenant loop and avoid reintroducing duplicate synthetic battery truth
- 🧪 Use backfilled market and weather history plus forward-collected simulator history for any future learned action model
- 🌐 Continue deployment hardening for AWS and local operator workflows

---

This document is the high-level runtime overview for the active Smart Energy AI stack. For the current trading-decision path and provenance rules, use `docs/technical/ML_TRADING_DECISION_FRAMEWORK.md` together with `docs/technical/DAGSTER_PIPELINE_DEPENDENCY_MAP.md`.