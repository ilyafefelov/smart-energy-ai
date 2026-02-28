# Smart Energy AI System - Project Schematic

## Overview

The Smart Energy AI system is a comprehensive platform designed to optimize energy storage and consumption for commercial and industrial clients using reinforcement learning (RL) and machine learning (ML) techniques. The system integrates real-time data from electricity markets, weather APIs, and client-specific configurations to provide intelligent energy management solutions.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     Smart Energy AI System                      │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │  Data Sources │  │  Data Pipeline │  │  Energy ML Engine  │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
│         │                │                       │              │
│         ▼                ▼                       ▼              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │ OREE Prices  │  │  Weather Data │  │  RL Training & Inference   │
│  │  (Ukraine)   │  │ (Open-Meteo)  │  │  (PPO Algorithm)    │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
│         │                │                       │              │
│         └──────────┬────┴───────────────────────┘              │
│                    ▼                                           │
│            ┌──────────────┐                                    │
│            │  PostgreSQL  │                                    │
│            │  Data Storage │                                    │
│            └──────────────┘                                    │
│                    │                                           │
│                    ▼                                           │
│  ┌───────────────────────────────────────────────────────┐     │
│  │          Orchestration & Management                    │     │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │     │
│  │  │   Dagster    │  │   MLflow     │  │  Streamlit   │  │     │
│  │  │  (Data Ops)  │  │ (ML Tracking)│  │ (Dashboard)  │  │     │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  │     │
│  └───────────────────────────────────────────────────────┘     │
│                    │                                           │
│                    ▼                                           │
│            ┌──────────────┐                                    │
│            │  Deployment  │                                    │
│            │  (Docker/K8s)│                                    │
│            └──────────────┘                                    │
└─────────────────────────────────────────────────────────────────┘
```

## Component Breakdown

### 1. Data Sources
- **OREE Prices (Ukraine)**: Real-time and historical electricity market prices from the Ukrainian Energy Exchange
- **Weather Data (Open-Meteo)**: Solar irradiance, temperature, and weather forecasts
- **Client Configurations**: Customer-specific data including battery parameters, load profiles, and tariffs

### 2. Data Pipeline
- **Ingestion**: Scripts to fetch and store data from external APIs
- **Validation**: Pydantic-based data quality checks
- **Transformation**: Data normalization and feature engineering

### 3. Energy ML Engine
- **RL Environment**: Battery physics and economic modeling with LFP degradation
- **Training**: Proximal Policy Optimization (PPO) algorithm for RL training
- **Inference**: Real-time decision-making for battery charging/discharging

### 4. Storage & Processing
- **PostgreSQL**: Central data repository for market, weather, and client data
- **Dagster**: Data orchestration and pipeline management
- **MLflow**: Experiment tracking and model registry

### 5. Dashboard & Monitoring
- **Streamlit**: Real-time monitoring and visualization of energy usage, savings, and system performance
- **Performance Metrics**: Cost reduction calculations, battery health monitoring, and optimization results

### 6. Deployment
- **Docker**: Containerization for consistent deployment across environments
- **Kubernetes/AWS ECS**: Scalable cloud deployment options
- **Local Development**: Docker Compose for easy local testing

## Directory Structure

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

## Data Flow

1. **Data Collection**: 
   - OREE prices scraped using Playwright/Selenium
   - Weather data fetched from Open-Meteo API
   - Client state generated synthetically

2. **Data Ingestion**:
   - Data validated using Pydantic models
   - Stored in PostgreSQL for historical analysis

3. **Feature Engineering**:
   - Market prices normalized
   - Weather data transformed for solar irradiance modeling
   - Client-specific features calculated

4. **RL Training**:
   - PPO algorithm trains on historical data
   - Model parameters saved as checkpoints
   - Experiment tracked in MLflow

5. **Inference & Optimization**:
   - Real-time data fed into trained model
   - Optimal charging/discharging decisions generated
   - Savings calculated vs baseline strategy

6. **Visualization**:
   - Results displayed in Streamlit dashboard
   - Performance metrics monitored in real-time

## Key Technologies

- **Programming Languages**: Python, JavaScript
- **Frameworks**: PyTorch, Scikit-learn, Streamlit, Dagster
- **Data Storage**: PostgreSQL
- **Orchestration**: Docker, Kubernetes, AWS ECS
- **APIs**: Open-Meteo, OREE (Ukraine)
- **Tools**: MLflow, Playwright, Selenium

## Development Workflow

1. **Local Development**: Use Docker Compose for local environment
2. **Testing**: Comprehensive test suite with pytest
3. **Deployment**: CI/CD pipeline with GitHub Actions
4. **Monitoring**: MLflow for experiment tracking, PostgreSQL for logs

## Future Improvements

- **Price Forecasting**: LSTM/Prophet models for price prediction
- **Solar Generation**: Advanced solar forecasting models
- **Real-time Optimization**: Faster inference and decision-making
- **Multi-client Support**: Scalable architecture for multiple clients
- **Advanced Analytics**: Deep learning models for energy load forecasting

This schematic provides a comprehensive overview of the Smart Energy AI system, including its architecture, components, data flow, and development workflow. It serves as a guide for understanding and extending the system.