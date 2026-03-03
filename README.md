# Smart Energy AI: Autonomous Arbitrage System (UA Market 2026)

## 1. System Overview
**Smart Energy AI** is a data orchestration and decision-making system for energy arbitrage on Ukraine's Day-Ahead Market (DAM) and Intraday Market (IDM).

The system is built on the **Software-Defined Assets (SDA)** principle using Dagster. It solves the multi-objective optimization problem: maximizing profit from buying/selling electricity while accounting for physical degradation of Lithium-Ion (LFP) batteries.

### Key Thesis Benchmark
The system implements **Dual-Engine Architecture** for Feature Engineering, allowing dynamic switching between:
1. **CPU-Optimized:** Rust-based Polars (for AWS Free Tier / Edge Devices)
2. **GPU-Accelerated:** NVIDIA NVTabular (for High-Performance Training on large datasets)

---

## 2. Software-Defined Assets Architecture (DAG)

The dependency graph guarantees that decisions are made only on fresh data.

### Level 1: Ingestion (Sourcing)
* **`market_data_asset`**: Parse hourly prices (EUR/MWh) from ENTSO-E/Ukrenergo API
* **`weather_asset`**: Local forecast (GHI, Temp, Wind Speed) via Open-Meteo API
* **`client_state_asset`**: IoT telemetry (SoC, Voltage, Cycle Count) via MQTT (Venus OS)

### Level 2: Processing (Feature Engineering)
* **`feature_matrix`**: Hybrid asset
  - **Inputs:** Raw time series
  - **Logic:** Generate lags, rolling means, calendar features
  - **Engine:** Selected via config (`execution_mode: "polars" | "nvtabular"`)

### Level 3: Intelligence (Decision)
* **`price_forecast_model`**: XGBoost Regressor (24-hour price prediction)
* **`optimization_engine`**: Optuna Study. Finds optimal charge/discharge schedule
  - **Objective:** `Maximize(Revenue - (GridCost + DegradationCost))`

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

The Optuna optimizer receives penalty if the proposed strategy risks reaching the Knee Point.

---

## 4. Hybrid Deployment (AWS Free Tier Strategy)

Architecture optimized for Free Tier constraints:

| Component | AWS Service | Usage Limits | Role |
|-----------|-------------|--------------|------|
| **Manager** | EC2 `t3.micro` | 750 hours/month | Dagster Webserver, Daemon, Postgres (Metadata) |
| **Compute** | AWS Lambda | 400k GB-seconds | Execute "heavy" Ops (Feature Eng, Optuna Trials) |
| **Storage** | S3 Standard | 5 GB | Store Pickle files (I/O Manager) and logs |
| **Edge** | Local / IoT | N/A | Telemetry collection, local GPU benchmarks |

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
For thesis work, we implement performance comparison:
- **Metric:** Processing Time (seconds) per 1M rows
- **Tracking:** MLflow Experiment `feature_eng_benchmark`
- **Tags:** `engine_type=polars` vs `engine_type=nvtabular`

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
├── requirements.txt                    # polars, dagster, xgboost, optuna...
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

## 8. Implementation Phase 1 (Stage 1 - Current Scope)

**Phase 1: Project Skeleton & Configuration**
1. Initialize folder structure as defined above
2. Create `src/physics/battery_lfp.py` with `DegradationModel` class
   - Implement `calculate_marginal_cost(soc, temp, cycle_depth)` method using formula above
   - Add `predict_sei_growth(time, temp)` for "Knee Point" analysis
3. Create `src/engines/polars_engine.py` and `src/engines/nvtabular_engine.py`
   - **Crucial:** NVTabular engine must use defensive imports so code doesn't crash on CPU instances

**Phase 2: Dagster Asset Factory**
1. Implement `src/assets/multi_tenant/optimization.py`
   - Load `customers.yaml`
   - Use loop to dynamically generate asset groups (`telemetry`, `features`, `schedule`) for each `client_id`
   - The `schedule` asset should call `optuna` to optimize battery charge/discharge plan

**Phase 3: AWS Lambda Compatibility**
1. In `src/resources/s3_io_manager.py`, implement Pickle-based I/O manager that writes intermediate DataFrames to S3. This allows Lambda functions to pass data between steps.

**Constraints:**
* Use `polars` for all default data manipulations
* Ensure all assets produce metadata (row counts, preview, costs)
* Add docstrings in English explaining the "Thesis Relevance" of each module

---

## Current Status: V1 Complete → Starting V2

**V1 Achievements (Completed Jan 2026):**
- ✅ Complete RL-based optimization system
- ✅ Real OREE market data integration
- ✅ 28.6% cost reduction demonstrated
- ✅ Production-ready Streamlit dashboard
- ✅ 87.5% test coverage, comprehensive documentation

**V2 Objectives (Stage 1 - Current):**
- 🎯 Dagster-based Software-Defined Assets
- 🎯 Dual-Engine CPU/GPU benchmarking system
- 🎯 Advanced economic & physical modeling
- 🎯 AWS Free Tier deployment architecture
- 🎯 Multi-tenant asset factory system

**V2 Stage 2 (Future):**
- 📡 Real IoT integration via MQTT
- 🏭 Industrial SCADA system integration
- 🌐 Edge device deployment
- 📱 Real-time mobile notifications

---

This document serves as the "constitution" for the Smart Energy AI V2 project, defining the architecture, scope, and implementation roadmap for the Software-Defined Assets stage.