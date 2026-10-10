# Smart Energy AI - Code Wiki

## Architecture Overview

```
smart-energy-ai/
├── app.py                          # Streamlit app entry
├── pages/
│   ├── 0_dashboard.py             # Main dashboard
│   └── 1_configuration.py          # Settings & training
├── src/
│   ├── enhanced_config.py          # Config & version mgmt
│   ├── oree_fixed_scraper.py      # OREE price scraper
│   ├── solar_data.py               # Solar forecasting
│   ├── enhanced_rl_trainer.py     # RL training engine
│   └── price_fallback.py           # Fallback data
├── config/                         # User configs & versions
├── models/                         # Trained models
└── checkpoints/                    # Training checkpoints
```

## Key Code Paths

### 1. Price Data Flow
```
OREE Website
    ↓
OREEEffectiveScraper.fetch_today_prices()
    ↓
DataFrame [hour, price_eur_mwh, price_uah_mwh]
    ↓
Dashboard Chart
    ↓
AI Recommendation Logic
```

### 2. Training Flow
```
User clicks "Train Model"
    ↓
EnhancedRLTrainer.train(episodes=N)
    ↓
PPO Algorithm (N episodes)
    ↓
EnhancedConfig.increment_version()
    ↓
Save model + log metrics
    ↓
Dashboard updates version
```

### 3. Solar Data Flow
```
OpenWeatherMap API
    ↓
SolarDataFetcher.get_current_irradiance()
    ↓
Calculate generation potential
    ↓
Dashboard solar chart
    ↓
Used in optimization
```

## Critical Functions

### src/oree_fixed_scraper.py
- `fetch_today_prices()` - Main scraper, returns 24-hour prices
- `_convert_to_dataframe()` - Formats extracted data

**Key Detail:** Prices are in UAH, divide by 35 for EUR

### src/solar_data.py
- `get_current_irradiance()` - Real-time data
- `get_24h_forecast()` - Daily forecast
- `get_7d_forecast()` - Weekly forecast

**Key Detail:** Uses OpenWeatherMap, graceful fallback on API failure

### src/enhanced_rl_trainer.py
- `train(episodes, learning_rate)` - Train model
- Auto-increments version on success
- Logs all metrics

**Key Detail:** Trains fast (~3min for 50 episodes)

### pages/0_dashboard.py
- Displays all real data
- Shows AI recommendations
- Renders price + solar charts
- Shows version history

**Performance:** <1s load time

### pages/1_configuration.py
- Profile management UI
- Hardware settings
- Training controls
- Model management

## Important Constants

```python
# OREE conversion (UAH to EUR)
EUR_RATE = 35  # 1 EUR = 35 UAH

# Thresholds (default, user-configurable)
CHEAP_THRESHOLD = 1.5   # EUR/MWh
EXPENSIVE_THRESHOLD = 13.0  # EUR/MWh

# Cache TTLs
PRICE_CACHE_TTL = 300   # 5 minutes
SOLAR_CACHE_TTL = 60    # 1 minute

# Training
DEFAULT_EPISODES = 50
DEFAULT_LR = 0.0003
GAMMA = 0.99
```

## Testing

Run all tests:
```bash
python test_complete_system.py
```

Individual modules:
```bash
python -m src.oree_fixed_scraper      # Test OREE scraper
python -m src.solar_data              # Test solar data
python test_enhanced_training.py      # Test RL training
```

## Common Issues & Fixes

### Issue: Playwright browser won't launch
- Fix: `playwright install chromium`
- Windows-specific: Use correct Poetry venv

### Issue: OREE prices missing
- Check: Website might be down
- Fallback: Auto-switches to sample data
- Monitor: Check dashboard logs

### Issue: Solar data unavailable
- Check: OpenWeatherMap API key
- Fallback: Returns zero irradiance
- Monitor: Check config for API key

### Issue: Training too slow
- Reduce episodes parameter
- Check: No other heavy processes
- Monitor: System RAM usage

## Code Style

- Python 3.8+
- PEP 8 compliant
- Type hints where applicable
- Docstrings on all public functions
- Logging at INFO level for user info

## Contributing

1. Create feature branch
2. Make changes
3. Run tests (must pass)
4. Create PR with description
5. Code review required
6. Merge to main

## Performance Targets

- Dashboard load: <1s ✅
- Price fetch: <0.5s ✅
- Solar fetch: <0.2s ✅
- Training: <5min for 100 episodes ✅
- Memory usage: <500MB ✅
