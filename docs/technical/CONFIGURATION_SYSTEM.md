# ⚙️ Configuration System Documentation

**Date:** 2026-01-29
**Feature:** Runtime Configuration Management
**Status:** ✅ COMPLETE

---

## Overview

The system now has a complete **configuration management system** that allows you to:
- ✅ View all system constants in one place
- ✅ Modify any constant at runtime (no code changes!)
- ✅ Save configuration changes
- ✅ Retrain models with new configuration
- ✅ Track configuration history

All without touching a single line of code.

---

## Architecture

### 1. Configuration Backend (`src/config.py`)

**SystemConfig Class:**
- Manages all constants
- Loads/saves from JSON
- Provides getter/setter with dot notation
- Validates changes
- Tracks defaults

**Global Instance:**
```python
from src.config import get_config
config = get_config()  # Returns singleton instance
```

### 2. Streamlit Frontend (`app_config.py`)

**4-Page Dashboard:**
1. **Current Configuration** - View all values
2. **Edit Configuration** - Modify and save
3. **Train Model** - Retrain with new config
4. **Training Results** - View history

### 3. Integration Points

**RL Environment (`src/rl_environment.py`):**
```python
from src.config import get_config

env = SmartEnergyEnv(weather, prices, config=get_config())
```

**Training Script (`src/train_baseline.py`):**
- Reads config before training
- Uses config values for model
- Saves config metadata after training

---

## Configuration Structure

### All Available Constants

```
BATTERY
├── capacity_kwh (default: 150)
├── min_soc_percent (default: 10)
├── max_soc_percent (default: 95)
├── charge_efficiency (default: 0.95)
└── discharge_efficiency (default: 0.95)

SOLAR
├── installed_capacity_kw (default: 20)
├── panel_efficiency (default: 0.20)
└── inverter_efficiency (default: 0.95)

GRID
├── max_import_power_kw (default: 100)
└── max_export_power_kw (default: 50)

DIESEL_GENERATOR
├── capacity_kw (default: 50)
└── fuel_cost_eur_per_kwh (default: 0.25)

TRAINING
├── learning_rate (default: 0.0003)
├── gamma (default: 0.99)
├── batch_size (default: 64)
├── episodes (default: 100)
└── timesteps_per_episode (default: 24)

OPTIMIZER
├── cheap_price_threshold_eur (default: 3.0)
├── expensive_price_threshold_eur (default: 8.0)
├── low_battery_threshold (default: 0.2)
└── high_battery_threshold (default: 0.9)
```

---

## Usage Guide

### Method 1: Command Line (View Config)

```bash
# Display all constants formatted
python src/config.py
```

Output:
```
════════════════════════════════════════════════════════════
SYSTEM CONFIGURATION
════════════════════════════════════════════════════════════

📋 BATTERY
────────────────────────────────────────
  capacity_kwh.................. 150
  min_soc_percent............... 10
  ...
```

### Method 2: Python API

```python
from src.config import get_config

# Get config instance
config = get_config()

# View a value
capacity = config.get('battery.capacity_kwh')
print(f"Battery: {capacity} kWh")  # Battery: 150 kWh

# Modify a value
config.set('battery.capacity_kwh', 300)

# Save to file
config.save_config()

# Get entire section
battery_cfg = config.get_battery_config()
print(battery_cfg)
# Output: {'capacity_kwh': 300, 'min_soc': 0.1, ...}

# Reset to defaults
config.reset_to_defaults()
```

### Method 3: Streamlit Dashboard (Recommended!)

```bash
streamlit run app_config.py
```

Then:
1. **View** → "Current Configuration" tab
2. **Edit** → "Edit Configuration" tab
3. **Train** → "Train Model" tab
4. **Results** → "Training Results" tab

---

## Common Tasks

### Task 1: Increase Battery Capacity

**Via Dashboard:**
1. Go to "Edit Configuration"
2. Find "Battery Capacity (kWh)"
3. Change 150 → 300
4. Click "Save Configuration"
5. Go to "Train Model" → Click "START TRAINING"

**Via Python:**
```python
config = get_config()
config.set('battery.capacity_kwh', 300)
config.save_config()

# Then retrain (e.g., from RL environment)
from src.train_baseline import train_baseline_with_real_data
train_baseline_with_real_data()
```

### Task 2: Adjust Solar Capacity

**Via Dashboard:**
1. Edit Configuration
2. "Solar Installed Capacity (kW)" 
3. Change 20 → 50 kW
4. Save → Train Model

**Via Python:**
```python
config.set('solar.installed_capacity_kw', 50)
config.save_config()
```

### Task 3: Change Price Thresholds

**Via Dashboard:**
1. Edit Configuration
2. "Cheap Price Threshold" → 2.0 €/MWh
3. "Expensive Price Threshold" → 10.0 €/MWh
4. Save → Train

**Via Python:**
```python
config.set('optimizer.cheap_price_threshold_eur', 2.0)
config.set('optimizer.expensive_price_threshold_eur', 10.0)
config.save_config()
```

### Task 4: Download Current Configuration

**Via Dashboard:**
1. Current Configuration tab
2. Click "📥 Download Config"
3. Saves as `system_config_YYYYMMDD_HHMMSS.json`

---

## Configuration File

### Location
```
config/system_config.json
```

### Format
```json
{
  "battery": {
    "capacity_kwh": 150,
    "min_soc_percent": 10,
    "max_soc_percent": 95,
    "charge_efficiency": 0.95,
    "discharge_efficiency": 0.95,
    "min_soc": 0.1,
    "max_soc": 0.95
  },
  "solar": {
    "installed_capacity_kw": 20,
    "panel_efficiency": 0.20,
    "inverter_efficiency": 0.95
  },
  "grid": {
    "max_import_power_kw": 100,
    "max_export_power_kw": 50
  },
  "diesel_generator": {
    "capacity_kw": 50,
    "fuel_cost_eur_per_kwh": 0.25
  },
  "training": {
    "learning_rate": 0.0003,
    "gamma": 0.99,
    "batch_size": 64,
    "episodes": 100,
    "timesteps_per_episode": 24
  },
  "optimizer": {
    "cheap_price_threshold_eur": 3.0,
    "expensive_price_threshold_eur": 8.0,
    "low_battery_threshold": 0.2,
    "high_battery_threshold": 0.9
  }
}
```

---

## Workflow: Edit Config → Retrain → See Results

### Step 1: View Current Config
```bash
streamlit run app_config.py
```
- Go to "Current Configuration"
- See all values

### Step 2: Edit Configuration
1. Go to "Edit Configuration"
2. Modify values using sliders/inputs
3. Click "💾 Save Configuration"
4. See confirmation: "✅ Configuration saved successfully!"

### Step 3: Train Model with New Config
1. Go to "Train Model"
2. See "Current Configuration Used" section
3. Click "▶️ START TRAINING"
4. Watch progress bar
5. See "✅ Training completed successfully!"

### Step 4: View Training Results
1. Go to "Training Results"
2. See:
   - Training timestamp
   - Configuration that was used
   - Status (success/failed)

### Step 5: Download Config
1. Back to "Current Configuration"
2. Click "📥 Download Config"
3. File saved: `system_config_20260129_173000.json`

---

## Integration with RL Environment

### Using Config in Custom Code

```python
from src.config import get_config
from src.rl_environment import SmartEnergyEnv
from src.data_pipeline.ingest_weather import WeatherIngester
from src.data_pipeline.ingest_prices import PriceIngester

# Get config
config = get_config()

# Print what's configured
print(f"Battery: {config.get('battery.capacity_kwh')} kWh")
print(f"Solar: {config.get('solar.installed_capacity_kw')} kW")

# Create environment with config
weather = WeatherIngester().fetch_weather()
prices = PriceIngester().fetch_oree_prices()

env = SmartEnergyEnv(weather, prices, config=config)

# Train with config-based environment
state = env.reset()
for _ in range(24):
    action = env.action_space.sample()
    state, reward, done, info = env.step(action)
    if done:
        break

# Environment automatically uses:
# - Battery capacity from config
# - Solar specs from config
# - Grid limits from config
```

---

## API Reference

### SystemConfig Class

**Methods:**

```python
# Loading/Saving
config.load_config()          # Load from file
config.save_config()          # Save to file
config.reset_to_defaults()    # Reset all values

# Getting Values
config.get('battery.capacity_kwh')        # Get single value
config.get_battery_config()               # Get all battery values
config.get_solar_config()                 # Get all solar values
config.get_grid_config()                  # Get all grid values
config.get_training_config()              # Get all training values
config.get_optimizer_config()             # Get all optimizer values
config.to_dict()                          # Get entire config as dict

# Setting Values
config.set('battery.capacity_kwh', 300)   # Set single value

# Utilities
config.display_summary()                  # Formatted string of all values
```

### Global Function

```python
from src.config import get_config

config = get_config()  # Returns singleton SystemConfig instance
```

---

## Testing

### View Current Configuration
```python
from src.config import get_config

config = get_config()
print(config.display_summary())
```

### Modify and Save
```python
config = get_config()
config.set('battery.capacity_kwh', 200)
config.save_config()

# Verify
print(config.get('battery.capacity_kwh'))  # Output: 200
```

### Reset to Defaults
```python
config.reset_to_defaults()
print(config.get('battery.capacity_kwh'))  # Output: 150
```

---

## Benefits

✅ **No Code Changes** - Modify config without editing code
✅ **Runtime Updates** - Change values and retrain immediately
✅ **Versioning** - Download/save different configurations
✅ **A/B Testing** - Test different settings easily
✅ **Non-Technical Access** - Streamlit UI for anyone
✅ **History Tracking** - Know what config was used for each training
✅ **Defaults Provided** - Never missing a value
✅ **Easy Validation** - Sliders prevent invalid values

---

## Next Steps

**Recommended Actions:**
1. ✅ Start Streamlit dashboard: `streamlit run app_config.py`
2. ✅ View current config
3. ✅ Edit battery capacity (try 200 kWh)
4. ✅ Save configuration
5. ✅ Go to "Train Model" and retrain
6. ✅ See new results!

---

**Configuration System Complete & Ready to Use!** 🎉

No more hardcoded constants. Everything is configurable.
