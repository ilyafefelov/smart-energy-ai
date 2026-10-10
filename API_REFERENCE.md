# Smart Energy AI - API Reference

## Core Classes

### OREEEffectiveScraper
```python
from src.oree_fixed_scraper import OREEEffectiveScraper

scraper = OREEEffectiveScraper(use_cache=True)
prices_df = scraper.fetch_today_prices()
# Returns: DataFrame with columns [hour, timestamp, price_eur_mwh, price_uah_mwh, source]
```

### SolarDataFetcher
```python
from src.solar_data import SolarDataFetcher

fetcher = SolarDataFetcher()
irradiance = fetcher.get_current_irradiance()  # W/m²
forecast_24h = fetcher.get_24h_forecast()      # DataFrame
forecast_7d = fetcher.get_7d_forecast()        # DataFrame
```

### SmartEnergyEnv & PPOTrainer
```python
from src.enhanced_rl_trainer import PPOTrainer

trainer = PPOTrainer()
trainer.train(episodes=100, learning_rate=0.0003)
# Auto-increments version, logs metrics, saves model
```

### EnhancedConfig
```python
from src.enhanced_config import get_config

config = get_config()
version = config.get_current_version()  # "1.0.3"
config.increment_version()              # Now "1.0.4"
```

## Data Formats

### Price DataFrame
```
hour    timestamp           price_eur_mwh  price_uah_mwh  source
0       2026-01-29 00:00   157.14         5500           oree_live
1       2026-01-29 01:00   154.29         5400           oree_live
...
```

### Solar Irradiance
```
W/m² (range: 0-1000 typical)
Daily peak: 10:00-16:00 hours
```

### Version Info
```json
{
  "current_version": "1.0.3",
  "last_trained": "2026-01-29 19:15:00",
  "total_trainings": 3,
  "training_history": [
    {"version": "1.0.1", "timestamp": "...", "episodes": 50},
    {"version": "1.0.2", "timestamp": "...", "episodes": 100},
    {"version": "1.0.3", "timestamp": "...", "episodes": 75}
  ]
}
```

## Configuration Files

### config/profiles/my_system.json
```json
{
  "name": "my_system",
  "hardware": {
    "battery_capacity_kwh": 15.0,
    "solar_panels_kw": 8.0,
    "grid_export_allowed": true
  },
  "optimizer": {
    "cheap_price_threshold_eur": 1.5,
    "expensive_price_threshold_eur": 13.0
  }
}
```

### config/version.json
Auto-managed, tracks version history and training metrics

## Environment Variables

- `OPENWEATHERMAP_API_KEY` - Required for solar data
- `NOTION_API_KEY` - Optional, for documentation
- `DEBUG` - Optional, for verbose logging
