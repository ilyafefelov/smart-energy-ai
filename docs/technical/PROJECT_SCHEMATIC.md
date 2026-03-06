# Smart Energy AI Project Schematic

## Project Overview
The Smart Energy AI system is an autonomous energy arbitrage platform designed to optimize energy storage and consumption for commercial and industrial clients using reinforcement learning and machine learning techniques.

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
├── streamlit_dashboard/          # Streamlit web interface
│   ├── app.py                    # Main Streamlit app
│   └── app_config.py             # Streamlit configuration
├── nuxt_dashboard/               # Nuxt3 Vue.js web interface
│   ├── app/                      # Application pages
│   ├── pages/                    # Page components (index, analytics, control, settings)
│   ├── components/               # Reusable Vue components
│   ├── composables/              # Vue composables
│   ├── stores/                   # Vuex stores
│   ├── layouts/                  # Page layouts
│   ├── data/                     # Static data files
│   ├── package.json              # NPM dependencies
│   ├── nuxt.config.ts            # Nuxt configuration
│   ├── tailwind.config.ts        # Tailwind CSS configuration
│   └── tsconfig.json             # TypeScript configuration
├── energy_ml/                    # Energy ML module with APIs
│   ├── simulator/                # Battery physics and simulation
│   ├── ml_integration_api.py     # API for ML integration
│   └── control_api.py            # Control system API
├── config/                       # Configuration files
├── data/                        # Data storage
│   ├── raw/
│   └── processed/
├── checkpoints/                 # Model checkpoints
├── docker/                      # Docker configuration
├── docs/                        # Documentation
├── tests/                       # Test suite
├── notebooks/                   # Jupyter notebooks
├── artifacts/                   # Generated artifacts
├── plots/                       # Generated plots
├── memory/                      # Memory files
├── projects/                    # Project files
├── .beads/                      # Beads issue tracking
└── README.md                    # Project documentation
```

## Key Technologies

| Component | Technology |
|-----------|------------|
| **Backend** | Python |
| **Machine Learning** | PyTorch, XGBoost, Optuna, Scikit-learn |
| **Data Processing** | Polars, Pandas, NVTabular |
| **Orchestration** | Dagster |
| **Web Frameworks** | Streamlit, Nuxt3/Vue.js, FastAPI |
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

## Dashboards

### Streamlit Dashboard (`streamlit_dashboard/`)

- **Main App**: `streamlit_dashboard/app.py` - Real-time monitoring of energy usage, savings, and system performance
- **Configuration**: `streamlit_dashboard/app_config.py` - Dashboard settings and constants
- **Features**:
  - Scenario selection (Normal, Winter, Blackout)
  - Hour-by-hour energy strategy visualization
  - Battery SOC and health monitoring
  - Training analysis and model evaluation
  - Technical guide and documentation

### Nuxt Dashboard (`nuxt_dashboard/`)

- **Pages**:
  - `index.vue` - Main dashboard with KPIs
  - `analytics.vue` - Data analytics and reports
  - `control.vue` - System control and management
  - `settings.vue` - Configuration settings
  - `configuration.vue` - Battery and market configuration
- **Features**:
  - Real-time energy data visualization
  - Control system integration
  - Settings management and import/export
  - Analytics and reporting
  - Responsive UI with Tailwind CSS

## APIs

### Energy ML API (`energy_ml/ml_integration_api.py`)

- **Endpoints**:
  - `/api/control/status` - Get system status
  - `/api/control/execute` - Execute control commands
  - `/api/control/schedule` - Get optimization schedule
  - `/api/settings/battery` - Manage battery settings
  - `/api/settings/market` - Manage market settings

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

### Streamlit Dashboard

```bash
cd streamlit_dashboard
streamlit run app.py
```

Equivalent root-level invocation:

```bash
streamlit run streamlit_dashboard/app.py
```

### Nuxt Dashboard

```bash
cd nuxt_dashboard
npm install
npm run dev
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

## Future Development

- Real IoT integration via MQTT
- Industrial SCADA system integration
- Edge device deployment
- Real-time mobile notifications
