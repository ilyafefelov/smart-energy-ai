# Phase 3: ML Pipeline with Dagster - Complete Architecture

**Status:** ✅ Specification in progress  
**Date:** 2026-02-07 17:35 GMT+2  
**Architecture:** Software-Defined Assets (Dagster)  

---

## 🎯 Your Vision (Locked In)

### Core Stack
- **Orchestration:** Dagster (Software-Defined Assets with full lineage tracking)
- **Computation:** Dask (distributed, parallel processing for 1000s of clients)
- **Data Prep:** NVTabular (GPU-accelerated time-series encoding)
- **Features:** Featuretools (automated complex feature relationships)
- **Optimization:** Optuna (automated hyperparameter tuning for strategy)
- **Modeling:** XGBoost/LightGBM (batch forecasting) + River (online learning for minute-scale prices)

### Why This Stack

| Component | Why | Benefit |
|-----------|-----|---------|
| **Dagster** | Orchestration + lineage | Know which data fed each recommendation, auto-recompute on updates |
| **Dask** | Distributed computation | Scale to 1000s of users without rewriting code |
| **NVTabular** | GPU time-series prep | 100x faster feature engineering on GPU |
| **Featuretools** | Auto relationships | Discover hidden feature interactions automatically |
| **Optuna** | Hyperparameter tuning | Find optimal strategy parameters (profit vs risk trade-offs) |
| **XGBoost/LightGBM** | Batch forecasting | High accuracy for hourly predictions |
| **River** | Online learning | Adapt to minute-scale price changes in real-time |

---

## 🏗️ Phase 3: Complete Dagster-Based Architecture

### Overview
```
DATA LAYER (Assets)
├── weather_data (OpenWeatherAPI → Dagster Asset)
├── price_data (OREE scraper → Dagster Asset)
├── solar_irradiance (calculated → Dagster Asset)
└── wind_forecast (calculated → Dagster Asset)

FEATURE ENGINEERING LAYER (Assets)
├── time_features (Dask + NVTabular → Asset)
├── weather_features (Dask + NVTabular → Asset)
├── price_features (Dask + NVTabular → Asset)
├── generation_features (Dask + NVTabular → Asset)
├── battery_features (Dask + NVTabular → Asset)
└── complex_features (Featuretools → Asset)

TRAINING LAYER (Assets)
├── feature_matrix (combine all features → Asset)
├── train_test_split (versioned → Asset)
├── xgboost_model (trained on batch data → Asset)
├── lightgbm_model (alternative → Asset)
└── river_model (online learning → Asset)

OPTIMIZATION LAYER (Assets)
├── strategy_parameters (Optuna study → Asset)
├── backtesting_results (strategy validation → Asset)
└── optimal_strategy (best params → Asset)

RECOMMENDATION LAYER (Assets)
├── current_recommendation (based on latest data → Asset)
├── 24h_schedule (hourly recommendations → Asset)
├── confidence_metrics (model confidence → Asset)
└── lineage_report (data provenance → Asset)

MONITORING LAYER (Assets)
├── model_performance (accuracy tracking → Asset)
├── recommendation_performance (vs actual prices → Asset)
└── alerts (retraining triggers → Asset)
```

### Key Dagster Concepts Applied

1. **Software-Defined Assets (SDAs)**
   - Each data transformation is an Asset
   - Automatic dependency tracking
   - Data lineage visualization in Dagster UI

2. **Lineage Tracking**
   - Know exactly which weather data → which price forecast → which recommendation
   - Full provenance for each decision

3. **Automatic Recomputation**
   - Weather API updates → Automatically trigger solar/wind recalc
   - Solar/wind updates → Automatically trigger feature recalc
   - Features update → Automatically trigger model retraining
   - Model updates → Automatically trigger recommendations

4. **Multi-Asset Jobs**
   - Batch daily: recompute all historical features + retrain models
   - Hourly: update current data + generate recommendations
   - On-demand: user settings change → retrain strategy parameters

---

## 📋 Phase 3A: Dagster Foundation (4-5 hours)

### Task 1: Dagster Setup & Project Structure (30 min)

**1.1 Create Dagster project**
```bash
cd projects/smart-energy-ai
dagster project scaffold --name energy_ml
cd energy_ml
pip install dagster dagster-webui python-dotenv
```

**1.2 Project structure**
```
energy_ml/
├── energy_ml/
│   ├── __init__.py
│   ├── assets/
│   │   ├── __init__.py
│   │   ├── data_sources.py (weather, price, solar, wind)
│   │   ├── features.py (time, weather, price, generation, battery)
│   │   ├── training.py (feature matrix, train/test, models)
│   │   ├── optimization.py (Optuna hyperparameter tuning)
│   │   └── recommendations.py (current rec, 24h schedule, lineage)
│   ├── jobs/
│   │   ├── __init__.py
│   │   ├── daily_batch.py (daily retraining job)
│   │   ├── hourly_update.py (hourly data + recommendations)
│   │   └── on_demand.py (settings change trigger)
│   ├── resources/
│   │   ├── __init__.py
│   │   ├── dask_resource.py (Dask client)
│   │   ├── nvtabular_resource.py (GPU workflow)
│   │   ├── optuna_resource.py (study manager)
│   │   └── db_resource.py (model & parameter storage)
│   ├── io_managers/
│   │   ├── __init__.py
│   │   └── parquet_io_manager.py (Dask dataframes → Parquet)
│   ├── definitions.py (Dagster definitions)
│   ├── utils.py (helpers)
│   └── config.py (configuration)
├── tests/
├── setup.py
├── pyproject.toml
└── README.md
```

**1.3 Install dependencies**
```bash
pip install \
  dagster \
  dagster-webui \
  dask[dataframe] \
  nvtabular \
  featuretools \
  optuna \
  xgboost \
  lightgbm \
  river \
  pandas \
  numpy \
  scikit-learn \
  requests \
  python-dotenv \
  sqlalchemy \
  pyarrow
```

---

### Task 2: Data Source Assets (45 min)

**File: `energy_ml/assets/data_sources.py`**

```python
from dagster import asset, Output, In, Field
from dagster_dask import dask_io_manager
import requests
import pandas as pd
from datetime import datetime, timedelta
import dask.dataframe as dd

# Configuration
OPENWEATHER_API_KEY = "your_key"
KYIV_LAT, KYIV_LON = 50.45, 30.52
OREE_API_URL = "https://www.oree.com.ua/api/..."

@asset(
    description="Real-time weather data for Kyiv from OpenWeatherAPI",
    tags={"domain": "data_sources", "refresh": "hourly"}
)
def weather_data(context) -> Output[pd.DataFrame]:
    """Fetch current weather from OpenWeatherAPI"""
    response = requests.get(
        f"https://api.openweathermap.org/data/2.5/weather?"
        f"lat={KYIV_LAT}&lon={KYIV_LON}&appid={OPENWEATHER_API_KEY}&units=metric"
    )
    data = response.json()
    
    df = pd.DataFrame({
        'timestamp': [datetime.utcnow()],
        'temp': [data['main']['temp']],
        'humidity': [data['main']['humidity']],
        'cloud_cover': [data['clouds']['all']],
        'wind_speed': [data['wind']['speed']],
        'wind_direction': [data['wind'].get('deg', 0)],
        'pressure': [data['main']['pressure']],
    })
    
    context.log.info(f"Fetched weather: {df['temp'].values[0]}°C")
    return Output(df, metadata={"rows": len(df)})

@asset(
    description="5-day weather forecast for Kyiv",
    tags={"domain": "data_sources", "refresh": "hourly"}
)
def weather_forecast(context) -> Output[pd.DataFrame]:
    """Fetch 5-day forecast from OpenWeatherAPI"""
    response = requests.get(
        f"https://api.openweathermap.org/data/2.5/forecast?"
        f"lat={KYIV_LAT}&lon={KYIV_LON}&appid={OPENWEATHER_API_KEY}&units=metric"
    )
    data = response.json()
    
    records = []
    for item in data['list'][:40]:  # 5 days
        records.append({
            'timestamp': pd.Timestamp.fromtimestamp(item['dt']),
            'temp': item['main']['temp'],
            'cloud_cover': item['clouds']['all'],
            'wind_speed': item['wind']['speed'],
            'precipitation': item.get('rain', {}).get('3h', 0),
        })
    
    df = pd.DataFrame(records)
    context.log.info(f"Fetched forecast: {len(df)} records")
    return Output(df, metadata={"rows": len(df)})

@asset(
    description="Real-time electricity prices from OREE (Ukrainian market)",
    tags={"domain": "data_sources", "refresh": "hourly"}
)
def price_data_current(context) -> Output[pd.DataFrame]:
    """Fetch current hourly prices from OREE"""
    # Placeholder - actual API integration depends on OREE structure
    df = pd.DataFrame({
        'timestamp': [datetime.utcnow()],
        'price_uah_per_kwh': [14.26],
        'price_trend': [1],  # 1=increasing, 0=stable, -1=decreasing
    })
    context.log.info(f"Fetched price: {df['price_uah_per_kwh'].values[0]} ₴/kWh")
    return Output(df, metadata={"rows": len(df)})

@asset(
    description="Historical price data (last 2 years)",
    tags={"domain": "data_sources", "refresh": "daily"}
)
def price_data_historical(context) -> Output[dd.DataFrame]:
    """Load 2-year price history as Dask dataframe"""
    # Load from parquet or database
    df = pd.read_csv("data/price_history.csv", parse_dates=['timestamp'])
    ddf = dd.from_pandas(df, npartitions=100)  # Dask dataframe
    
    context.log.info(f"Loaded price history: {len(df)} records")
    return Output(ddf, metadata={"rows": len(df)})

@asset(
    description="Solar irradiance data (calculated from weather)",
    ins={"weather": In(weather_data)},
    tags={"domain": "data_sources", "refresh": "hourly"}
)
def solar_irradiance(context, weather: pd.DataFrame) -> Output[pd.DataFrame]:
    """Calculate solar irradiance based on sun position and weather"""
    from energy_ml.utils import calculate_solar_position, calculate_irradiance
    
    # Calculate solar position for Kyiv
    position = calculate_solar_position(KYIV_LAT, KYIV_LON, datetime.utcnow())
    irradiance = calculate_irradiance(position, weather['cloud_cover'].values[0])
    
    df = pd.DataFrame({
        'timestamp': weather['timestamp'],
        'irradiance_w_per_m2': [irradiance['GHI']],
        'elevation': [position['elevation']],
        'azimuth': [position['azimuth']],
    })
    
    context.log.info(f"Calculated irradiance: {irradiance['GHI']} W/m²")
    return Output(df, metadata={"irradiance_w_m2": irradiance['GHI']})

@asset(
    description="Wind power potential (calculated from weather)",
    ins={"weather": In(weather_data)},
    tags={"domain": "data_sources", "refresh": "hourly"}
)
def wind_potential(context, weather: pd.DataFrame) -> Output[pd.DataFrame]:
    """Calculate wind power potential from wind speed"""
    from energy_ml.utils import wind_power_curve
    
    wind_speed = weather['wind_speed'].values[0]
    power = wind_power_curve(wind_speed)
    
    df = pd.DataFrame({
        'timestamp': weather['timestamp'],
        'wind_speed': [wind_speed],
        'power_potential': [power],
    })
    
    context.log.info(f"Wind potential: {power} (wind speed: {wind_speed} m/s)")
    return Output(df, metadata={"wind_speed": wind_speed})

@asset(
    description="Battery state from smart meter",
    tags={"domain": "data_sources", "refresh": "hourly"}
)
def battery_state(context) -> Output[pd.DataFrame]:
    """Fetch current battery state"""
    df = pd.DataFrame({
        'timestamp': [datetime.utcnow()],
        'soc': [72.6],  # State of charge %
        'charge_rate': [3.5],  # kW
        'discharge_rate': [4.2],  # kW
    })
    return Output(df, metadata={"soc": 72.6})
```

---

### Task 3: Feature Engineering Assets (60 min)

**File: `energy_ml/assets/features.py`**

```python
from dagster import asset, In, Output, Field, DynamicOut, DynamicOutput
from dagster_dask import dask_io_manager
import pandas as pd
import dask.dataframe as dd
from datetime import datetime, timedelta
import featuretools as ft
from nvtabular import Workflow
import nvtabular.ops as ops

@asset(
    description="Time-based features (hour, day, season, holiday)",
    ins={"price_data": In(price_data_current)},
    tags={"domain": "features"}
)
def time_features(context, price_data: pd.DataFrame) -> Output[pd.DataFrame]:
    """Create time-based features"""
    df = price_data.copy()
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    df['hour'] = df['timestamp'].dt.hour
    df['day_of_week'] = df['timestamp'].dt.dayofweek
    df['day_of_month'] = df['timestamp'].dt.day
    df['month'] = df['timestamp'].dt.month
    df['quarter'] = df['timestamp'].dt.quarter
    df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)
    df['is_holiday'] = 0  # Placeholder
    
    # Season
    df['season'] = df['month'].apply(lambda m: 
        0 if m in [12, 1, 2] else  # Winter
        1 if m in [3, 4, 5] else   # Spring
        2 if m in [6, 7, 8] else   # Summer
        3  # Fall
    )
    
    context.log.info(f"Created time features for {len(df)} records")
    return Output(df, metadata={"features_created": 9})

@asset(
    description="Weather-based features (normalized, lagged)",
    ins={"weather": In(weather_data), "weather_forecast": In(weather_forecast)},
    tags={"domain": "features"}
)
def weather_features(context, weather: pd.DataFrame, weather_forecast: pd.DataFrame) -> Output[pd.DataFrame]:
    """Create weather features using NVTabular on GPU if available"""
    df = weather.copy()
    
    # Current features
    df['temp_norm'] = (df['temp'] + 5) / 35  # Normalize -5 to +30°C
    df['humidity_norm'] = df['humidity'] / 100
    df['cloud_cover_norm'] = df['cloud_cover'] / 100
    
    # Forecast aggregates (from forecast data)
    df['temp_forecast_mean_3h'] = weather_forecast['temp'].rolling(3, min_periods=1).mean().iloc[0]
    df['wind_forecast_max_6h'] = weather_forecast['wind_speed'].rolling(6, min_periods=1).max().iloc[0]
    
    # Weather condition encoding
    df['is_clear'] = (df['cloud_cover'] < 30).astype(int)
    df['is_cloudy'] = ((df['cloud_cover'] >= 30) & (df['cloud_cover'] < 70)).astype(int)
    df['is_overcast'] = (df['cloud_cover'] >= 70).astype(int)
    
    context.log.info(f"Created weather features for {len(df)} records")
    return Output(df, metadata={"features_created": 9})

@asset(
    description="Price trend features (lags, moving averages, volatility)",
    ins={"price_historical": In(price_data_historical)},
    tags={"domain": "features"}
)
def price_features(context, price_historical: dd.DataFrame) -> Output[dd.DataFrame]:
    """Create price trend features using Dask for distributed computation"""
    
    # Convert to pandas for computation (can use Dask groupby for large datasets)
    df = price_historical.compute().sort_values('timestamp')
    
    # Lags
    for lag in [1, 3, 6, 12, 24]:
        df[f'price_lag_{lag}h'] = df['price_uah_per_kwh'].shift(lag)
    
    # Moving averages
    for window in [6, 12, 24]:
        df[f'price_ma_{window}h'] = df['price_uah_per_kwh'].rolling(window).mean()
    
    # Volatility (std dev of returns)
    for window in [6, 24]:
        returns = df['price_uah_per_kwh'].pct_change()
        df[f'volatility_{window}h'] = returns.rolling(window).std()
    
    # Trend
    df['price_trend'] = df['price_uah_per_kwh'].diff().apply(lambda x: 1 if x > 0 else -1 if x < 0 else 0)
    
    # Peak detection
    df['is_peak_hour'] = (df.set_index('timestamp').index.hour >= 14).astype(int)
    df['is_off_peak_hour'] = (df.set_index('timestamp').index.hour < 7).astype(int)
    
    ddf = dd.from_pandas(df, npartitions=100)
    context.log.info(f"Created price features: {len(df)} records, {df.shape[1]} features")
    return Output(ddf, metadata={"features_created": 20, "lag_features": 5})

@asset(
    description="Generation features (solar/wind potential from settings)",
    ins={
        "solar_irradiance": In(solar_irradiance),
        "wind_potential": In(wind_potential)
    },
    tags={"domain": "features"}
)
def generation_features(context, solar_irradiance: pd.DataFrame, wind_potential: pd.DataFrame) -> Output[pd.DataFrame]:
    """Create generation features based on user capacity settings"""
    
    # User settings (from app)
    solar_capacity_kw = 10  # Get from settingsStore
    wind_capacity_kw = 5
    panel_efficiency = 0.18
    
    df = solar_irradiance.copy()
    
    # Convert irradiance to generation
    df['solar_generation_kw'] = (df['irradiance_w_per_m2'] * solar_capacity_kw * panel_efficiency) / 1000
    
    # Wind generation
    df['wind_generation_kw'] = wind_potential['power_potential'].values * wind_capacity_kw / 10
    
    # Total generation
    df['total_generation_kw'] = df['solar_generation_kw'] + df['wind_generation_kw']
    
    # Generation potential (0-1)
    df['solar_potential'] = df['irradiance_w_per_m2'] / 1000  # 0-1 normalized
    df['wind_potential'] = wind_potential['power_potential'].values / 10
    
    context.log.info(f"Solar gen: {df['solar_generation_kw'].values[0]:.2f} kW, Wind gen: {df['wind_generation_kw'].values[0]:.2f} kW")
    return Output(df, metadata={"solar_capacity_kw": solar_capacity_kw, "wind_capacity_kw": wind_capacity_kw})

@asset(
    description="Battery state features",
    ins={"battery": In(battery_state)},
    tags={"domain": "features"}
)
def battery_features(context, battery: pd.DataFrame) -> Output[pd.DataFrame]:
    """Create battery state features"""
    
    df = battery.copy()
    
    # Normalized SOC
    df['soc_norm'] = df['soc'] / 100
    
    # Battery health (placeholder - would come from BMS)
    df['battery_health'] = 0.95  # 95% health
    
    # Time to full/empty
    charge_rate = df['charge_rate'].values[0]
    discharge_rate = df['discharge_rate'].values[0]
    
    df['hours_to_full'] = (100 - df['soc'].values[0]) / charge_rate if charge_rate > 0 else 999
    df['hours_to_empty'] = df['soc'].values[0] / discharge_rate if discharge_rate > 0 else 999
    
    # Discharge schedule active
    df['discharge_schedule_active'] = 0  # Get from settings
    
    context.log.info(f"Battery SOC: {df['soc'].values[0]}%, Health: {df['battery_health'].values[0]}")
    return Output(df, metadata={"soc": df['soc'].values[0], "health": df['battery_health'].values[0]})

@asset(
    description="Complex features from Featuretools (feature relationships)",
    ins={
        "price": In(price_features),
        "weather": In(weather_features),
        "generation": In(generation_features),
        "battery": In(battery_features)
    },
    tags={"domain": "features", "featuretools": True}
)
def featuretools_features(context, price, weather, generation, battery) -> Output[pd.DataFrame]:
    """Use Featuretools to discover complex feature relationships"""
    
    # Create entity set
    es = ft.EntitySet(id="energy_system")
    
    # Add entities
    es.add_dataframe(dataframe_name="price", dataframe=price)
    es.add_dataframe(dataframe_name="weather", dataframe=weather)
    es.add_dataframe(dataframe_name="generation", dataframe=generation)
    es.add_dataframe(dataframe_name="battery", dataframe=battery)
    
    # Define relationships (based on timestamp)
    # This is simplified - in production would define more complex relationships
    
    # Deep feature synthesis
    feature_matrix, features = ft.dfs(
        entityset=es,
        target_dataframe_name="price",
        max_depth=2,
        verbose=True
    )
    
    context.log.info(f"Featuretools created {len(feature_matrix.columns)} features")
    return Output(feature_matrix, metadata={"features_generated": len(feature_matrix.columns)})

@asset(
    description="Combined feature matrix ready for ML training",
    ins={
        "time_ft": In(time_features),
        "weather_ft": In(weather_features),
        "price_ft": In(price_features),
        "generation_ft": In(generation_features),
        "battery_ft": In(battery_features),
        "featuretools_ft": In(featuretools_features)
    },
    tags={"domain": "features", "ml_ready": True}
)
def feature_matrix(context, time_ft, weather_ft, price_ft, generation_ft, battery_ft, featuretools_ft) -> Output[pd.DataFrame]:
    """Combine all features into single matrix for training"""
    
    # Align all features by timestamp
    combined = pd.concat([
        time_ft.set_index('timestamp'),
        weather_ft.set_index('timestamp'),
        generation_ft.set_index('timestamp'),
        battery_ft.set_index('timestamp'),
    ], axis=1)
    
    # Fill missing values
    combined = combined.fillna(method='ffill').fillna(method='bfill')
    
    # Add complex featuretools features
    complex = featuretools_ft.copy()
    combined = combined.join(complex, how='left')
    
    context.log.info(f"Feature matrix: {combined.shape[0]} rows × {combined.shape[1]} columns")
    return Output(combined, metadata={
        "rows": combined.shape[0],
        "columns": combined.shape[1],
        "missing_values": int(combined.isnull().sum().sum())
    })
```

---

### Task 4: Dagster Resources (30 min)

**File: `energy_ml/resources/__init__.py`**

```python
from dagster import resource
from dask.distributed import Client
import dask
import tempfile

@resource
def dask_resource():
    """Dask client for distributed computation"""
    # Local cluster (can be changed to remote)
    client = Client(processes=False, n_workers=4, threads_per_worker=2)
    yield client
    client.close()

@resource
def io_manager_resource():
    """IO manager for storing assets as Parquet"""
    from dagster_dask import dask_io_manager
    return dask_io_manager

@resource
def optuna_resource():
    """Optuna study manager for hyperparameter optimization"""
    import optuna
    study = optuna.create_study(
        direction='maximize',  # Maximize profit
        sampler=optuna.samplers.TPESampler()
    )
    yield study
```

---

### Task 5: Define Dagster Job (30 min)

**File: `energy_ml/jobs/daily_batch.py`**

```python
from dagster import define_asset_job, DefaultSensorDefinition, build_schedule_from_partitioned_asset
from energy_ml.assets.data_sources import *
from energy_ml.assets.features import *
from energy_ml.assets.training import *
from energy_ml.assets.recommendations import *

# Daily batch job - retrain models, update all features
daily_batch_job = define_asset_job(
    name="daily_batch_job",
    selection=all_assets,  # Recompute all
    tags={"batch": True, "frequency": "daily"}
)
```

---

### Task 6: Dagster Definitions (20 min)

**File: `energy_ml/definitions.py`**

```python
from dagster import Definitions, load_assets_from_modules, DefaultSensorDefinition
from energy_ml import assets
from energy_ml.jobs import daily_batch_job
from energy_ml.resources import dask_resource, io_manager_resource, optuna_resource

# Load all assets
asset_modules = [assets.data_sources, assets.features, assets.training, assets.optimization, assets.recommendations]
all_assets = load_assets_from_modules(asset_modules)

# Define Dagster instance
defs = Definitions(
    assets=all_assets,
    jobs=[daily_batch_job],
    resources={
        "dask": dask_resource,
        "io_manager": io_manager_resource,
        "optuna": optuna_resource,
    }
)
```

---

### Task 7: Launch Dagster UI (10 min)

```bash
cd energy_ml
dagster dev  # Starts Dagster UI at http://localhost:3000
```

In Dagster UI:
- See all assets (data sources → features → models → recommendations)
- See lineage (which data fed which decisions)
- Trigger jobs manually
- Monitor asset versions
- See asset materialization history

---

## 📊 Phase 3B: Advanced Features (4-5 hours)

### NVTabular GPU Feature Engineering
```python
@asset
def nvtabular_workflow(context, price_features: pd.DataFrame):
    """GPU-accelerated time-series feature engineering"""
    from nvtabular import Workflow
    import nvtabular.ops as ops
    
    # Create workflow
    workflow = Workflow(
        cat_names=["hour", "day_of_week", "season"],
        cont_names=["price_lag_1", "price_lag_3", "volatility_24h"],
        label_name="action"
    )
    
    # Define transformations
    workflow.add_feature(
        ops.Lag("price", shifts=[1, 3, 6, 12, 24]),
        ops.ExpandingMean("price", window=24),
        ops.DifferenceOp("price", periods=[1, 24])
    )
    
    # Fit on GPU
    workflow.fit(price_features)
    features = workflow.transform(price_features)
    
    return features
```

### Optuna Hyperparameter Optimization
```python
@asset
def optimal_strategy_params(context, feature_matrix: pd.DataFrame, optuna_resource):
    """Use Optuna to find optimal strategy parameters"""
    
    def objective(trial):
        # Parameters to optimize
        profit_weight = trial.suggest_float('profit_weight', 0.3, 1.0)
        safety_weight = trial.suggest_float('safety_weight', 0.1, 0.8)
        min_soc_threshold = trial.suggest_int('min_soc_threshold', 20, 60)
        
        # Backtest with these parameters
        profit = backtest_strategy(feature_matrix, profit_weight, safety_weight, min_soc_threshold)
        
        # Return profit (maximize)
        return profit
    
    # Run Optuna study
    optuna_resource.optimize(objective, n_trials=100)
    
    # Get best params
    best_params = optuna_resource.best_params
    
    return best_params
```

### XGBoost + River Hybrid Models
```python
@asset
def xgboost_batch_model(context, feature_matrix: pd.DataFrame):
    """XGBoost for hourly batch predictions"""
    from xgboost import XGBRegressor
    
    model = XGBRegressor(n_estimators=100, max_depth=6)
    model.fit(feature_matrix.drop('price', axis=1), feature_matrix['price'])
    
    # Save model
    model.save_model("models/xgboost_latest.model")
    return model

@asset
def river_online_model(context, feature_matrix: pd.DataFrame):
    """River for minute-scale online learning"""
    from river import linear_model, preprocessing
    
    model = preprocessing.StandardScaler() | linear_model.LinearRegression()
    
    # Train online on streaming data
    for i in range(len(feature_matrix)):
        x = feature_matrix.iloc[i].drop('price').to_dict()
        y = feature_matrix.iloc[i]['price']
        model.learn_one(x, y)
    
    return model
```

---

## 🎯 Phase 3C: Recommendations & Monitoring (2-3 hours)

### Recommendation Asset
```python
@asset(deps=[xgboost_batch_model, feature_matrix])
def current_recommendation(context, feature_matrix: pd.DataFrame) -> Output[dict]:
    """Generate current recommendation with lineage"""
    
    # Load latest model
    from xgboost import XGBRegressor
    model = XGBRegressor()
    model.load_model("models/xgboost_latest.model")
    
    # Get latest features
    latest_features = feature_matrix.iloc[-1].drop('price')
    
    # Predict
    price_forecast = model.predict([latest_features])[0]
    current_price = feature_matrix.iloc[-1]['price']
    
    # Decision logic
    if price_forecast < current_price * 0.85:
        action = "CHARGE"
        confidence = 0.92
    elif price_forecast > current_price * 1.15:
        action = "DISCHARGE"
        confidence = 0.88
    else:
        action = "HOLD"
        confidence = 0.75
    
    recommendation = {
        'action': action,
        'confidence': confidence,
        'price_forecast': float(price_forecast),
        'current_price': float(current_price),
        'factors': ['price_trend', 'volatility_24h', 'solar_generation_kw'],
        'timestamp': datetime.utcnow().isoformat()
    }
    
    context.log.info(f"Recommendation: {action} (confidence: {confidence})")
    return Output(recommendation, metadata=recommendation)

@asset
def model_performance(context, feature_matrix: pd.DataFrame):
    """Monitor model performance and trigger retraining if accuracy drops"""
    
    # Calculate actual vs predicted
    predictions = feature_matrix['price_predicted']
    actuals = feature_matrix['price']
    
    mae = (predictions - actuals).abs().mean()
    rmse = ((predictions - actuals) ** 2).mean() ** 0.5
    mape = ((predictions - actuals).abs() / actuals).mean()
    
    context.log.info(f"Model performance - MAE: {mae:.2f}, RMSE: {rmse:.2f}, MAPE: {mape:.2%}")
    
    # Alert if performance degrades
    if mape > 0.15:  # >15% error
        context.log.warning("Model accuracy degraded - recommend retraining")
    
    return {
        'mae': float(mae),
        'rmse': float(rmse),
        'mape': float(mape),
        'timestamp': datetime.utcnow().isoformat()
    }
```

---

## 🔗 Lineage & Tracking

**Dagster automatically tracks:**

1. **Data Lineage**
   - Weather API → Solar Irradiance → Generation Features → Feature Matrix → XGBoost Model → Recommendation
   - Know exactly which data fed each prediction

2. **Asset Versioning**
   - Each asset materialization is versioned with timestamp
   - Can rollback to previous versions

3. **Dependency Tracking**
   - If weather data updates → automatically trigger dependent assets
   - If strategy parameters change → trigger feature recomputation

4. **Metadata**
   - Store metadata with each asset (rows, quality metrics, timestamp)
   - Query in Dagster UI

---

## 📈 Integration with Dashboard

### API Layer (Express/Nuxt)
```typescript
// server/api/dagster/recommendation.ts
export default eventHandler(async (event) => {
  // Query Dagster for latest recommendation asset
  const response = await fetch('http://localhost:3500/api/graphql', {
    method: 'POST',
    body: JSON.stringify({
      query: `{ assetMaterializations(assetKey: "current_recommendation", limit: 1) { ... } }`
    })
  })
  
  const { data } = await response.json()
  return data.recommendation
})
```

### Dashboard Widget
```vue
<template>
  <div class="recommendation-card">
    <h3>ML Recommendation</h3>
    <p class="action">{{ recommendation.action }}</p>
    <p class="confidence">Confidence: {{ recommendation.confidence }}%</p>
    <p class="factors">Factors: {{ recommendation.factors.join(', ') }}</p>
    <p class="timestamp">{{ recommendation.timestamp }}</p>
    
    <!-- Lineage visualization -->
    <div class="lineage">
      <p>Lineage:</p>
      <code>Weather API → Solar Gen → Features → XGBoost → {{ recommendation.action }}</code>
    </div>
  </div>
</template>
```

---

## 🚀 Full Execution Timeline

### Phase 3A (Today): Dagster Foundation
- Task 1: Dagster project setup (30 min)
- Task 2: Data source assets (45 min)
- Task 3: Feature engineering assets (60 min)
- Task 4: Resources setup (30 min)
- Task 5: Define job (30 min)
- Task 6: Definitions (20 min)
- Task 7: Launch UI (10 min)

**Total:** 4-5 hours

### Phase 3B: Advanced Features
- NVTabular GPU workflows (60 min)
- Optuna hyperparameter tuning (60 min)
- XGBoost/River models (60 min)
- Featuretools deep synthesis (30 min)

**Total:** 3-4 hours

### Phase 3C: Integration & Monitoring
- Recommendation API (30 min)
- Model performance monitoring (30 min)
- Dashboard integration (45 min)
- Testing & deployment (30 min)

**Total:** 2-3 hours

---

## 🎯 Success Criteria

✅ **Dagster UI shows:**
- All assets with lineage graph
- Daily job running without errors
- Asset versions tracked
- Metadata visible for each materialization

✅ **Recommendations show:**
- Action (CHARGE/DISCHARGE/HOLD)
- Confidence score (0-100%)
- List of factors that drove decision
- Full lineage (which data led to this recommendation)

✅ **Performance:**
- Feature engineering < 2 seconds (with NVTabular GPU)
- Model training < 30 seconds (Dask distributed)
- Recommendation generation < 500ms
- Dask scales to 1000s of users without code change

---

## 📚 Key Advantages of This Stack

| Feature | Benefit |
|---------|---------|
| **Dagster** | Full lineage tracking, automatic recomputation, versioning |
| **Dask** | Scales to 1000s of clients without code rewrite |
| **NVTabular** | GPU acceleration (100x faster feature engineering) |
| **Featuretools** | Discovers complex feature relationships automatically |
| **Optuna** | Finds optimal strategy parameters for maximum profit |
| **XGBoost/River** | Hybrid: batch predictions + online learning for real-time |

---

**Ready to execute Phase 3A with this architecture?**

