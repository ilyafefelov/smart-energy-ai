## WEEK 2 PLANNING - RL AGENT + AIRFLOW

**Timeline:** Days 8-14 (2026-01-30 to 2026-02-05)
**Owner:** Illya F + Cloud
**Deliverables:** RL environment, trained agent, Airflow DAG

---

## What We Have From Week 1

✅ **Data Pipeline (Production Ready)**
- PostgreSQL ORM models
- Open-Meteo weather API integration
- OREE price API integration
- Pydantic validation layer
- 7-day sample training data (168 hours)

✅ **Testing (96% passing)**
- 25 unit tests
- Full validation coverage
- API integration tests
- Batch processing tests

✅ **Infrastructure**
- Database schema ready
- Connection pooling
- Error handling
- Logging setup

---

## Week 2 Goals

### Goal 1: Build RL Environment (Days 8-10)
**Input:** 7-day sample data from Week 1
**Output:** Gym environment ready for training

Create `src/rl_environment.py`:
- OpenAI Gym environment wrapper
- State: [temperature, solar_radiation, cloudcover, market_price, battery_soc]
- Actions: [charge_rate, discharge_rate, buy_grid, sell_grid]
- Reward: -cost_per_hour (minimize electricity cost)
- Episode: 24-hour day (24 steps)

### Goal 2: Train PPO Agent (Days 10-12)
**Input:** RL environment + sample data
**Output:** Trained RL model checkpoint

Create `src/rl_training.py`:
- Stable-Baselines3 PPO agent
- Training on 7-day data (multiple episodes)
- Validation on same data
- Save trained model to `models/ppo_agent.zip`

### Goal 3: Create Airflow DAG (Days 12-14)
**Input:** Trained model + APIs
**Output:** Operational daily automation

Create `dags/smart_energy_dag.py`:
- Daily schedule (runs at 00:00 GMT+2)
- Fetch weather (Open-Meteo)
- Fetch prices (OREE)
- Load trained RL model
- Generate 24-hour actions
- Log predictions to database
- Send summary to Telegram

---

## Week 2 Deliverables

### Code (3 New Modules)
- `src/rl_environment.py` - Gym environment definition
- `src/rl_training.py` - Training script with validation
- `dags/smart_energy_dag.py` - Airflow DAG

### Models
- `models/ppo_agent.zip` - Trained RL model

### Tests
- `tests/test_rl_environment.py` - Environment tests
- `tests/test_training.py` - Training validation

### Documentation
- RL environment design doc
- Training results summary
- DAG configuration guide

### Data
- 24-hour predictions (sample)
- Model performance metrics
- Comparison: baseline vs RL

---

## RL Environment Details

**State Space (5-dimensional):**
```python
state = [
    temperature,           # -50 to +50 °C
    solar_radiation,       # 0 to 2000 W/m²
    cloudcover,           # 0 to 100 %
    market_price,         # 0.5 to 20 EUR/MWh
    battery_soc           # 0 to 100 %
]
```

**Action Space (4-dimensional, continuous):**
```python
action = [
    charge_rate,          # 0 to 150 kW (battery charging)
    discharge_rate,       # 0 to 150 kW (battery discharging)
    grid_buy,            # 0 to 100 kW (buy from grid)
    grid_sell            # 0 to 50 kW (sell to grid)
]
```

**Reward Function:**
```python
reward = -hourly_cost
# Minimize: (grid_buy * market_price) - (grid_sell * market_price * 0.9)
# Maximize: solar usage, battery discharge at peak prices
```

**Episode:**
- 24 steps (one per hour)
- Terminates after 24 hours
- Resets to next day

---

## Training Details

**Hyperparameters (Stable-Baselines3 PPO):**
- Policy: MlpPolicy (neural network)
- Learning rate: 3e-4
- N steps: 2048
- Batch size: 64
- Epochs: 20
- Clip range: 0.2

**Training Data:**
- Episodes: 7 days × multiple seeds = ~10 episodes
- Total timesteps: 10 × 24 = 240 timesteps
- Validation: same 7-day window (overfitting check)

**Expected Performance:**
- Baseline (random): -500 EUR/week
- Expected RL: -350 EUR/week (~30% improvement)
- Peak improvement: night charging at cheap prices, selling at peak

---

## Airflow DAG Schedule

**Trigger:** Daily at 00:00 GMT+2 (midnight)

**Tasks:**
1. fetch_weather - Get 24-hour forecast
2. fetch_prices - Get hourly prices
3. load_model - Load trained RL model
4. generate_actions - Run 24-hour prediction
5. store_predictions - Save to database
6. notify_user - Send summary to Telegram

**Example Output (Telegram):**
```
🤖 Smart Energy RL Optimization

Today's Forecast:
Temperature: -2°C
Solar: Low (20% capacity)
Prices: Peak at 17:00 (12.5 EUR/MWh)

Recommended Actions:
⏱️ 06:00-10:00: Charge battery (cheap prices)
☀️ 10:00-14:00: Use solar (peak generation)
💰 17:00-21:00: Discharge battery (peak prices)
🔌 22:00-06:00: Charge battery (lowest prices)

Expected Savings: 45 EUR today
```

---

## Success Criteria

✅ Week 2 Complete When:
- [ ] RL environment builds without errors
- [ ] Environment tests passing (full action/state space)
- [ ] Model trains for 100+ timesteps
- [ ] Training curves show improvement
- [ ] DAG successfully runs daily
- [ ] Predictions generated for 24 hours
- [ ] Comparison plot: baseline vs RL
- [ ] Documentation complete

---

## Schedule

**Days 8-10 (Thu-Sat):**
- Build Gym environment
- Write environment tests
- Validate action/state spaces

**Days 10-12 (Sat-Mon):**
- Create training script
- Train on 7-day data
- Validate model performance

**Days 12-14 (Mon-Wed):**
- Create Airflow DAG
- Test daily schedule
- Deploy to production
- Create performance graphs

**By Day 14:** Ready for Week 3 (testing + presentation)

---

## Known Risks & Mitigation

| Risk | Impact | Mitigation |
|------|--------|-----------|
| RL training unstable | Model fails | Use pre-tuned hyperparams, start simple |
| Airflow setup complex | DAG doesn't run | Test locally first, then airflow-standalone |
| Insufficient data | Model overfits | Use data augmentation, cross-validation |
| API failures | Missing data | Implement fallback to cached data |

---

## Next Action

**Start with:** Build `src/rl_environment.py`
- Define state/action spaces
- Implement step() and reset() methods
- Test with dummy episode

**Then:** Write tests to validate environment
**Then:** Create training script
**Finally:** Airflow DAG integration

Ready to begin Week 2! 🚀
