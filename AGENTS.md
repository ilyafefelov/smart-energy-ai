# Smart Energy AI - Agent Instructions

This project uses **bd** (beads) for issue tracking. Run `bd onboard` to get started.

## Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --status in_progress  # Claim work
bd close <id>         # Complete work
bd sync               # Sync with git
```

## Project Overview

The Smart Energy AI system is a comprehensive platform designed to optimize energy storage and consumption for commercial and industrial clients using reinforcement learning (RL) and machine learning (ML) techniques. The system integrates real-time data from electricity markets, weather APIs, and client-specific configurations to provide intelligent energy management solutions.

## Project Structure

```
smart-energy-ai/
├── src/                          # Main source code
│   ├── rl_environment.py        # RL environment with battery physics
│   ├── rl_training.py           # PPO algorithm implementation
│   ├── weather_fetcher.py       # Weather data from Open-Meteo
│   ├── real_price_data.py       # Real price data from European sources
│   ├── oree_*.py                # OREE price scrapers (Playwright, Selenium)
│   ├── data_pipeline/           # Data ingestion and validation
│   │   ├── ingest_weather.py
│   │   ├── ingest_prices.py
│   │   └── validate.py
│   └── assets/core/             # Dagster assets (data definitions)
│       ├── market.py
│       ├── weather.py
│       └── client_state.py
├── dashboard/                    # Streamlit web interface
├── config/                       # Configuration files
├── data/                        # Data storage
│   ├── raw/
│   └── processed/
├── docker/                      # Docker configuration
├── checkpoints/                 # Model checkpoints
├── docs/                        # Documentation
└── tests/                       # Test suite
```

## Key Technologies

- **Programming Languages**: Python, JavaScript
- **Frameworks**: PyTorch, Scikit-learn, Streamlit, Dagster
- **Data Storage**: PostgreSQL
- **Orchestration**: Docker, Kubernetes, AWS ECS
- **APIs**: Open-Meteo, OREE (Ukraine)
- **Tools**: MLflow, Playwright, Selenium

## Development Guidelines

### Getting Started

1. **Set up environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   .\venv\Scripts\Activate.ps1  # Windows
   pip install -r requirements.txt
   pip install -r requirements-test.txt
   ```

2. **Run tests**:
   ```bash
   pytest tests/ -v
   ```

3. **Run the dashboard**:
   ```bash
   streamlit run app.py
   ```

4. **Run data pipeline**:
   ```bash
   python -m src.data_pipeline.ingest_weather
   python -m src.data_pipeline.ingest_prices
   ```

### Working with Docker

1. **Build image**:
   ```bash
   docker build -t smart-energy-ai .
   ```

2. **Run container**:
   ```bash
   docker run -p 8501:8501 --env-file .env smart-energy-ai
   ```

3. **Local development with Docker Compose**:
   ```bash
   cd docker
   docker-compose up -d
   ```

### Data Pipeline

1. **Weather Data**: Fetches data from Open-Meteo API for solar irradiance and temperature forecasts
2. **Price Data**: Scrapes OREE Ukrainian electricity prices using Playwright or Selenium
3. **Data Validation**: Uses Pydantic models to ensure data quality and consistency

### RL Training

1. **Training**: Run `rl_training.py` to train the PPO algorithm
2. **Checkpoints**: Trained models are saved in `checkpoints/` directory
3. **Inference**: Use trained models for real-time decision-making

### Dashboard

- **Streamlit Dashboard**: Real-time monitoring of energy usage, savings, and system performance
- **Visualizations**: Cost reduction calculations, battery health monitoring, and optimization results

## Issue Tracking

The project uses **bd** (beads) for issue tracking. All issues are stored in `.beads/issues.jsonl`.

### Common Tasks

1. **View all open issues**:
   ```bash
   bd ready
   ```

2. **View issue details**:
   ```bash
   bd show <issue-id>
   ```

3. **Claim an issue**:
   ```bash
   bd update <issue-id> --status in_progress
   ```

4. **Complete an issue**:
   ```bash
   bd close <issue-id>
   ```

## Resources

- **Project Schematic**: `PROJECT_SCHEMATIC.md` - Comprehensive architecture overview
- **API Documentation**: `API_DOCUMENTATION_IMPORT_EXPORT.md`
- **ML Pipeline**: `ML_PIPELINE_PLAN.md`
- **Testing Guide**: `TEST_PIPELINE_GUIDE.md`