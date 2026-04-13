# Smart Energy AI Project Schematic

## Project Overview
The Smart Energy AI system is an energy arbitrage platform centered on Dagster orchestration, a canonical Nuxt operator dashboard, and a Python decision stack that currently combines schedule optimization with rule-based and heuristic fallback logic.

## Directory Structure

```
smart-energy-ai/
├── src/                          # Main Python source code
│   ├── assets/                   # Dagster assets
│   │   ├── core/                 # Core data definitions
│   │   │   ├── market.py         # Market data handling
│   │   │   └── weather.py        # Weather data handling
│   │   └── multi_tenant/         # Multi-tenancy support
│   ├── data_pipeline/            # Data ingestion and validation
│   │   ├── ingest_weather.py
│   │   ├── ingest_prices.py
│   │   └── validate.py
│   ├── physics/                  # Battery physics and degradation models
│   ├── engines/                  # Feature engineering engines (Polars, NVTabular)
│   ├── rl_environment.py         # RL environment
│   ├── rl_training.py            # PPO algorithm implementation
│   ├── training_analyzer.py      # Training analysis
│   ├── weather_fetcher.py        # Weather data from Open-Meteo
│   ├── real_price_data.py        # Real price data from European sources
│   ├── oree_*.py                 # OREE price scrapers
│   └── price_processor.py        # Price data processing
├── streamlit_dashboard/          # Legacy Streamlit web interface kept for reference
├── dashboard/                    # Canonical Nuxt3 Vue.js web interface
├── archive/                      # Archived legacy trees and historical snapshots
├── energy_ml/                    # Energy ML runtime and ML ops support code
│   ├── simulator/                # Battery physics and simulation
│   ├── mlops/                    # Model-serving and MLflow support surfaces
│   └── optimizer/                # Optimization and schedule logic
├── data/                         # Data storage
│   ├── raw/
│   ├── processed/
│   └── results/
├── docker/                      # Docker configuration
├── docs/                        # Documentation
├── tests/                       # Test suite
├── artifacts/                   # Generated artifacts
├── plots/                       # Generated plots
├── projects/                    # Project files
├── .beads/                      # Beads issue tracking
├── ml_integration_api.py         # Canonical Python bridge used by dashboard APIs
└── README.md                    # Project documentation
```

## Key Technologies

| Component | Technology |
|-----------|------------|
| **Backend** | Python |
| **Machine Learning** | PyTorch, XGBoost, Optuna, Scikit-learn |
| **Data Processing** | Polars, Pandas, NVTabular |
| **Orchestration** | Dagster |
| **Web Frameworks** | Nuxt3/Vue.js, Streamlit (legacy), CLI-style Python bridges |
| **Storage** | PostgreSQL, AWS S3, Local File System |
| **Deployment** | Docker, Kubernetes, AWS Lambda |
| **APIs** | Open-Meteo, ENTSO-E, Ukrenergo, MQTT |
| **Styling** | Tailwind CSS, Plotly, Vega |

## Data Pipeline

1. **Weather Data**: Fetches data from Open-Meteo API for solar irradiance and temperature forecasts
2. **Price Data**: Scrapes OREE Ukrainian electricity prices using Playwright/Selenium
3. **Data Validation**: Uses Pydantic models to ensure data quality
4. **Feature Engineering**: Generates features using Polars (CPU) or NVTabular (GPU)
5. **Model Training**: Trains XGBoost for price prediction and PPO for RL optimization

## RL Training

1. **Environment**: `rl_environment.py` with battery physics and degradation models
2. **Training**: `rl_training.py` implements PPO algorithm
3. **Checkpoints**: Trained models saved in `checkpoints/` directory
4. **Inference**: Uses trained models for real-time decision-making

## Runtime Surfaces

### Canonical dashboard (`dashboard/`)

- Primary operator-facing web UI used by the local launcher, runtime docs, and current validation flows.
- Default local URL is `http://127.0.0.1:3600`.

### Legacy UIs

- `streamlit_dashboard/` is legacy and no longer the primary runtime path.
- `archive/nuxt_dashboard_legacy_20260306/` is the archived legacy Nuxt application.
- There is no active root-level `nuxt_dashboard/` runtime anymore.

## APIs

### Energy ML bridge (`ml_integration_api.py`)

- Canonical Python bridge invoked by dashboard ML and optimization strategy routes.
- `energy_ml/ml_integration_api.py` now exists only as a compatibility wrapper for older import and cwd-based entrypoints.

## Key Files and Their Purpose

| File | Purpose |
|------|---------|
| `src/physics/battery_lfp.py` | LFP battery degradation model |
| `src/economics.py` | Economic modeling and cost calculations |
| `src/engines/polars_engine.py` | CPU-optimized feature engineering |
| `src/engines/nvtabular_engine.py` | GPU-accelerated feature engineering |
| `src/assets/core/market.py` | Market data asset definition |
| `src/assets/core/weather.py` | Weather data asset definition |
| `src/assets/multi_tenant/optimization.py` | Optimization asset for multi-tenancy |
| `src/data_pipeline/ingest_weather.py` | Weather data ingestion |
| `src/data_pipeline/ingest_prices.py` | Price data ingestion |
| `src/data_pipeline/validate.py` | Data validation using Pydantic |

## Setup and Running

### Nuxt Dashboard

```bash
cd dashboard
npm install
npm run dev
```

### Local Stack

```powershell
.\scripts\local\start-local-stack.ps1 -Start both
```

### Data Pipeline

```bash
# Ingest weather data
python -m src.data_pipeline.ingest_weather

# Ingest price data
python -m src.data_pipeline.ingest_prices
```

### Training

```bash
python -m src.rl_training
```

### Tests

```bash
pytest tests/ -v
```

## Project Conventions

- **Python**: Use type hints, docstrings, and follow PEP 8
- **Vue.js**: Use Composition API, TypeScript, and follow Vue 3 best practices
- **Data**: Use Polars for data processing by default, NVTabular for GPU acceleration
- **Styling**: Use Tailwind CSS for responsive design
- **Documentation**: Write clear READMEs and inline comments

## Current Development Focus

- Harden optimization history and decision-snapshot contracts for Stage 2 learned-policy rollout.
- Keep dashboard behavior grounded in Dagster schedule truth first, with explicit fallback provenance.
- Continue moving legacy/demo surfaces out of the active runtime path.
