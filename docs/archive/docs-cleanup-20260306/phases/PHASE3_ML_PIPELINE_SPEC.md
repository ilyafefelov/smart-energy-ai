# Phase 3: ML Pipeline - Real-Time Data Integration & Recommendations

**Status:** ✅ Specification & Planning Complete  
**Target Duration:** 8-12 hours across 2-3 sessions  
**Start:** 2026-02-07 14:33 GMT+2  
**Branch:** `feature/ml-pipeline` (create new)

---

## 📋 Requirements Summary

### User Request (2026-02-07 14:33)
> "Incorporate scrapers on real-time price data, API weather for sun and wind (based on set location - Kyiv, Ukraine, default), incorporate them in ML pipeline with featuretools. Settings for solar and wind generation ability. Simulate discharge during set hours. ML system gives recommendations based on historical data, current data, future possible data, all weather, other factors. Preset scenarios: winter, max profit, max battery safer, max energy safe, blackout, etc. If any settings or user preference change, model must reflect this, retrain if needs be."

### Core Components Required

1. **Real-Time Data Sources**
   - ✅ Price scraper (OREE/Ukrainian energy market) - ACTIVE
   - 🆕 Weather API (OpenWeatherMap or NOAA) - Kyiv, Ukraine
   - 🆕 Solar irradiance forecasting
   - 🆕 Wind speed forecasting

2. **Feature Engineering (Featuretools)**
   - Time-based features (hour, day-of-week, season, holiday)
   - Weather features (temp, humidity, cloud cover, wind speed)
   - Energy market features (price trends, peak/off-peak cycles)
   - Solar generation potential (based on location, time, weather)
   - Wind generation potential (based on location, time, weather)
   - Battery state features (SOC, age, health)
   - Historical patterns (previous day, week, month)

3. **Settings & Configuration**
   - Solar generation capacity (kW) - user settable
   - Wind generation capacity (kW) - user settable
   - Battery capacity (kWh) - already settable
   - Discharge hours (schedule) - when to discharge
   - Location override (default: Kyiv, Ukraine)
   - Scenario selection (Winter, Max Profit, Max Safety, Energy Safe, Blackout)

4. **Recommendation Engine**
   - XGBoost model for price forecasting (already built)
   - Decision model: BUY/SELL/HOLD/DISCHARGE recommendations
   - Multi-objective optimization (profit vs. safety vs. energy)
   - Scenario-based constraints (different goals for each scenario)

5. **Automatic Retraining**
   - Trigger on settings change (solar/wind capacity, discharge hours, scenario)
   - Trigger on user preference change
   - Scheduled retraining (daily, if enough new data)
   - Version tracking (model versioning for rollback)

6. **Preset Scenarios**
   - **Winter:** Prioritize battery preservation, minimize discharge
   - **Max Profit:** Maximize arbitrage opportunities, high trading frequency
   - **Max Safety:** Keep battery above 60%, conservative trading
   - **Energy Safe:** Ensure 24h self-sufficiency, prioritize generation storage
   - **Blackout:** Emergency mode, discharge only when needed, maximize reserves

---

## 🏗️ Architecture

### Data Pipeline
```
OREE Price Scraper → Price Store (Redis/Memory)
OpenWeatherAPI → Weather Cache (6h TTL)
Solar Model → Generation Forecast
Wind Model → Generation Forecast
Battery State → Current SOC
User Settings → Feature Modifiers

        ↓ All feeds into ↓

Featuretools ETL Engine
        ↓
Feature Matrix (historical + current + forecasted)
        ↓
XGBoost Pricing Model
Decision Tree / MILP Optimizer
        ↓
Recommendation Engine
        ↓
Dashboard + API
```

### ML Pipeline Components

#### 1. Data Collection Layer
```typescript
// Location: server/api/data/
- prices/current.ts         // OREE (existing ✅)
- prices/historical.ts      // Daily price history
- weather/current.ts        // OpenWeatherAPI call
- weather/forecast.ts       // 5-day forecast
- solar/potential.ts        // Solar irradiance calculation
- wind/potential.ts         // Wind speed from weather
- battery/state.ts          // Current battery SOC
```

#### 2. Feature Engineering Layer
```typescript
// Location: server/ml/features/
- timeFeatures.ts           // Hour, day, season, etc.
- weatherFeatures.ts        // Temp, humidity, cloud cover
- priceFeatures.ts          // Trend, volatility, peak detection
- generationFeatures.ts     // Solar/wind potential + user capacity
- batteryFeatures.ts        // SOC, charge/discharge rate
- aggregator.ts             // Combine all into feature matrix
```

#### 3. Model Layer
```typescript
// Location: server/ml/models/
- priceForecaster.ts        // XGBoost (existing)
- decisionModel.ts          // Recommend BUY/SELL/HOLD
- scenarioWeights.ts        // Adjust recommendations by scenario
- optimizer.ts              // MILP for optimal schedule
```

#### 4. Recommendation Engine
```typescript
// Location: server/api/recommendations/
- current.ts                // Immediate action for next hour
- schedule24h.ts            // Full 24h plan
- rationale.ts              // Explain why (factors, confidence)
```

---

## 📊 Feature Matrix Specification

### Input Features (100+ total)

#### Time Features (5)
- `hour` (0-23)
- `dayOfWeek` (0-6)
- `isWeekend` (0-1)
- `season` (0-3: winter, spring, summer, fall)
- `isHoliday` (0-1)

#### Weather Features (12)
- `temp_current` (°C)
- `temp_forecast_1h, 3h, 6h, 12h, 24h`
- `humidity` (%)
- `cloudCover` (%)
- `windSpeed` (m/s)
- `windForecast_1h, 6h, 24h`

#### Price Features (15)
- `price_current` (₴/kWh)
- `price_forecast_1h, 3h, 6h, 12h, 24h`
- `priceChange_1h, 24h` (%)
- `priceVolatility_24h`
- `isPeakHour` (0-1)
- `isOffPeakHour` (0-1)
- `priceRank_percentile` (0-100)

#### Solar Generation Features (10)
- `solarIrradiance_current` (W/m²)
- `solarIrradiance_forecast_1h, 3h, 6h, 12h, 24h` (W/m²)
- `userSolarCapacity` (kW - from settings)
- `expectedSolarGen_current` (kW)
- `expectedSolarGen_1h_to_24h` (kW)

#### Wind Generation Features (8)
- `windSpeed` (m/s)
- `windForecast_1h, 3h, 6h, 12h, 24h`
- `userWindCapacity` (kW - from settings)
- `expectedWindGen_current` (kW)

#### Battery Features (10)
- `batterySOC` (%)
- `batteryCapacity` (kWh - from settings)
- `chargeRate_max` (kW - from settings)
- `dischargeRate_max` (kW - from settings)
- `dischargeSchedule_active` (0-1)
- `dischargeSchedule_hours` (e.g., [14, 15, 16, 17])
- `batteryHealth` (%)
- `timeToFullCharge` (hours)
- `timeToEmpty` (hours)
- `isScheduledForDischarge_nextHour` (0-1)

#### Historical Pattern Features (20)
- `avgPrice_lastDay, lastWeek, lastMonth`
- `avgPrice_sameDayLastWeek, lastMonth`
- `avgSolarGen_lastDay, lastWeek`
- `avgWindGen_lastDay, lastWeek`
- `volatility_1d, 7d, 30d`
- `priceRank_compare_lastWeek, lastMonth`

#### Scenario Features (5)
- `scenario_type` (encoded: 0=Winter, 1=MaxProfit, 2=MaxSafety, 3=EnergySafe, 4=Blackout)
- `scenario_profitWeight` (0-1)
- `scenario_safetyWeight` (0-1)
- `scenario_energyWeight` (0-1)
- `scenario_constraints` (bitmask)

#### Demand Features (8)
- `expectedLoad_current` (kW - if available)
- `expectedLoad_1h, 3h, 6h, 12h, 24h`
- `loadForecast_confidence`
- `demandTrend` (increasing/stable/decreasing)

---

## 🎯 Recommendation Logic

### Decision Matrix

**Input:** Feature matrix + current state + scenario

**Output:** Recommended action for next hour

```
IF price_forecast < price_threshold_low AND batterySOC < 90%:
  → CHARGE (if solar/wind available) OR BUY (if profitable)

IF price_forecast > price_threshold_high AND batterySOC > min_reserve:
  → DISCHARGE or SELL_TO_GRID

IF price_forecast ≈ current_price AND no_major_load:
  → HOLD

IF scenario == "Blackout":
  → Maximize reserve (don't discharge below 80%)
  → Store all available generation
  
IF scenario == "MaxProfit":
  → Trade aggressively
  → Use arbitrage windows
  
IF scenario == "EnergySafe":
  → Prioritize self-sufficiency
  → Store excess generation
  → Minimize grid dependency
```

### Confidence Scores
Each recommendation includes:
- `confidence` (0-100): How confident is the model?
- `factors` array: Which features drove this decision?
- `alternative` action: What if forecast is wrong?

---

## 🔧 Implementation Phases

### Phase 3A: Data Integration (3-4 hours)
**Goal:** Get real-time data flowing into the dashboard

- [ ] **Weather API integration**
  - Sign up for OpenWeatherMap API (free tier: 60/min)
  - Create `server/api/weather/current.ts` (fetch Kyiv weather)
  - Add 6-hour caching
  - Display on dashboard (current temp, wind, cloud cover)

- [ ] **Solar irradiance model**
  - Use location (Kyiv: 50.45°N, 30.52°E)
  - Calculate solar position (solar noon, sunrise/sunset)
  - Model irradiance based on time + cloud cover
  - Create `server/ml/features/solarModel.ts`

- [ ] **Wind model**
  - Use wind speed from weather API
  - Model generation potential based on wind curve
  - Create `server/ml/features/windModel.ts`

- [ ] **Settings schema update**
  - Add `solarCapacity` (kW) to settings store
  - Add `windCapacity` (kW) to settings store
  - Add `dischargeSchedule` (hours array) to settings
  - Add `location` override (default: Kyiv)
  - Add `scenario` selection (enum)

### Phase 3B: Feature Engineering (3-4 hours)
**Goal:** Build feature matrix for ML model

- [ ] **Featuretools integration**
  - Install featuretools Python package
  - Create `server/ml/featuretools/entityset.ts` (define entities)
  - Implement feature generation pipeline
  - Cache features for reuse

- [ ] **Feature aggregator**
  - Combine all data sources into single matrix
  - Handle missing/null values (imputation)
  - Normalize/scale features
  - Add scenario-based feature modifiers

- [ ] **Historical data aggregation**
  - Load 2 years of price history
  - Calculate rolling statistics (7d, 30d, 365d)
  - Pattern detection (peak hours, seasonal trends)

### Phase 3C: Model Training & Recommendations (2-3 hours)
**Goal:** Train decision model and serve recommendations

- [ ] **Decision model training**
  - Use XGBoost for binary classification (CHARGE vs DISCHARGE)
  - Multi-objective loss: profit + safety + reliability
  - Scenario-weighted objectives
  - Backtest on 6 months of data

- [ ] **Recommendation API**
  - Create `server/api/recommendations/current.ts`
  - Return: action, confidence, factors, rationale
  - Cache for 5 minutes (don't retrain constantly)

- [ ] **24h Schedule**
  - Create `server/api/recommendations/schedule24h.ts`
  - Return hourly recommendations
  - Include confidence intervals
  - Show cumulative profit/savings

### Phase 3D: Automatic Retraining (1-2 hours)
**Goal:** Keep model updated as settings change

- [ ] **Change detection**
  - Monitor settings store for changes
  - Detect: solar/wind capacity, discharge schedule, scenario

- [ ] **Incremental retraining**
  - When settings change: retrain with new constraints
  - When new data arrives (daily): update model
  - Version control: save model snapshots

- [ ] **Fallback strategy**
  - If training fails: use previous model
  - Log errors for debugging
  - Alert user if model is stale

---

## 📱 UI/UX Updates for Phase 3

### Dashboard Enhancements
```vue
<!-- New widgets -->
- Weather card (current + 24h forecast)
- Solar generation gauge (capacity + forecast)
- Wind generation gauge (capacity + forecast)
- Recommendation banner (action + confidence)
- 24h schedule chart (hourly recommendations)
```

### Settings Page Updates
```vue
<!-- New settings -->
- Solar Capacity (kW slider: 0-50)
- Wind Capacity (kW slider: 0-50)
- Discharge Schedule (time picker: hours to discharge)
- Location (select: default Kyiv, or custom)
- Scenario (select: Winter, MaxProfit, MaxSafety, EnergySafe, Blackout)
```

### New Pages/Features
- **Recommendations Page** - See current + 24h plan with rationale
- **Model Info Page** - Model version, training date, features used, confidence
- **Scenario Simulator** - Test different scenarios, see impact on savings

---

## 🚀 Quick Start Checklist

### Session 1 (Today - Phase 3A: Data Integration)
- [ ] Create feature branch `feature/ml-pipeline`
- [ ] Set up OpenWeatherMap API account + key
- [ ] Build weather API integration
- [ ] Build solar irradiance model
- [ ] Build wind generation model
- [ ] Update settings schema (solar/wind/discharge/scenario)
- [ ] Display weather + generation on dashboard
- **Commit:** "feat: Real-time weather and generation data integration"

### Session 2 (Phase 3B: Feature Engineering)
- [ ] Integrate Featuretools
- [ ] Build feature matrix aggregator
- [ ] Backfill historical features from 2-year price history
- [ ] Create feature cache layer
- **Commit:** "feat: Featuretools feature engineering pipeline"

### Session 3 (Phase 3C & D: ML & Retraining)
- [ ] Train decision model (BUY/SELL/HOLD)
- [ ] Build recommendation API
- [ ] Implement 24h schedule generation
- [ ] Build change detection + retraining logic
- **Commit:** "feat: ML recommendation engine with auto-retraining"

---

## 🎯 Success Criteria

✅ **Phase 3A Complete:**
- Dashboard shows real-time weather (temp, wind, cloud cover)
- Solar/wind generation capacity from settings
- Estimated generation displayed
- Settings page allows changing all parameters

✅ **Phase 3B Complete:**
- Feature matrix builds with 100+ features
- No missing values in feature data
- Historical patterns extracted and visible
- Model can be trained on full feature set

✅ **Phase 3C Complete:**
- Recommendation API returns action + confidence
- 24h schedule shows hourly recommendations
- Rationale explains which features drove decision
- All scenarios implemented and testable

✅ **Phase 3D Complete:**
- Changing settings triggers automatic retraining
- User sees model version + training date
- Model fallback works if training fails
- No service interruption during retraining

---

## 📚 References & Dependencies

### Python Libraries Needed
```
featuretools==1.27.0
xgboost==2.1.0
scikit-learn==1.4.1
pandas==2.1.3
numpy==1.24.3
requests==2.31.0          # For weather API
python-dateutil==2.8.2
joblib==1.3.2             # Model serialization
```

### APIs
- **OpenWeatherMap** - https://openweathermap.org/api (free tier: 60/min)
- **Solar Position Algorithm** - Can use built-in (no API needed)
- **Wind Model** - Use weather API wind speed data

### Data Sources (Already Available)
- ✅ OREE price history (2 years)
- ✅ Hourly prices (Jan-Feb 2026)
- ✅ Sample energy data (with solar generation)

---

## 📝 Notes

- **Training data:** 2 years of daily prices available, enough for XGBoost
- **Scenario weights:** Can be tuned per user preference
- **Retraining threshold:** Trigger on settings change or daily if new data
- **Inference latency:** Target <500ms per recommendation
- **Cold start:** Use default scenario (MaxSafety) until model trained
- **Model versioning:** Save model artifacts with timestamp + git commit hash

---

**Next Action:** Create feature branch and start Phase 3A implementation!
