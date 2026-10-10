# 🚀 QUICK START GUIDE - Smart Energy AI System

## Start the Streamlit App

```bash
cd C:\Users\ilyaf\clawd\projects\smart-energy-ai
streamlit run app.py
```

The dashboard will open at: `http://localhost:8501`

---

## 📊 Dashboard Features

### Main Dashboard (page 0_dashboard.py)

1. **Model Version Display**
   - Shows current AI model version (e.g., v1.0.2)
   - Shows last training date

2. **Current Market Conditions**
   - 💶 Current Price (EUR/MWh and UAH)
   - 📊 Daily Average Price
   - ☀️ Solar Irradiance (W/m²)
   - 📈 Estimated Solar Generation (kW)

3. **24-Hour Price Forecast**
   - Interactive price chart
   - Green threshold line (cheap, typically €3/MWh)
   - Red threshold line (expensive, typically €8/MWh)

4. **24-Hour Solar Generation**
   - Bar chart showing expected solar output per hour
   - Peak generation typically 12:00-14:00

5. **AI Recommendations**
   - 💚 **CHARGE** when price < €3/MWh
   - ❤️ **DISCHARGE** when price > €8/MWh
   - 🟡 **HOLD** when price is average

6. **Model Version History**
   - Shows all trained versions
   - Training date, episodes, rewards, time

---

## ⚙️ Configuration Page

### User Profiles
Create different system configurations:
- Small residential (50 kWh battery, 5 kW solar)
- Large residential (150 kWh battery, 20 kW solar)
- Industrial small (500 kWh battery, 100 kW solar)

### Retraining UI
1. Set number of episodes (10-500)
2. Select learning rate
3. Click "START TRAINING"
4. Watch progress bar in real-time
5. See results with metrics

### Solar Configuration
- Location: Kyiv, Ukraine (50.45°N, 30.52°E)
- Panel efficiency: 18-22%
- System capacity: customizable per profile

### Optimizer Thresholds
- Cheap price: € below this = CHARGE
- Expensive price: € above this = DISCHARGE
- Battery thresholds: low/high SOC limits

### Version History
View all trained models:
- Version number
- Training date
- Episodes trained
- Rewards (average & best)
- Training duration

---

## 🤖 Training Your Model

### Quick Train (50 episodes)
```python
from src.enhanced_rl_trainer import EnhancedRLTrainer
from src.enhanced_config import get_config
import pandas as pd

# Load data
weather = pd.read_csv("data.csv")
prices = pd.read_csv("prices.csv")

# Train
config = get_config()
trainer = EnhancedRLTrainer(weather, prices, config)
result = trainer.train(episodes=50)

# Result:
# {
#   'version': '1.0.3',
#   'episodes': 50,
#   'avg_reward': -75.42,
#   'best_reward': -20.15,
#   'training_time_seconds': 0.15,
#   'model_path': 'config/models/ppo_v1.0.3_...'
# }
```

### Check Training History
```python
from src.enhanced_config import get_config

config = get_config()
history = config.get_version_history()

for v in history[:5]:  # Last 5 versions
    print(f"v{v.version}: {v.episodes} ep, avg={v.avg_reward:.0f}")
```

---

## ☀️ Solar Data Features

### Get Current Solar
```python
from src.solar_data import get_solar_fetcher

fetcher = get_solar_fetcher()
current = fetcher.get_current_solar_irradiance()

print(f"Irradiance: {current['irradiance_w_m2']:.0f} W/m²")
print(f"Cloud cover: {current['cloudcover_percent']:.0f}%")
print(f"Temperature: {current['temperature']:.1f}°C")
```

### 24-Hour Forecast
```python
forecast = fetcher.get_hourly_forecast_24h()

for row in forecast.iterrows():
    hour = row[1]['hour']
    gen = row[1]['generation_forecast_kw']
    print(f"Hour {hour:02d}: {gen:.2f} kW")
```

### 7-Day Forecast
```python
weekly = fetcher.get_daily_forecast_7d()

total = weekly['daily_total_kwh'].sum()
print(f"Weekly total: {total:.0f} kWh")
```

---

## 📝 Typical Workflow

### Day 1: Setup
1. Open dashboard
2. Check model version
3. View current prices
4. See solar forecast

### Day 1-3: Monitor
1. Daily check market conditions
2. Track AI recommendations
3. Monitor solar generation

### Week 1: Retrain
1. Go to Configuration page
2. Set episodes to 100
3. Click "START TRAINING"
4. Wait for completion
5. Check new version (e.g., 1.0.3)

### Ongoing: Optimization
1. Monthly retraining
2. Track reward improvements
3. Adjust thresholds as needed
4. Monitor performance metrics

---

## 🔍 Troubleshooting

### Dashboard Won't Load
```bash
# Check dependencies
pip install streamlit plotly pandas numpy

# Restart
streamlit run app.py
```

### No Solar Data
- System uses fallback synthetic data
- OpenWeatherMap is optional
- Forecasts will still work

### Training Too Slow
- Reduce episodes (start with 20)
- Check CPU usage
- Increase learning rate

### Price Data Missing
- OREE scraper may have issues
- System uses fallback data
- Check price_fallback.py

---

## 📊 API Endpoints Used

1. **OpenWeatherMap** (Free tier)
   - Solar irradiance data
   - Cloud cover
   - Temperature

2. **OREE** (Ukrainian Market)
   - Real-time electricity prices
   - Hourly forecasts

Both have fallback mechanisms if unavailable.

---

## 🎯 Key Metrics to Monitor

| Metric | Good Value | What It Means |
|--------|------------|---------------|
| Current Irradiance | >500 W/m² (daytime) | Good solar conditions |
| Cloud Cover | <50% | Clear skies |
| Current Price | <€3 | Cheap - good time to charge |
| Model Version | Latest | Recently trained |
| Avg Reward | >-50 | Good model performance |
| Training Time | <1 min | Fast training |

---

## 💡 Pro Tips

1. **Batch Training**: Train during low-activity hours (2-4 AM)
2. **Monitor History**: Watch avg_reward trend over versions
3. **Solar Peaks**: Most generation 11:00-15:00
4. **Price Patterns**: Night (2-4 AM) usually cheapest
5. **Version Control**: Keep 5-10 recent versions
6. **Configuration**: Adjust thresholds based on your data

---

## 📞 Support

For issues, check:
1. `COMPLETE_SYSTEM_REPORT.md` - Full documentation
2. `test_complete_system.py` - Run tests
3. Dashboard error messages
4. Configuration logs in `config/`

---

**Happy energy optimization! 🌞⚡**
