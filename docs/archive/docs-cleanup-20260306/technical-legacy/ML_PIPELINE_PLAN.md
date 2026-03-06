# ML Pipeline Recreation Plan - Weather & Simulation

**Date:** 2026-02-07  
**Status:** Planning Phase  
**Trigger:** After Phase 2 dashboard fixes complete

---

## Context: What We Had Before

In the old dashboard, there were realistic simulations of:
1. **Weather Data** - Wind speed, solar radiation, temperature
2. **Generation** - Solar panels generating power based on weather
3. **Battery** - Charging/discharging based on price optimization strategy
4. **Grid Events** - Peak/off-peak periods, price spikes, demand variations
5. **Real-world Scenarios** - Cloud cover, time of day, seasonal variations

---

## What Needs to Be Recreated

### 1. Weather Simulation Module
**Components:**
- Wind speed variations (0-30 m/s, realistic patterns)
- Solar radiation (0-1000 W/m², diurnal + cloud patterns)
- Temperature (hourly, seasonal trends)
- Cloud cover percentage (0-100%, affects solar)

**Data sources:**
- Historical weather data (Ukraine region)
- Seasonal patterns (winter/summer)
- Realistic time-of-day variations

**Files to create:**
- `server/weather/simulator.ts` - Weather data generator
- `server/weather/history.json` - Historical patterns
- `server/api/weather/current.ts` - Current weather endpoint

### 2. Solar Generation Module
**Components:**
- Panel efficiency (% based on temp)
- Irradiance model (converts solar radiation to power)
- Cloud impact calculation
- Time-of-day efficiency curve
- Panel temperature model

**Formula:**
```
Power_out = Solar_Radiation * Panel_Area * Efficiency * (1 - Cloud_Factor)
Efficiency = Base_Efficiency * Temperature_Factor
```

**Files to create:**
- `server/solar/generator.ts` - Solar generation calculator
- `server/solar/models.json` - Equipment specs, efficiency curves
- `server/api/solar/generation.ts` - Generation forecast endpoint

### 3. Wind Generation Module (Optional but realistic)
**Components:**
- Wind speed to power curve (turbine-specific)
- Cut-in speed (min wind to generate)
- Rated speed (max useful wind)
- Capacity factor (typical 25-35%)

**Files to create:**
- `server/wind/generator.ts` - Wind generation calculator
- `server/wind/models.json` - Turbine specs
- `server/api/wind/generation.ts` - Wind forecast

### 4. Battery Simulation Module
**Components:**
- State of charge (SOC) tracking
- Charge/discharge efficiency (95%)
- Power limits (max kW in/out)
- Thermal model (heat generation)
- Degradation tracking (cycles)

**Logic:**
```
Next_SOC = Current_SOC + (Charge_Power * Efficiency) - Discharge_Power / Battery_Capacity
Cost = Price * Power_Used
Savings = Peak_Price * Power_Saved - Off_Peak_Cost
```

**Files to create:**
- `server/battery/simulator.ts` - Battery state tracker
- `server/battery/models.json` - Battery specs (capacity, efficiency, limits)
- Updated `stores/batteryStore.ts` with simulation

### 5. Grid & Price Simulation
**Components:**
- Daily price curve (realistic patterns)
- Peak hours (usually morning 7-9 AM, evening 6-8 PM)
- Seasonal variations (winter prices higher)
- Random events (supply shortage = spike)
- Demand response signals

**Files to create:**
- `server/grid/pricer.ts` - Price simulation engine
- `server/grid/patterns.json` - Historical price patterns
- `server/api/prices/simulate.ts` - Get simulated prices

### 6. Optimization Strategy Module
**Components:**
- Decision logic (when to charge/discharge)
- Forecast-based planning (24h ahead)
- Risk management (don't drain battery completely)
- Profit maximization (buy low, sell high)

**Files to create:**
- `server/strategy/optimizer.ts` - Optimization logic
- `server/strategy/rules.json` - Strategy parameters
- `server/api/strategy/recommendation.ts` - Get charge/discharge recommendation

### 7. Data Pipeline Orchestration
**Components:**
- Hourly simulation runner (cron job)
- Data aggregation (weather + solar + wind + battery + price)
- Results storage (historical data)
- Performance tracking (savings, ROI, etc.)

**Files to create:**
- `server/pipeline/simulator.ts` - Main orchestrator
- `server/pipeline/jobs.ts` - Scheduled tasks (cron)
- `data/simulation/` - Historical results storage

---

## Implementation Sequence

### Phase 1: Foundation (2-3 hours)
1. **Weather Simulator** - Generate realistic weather data
   - Create `server/weather/simulator.ts`
   - Add weather API endpoint
   - Test: Get realistic weather values

2. **Solar Generator** - Calculate solar power from weather
   - Create `server/solar/generator.ts`
   - Wire to weather data
   - Test: Solar output varies with cloud cover and time of day

3. **Battery Simulator** - Track battery state
   - Update `server/battery/simulator.ts`
   - Store SOC history
   - Test: SOC increases on charge, decreases on discharge

### Phase 2: Intelligence (2-3 hours)
4. **Grid Pricing** - Simulate realistic prices
   - Create `server/grid/pricer.ts`
   - Add daily patterns, seasonality
   - Test: Prices peak at expected times

5. **Strategy Optimizer** - Decide charge/discharge
   - Create `server/strategy/optimizer.ts`
   - Use price forecasts to optimize
   - Test: Charges when cheap, discharges when expensive

6. **Results Aggregation** - Collect all data
   - Create `server/pipeline/simulator.ts`
   - Combine weather + solar + battery + price
   - Test: All systems feed into result

### Phase 3: Integration (1-2 hours)
7. **Dashboard Integration** - Wire to UI
   - Update dashboard pages to show simulation results
   - Add realtime charts (solar generation, battery SOC, savings)
   - Test: All data displays correctly

8. **Historical Data** - Store and analyze
   - Create data storage (`data/simulation/`)
   - Add historical trends page
   - Test: Can view past performance

### Phase 4: Advanced Features (Optional, 2-3 hours)
9. **Cron Jobs** - Automate simulation
   - Schedule hourly runs
   - Update database with results
   - Send alerts (battery low, peak approaching, etc.)

10. **ML Training Integration** - Feed simulator data to models
    - Collect training data from simulation
    - Train forecasting models
    - Evaluate accuracy

11. **Real Data Blending** - Mix with real grid data
    - Use real prices when available
    - Fill gaps with simulation
    - Transition from simulation to real data

---

## Data Files to Create

### `server/weather/history.json`
```json
{
  "hourly_patterns": {
    "solar_radiation": [0, 50, 150, 300, 500, 700, 900, 950, 950, 900, 750, 500, 300, 150, 50, 0],
    "wind_speed": [5, 4.5, 4, 4.5, 5, 5.5, 6, 6.5, 7, 7.5, 8, 8.5, 8, 7.5, 7, 6],
    "temperature": [5, 4, 3, 3, 4, 6, 9, 12, 15, 17, 18, 18, 17, 15, 12, 9]
  },
  "seasonal_factors": {
    "winter": { "solar": 0.5, "wind": 1.2, "temp": -5 },
    "spring": { "solar": 0.8, "wind": 1.0, "temp": 10 },
    "summer": { "solar": 1.0, "wind": 0.9, "temp": 20 },
    "fall": { "solar": 0.7, "wind": 1.1, "temp": 12 }
  }
}
```

### `server/grid/patterns.json`
```json
{
  "daily_price_curve": [
    0.8, 0.75, 0.7, 0.72, 1.2, 1.3, 1.25, 1.15,
    0.9, 0.85, 0.8, 0.85, 0.9, 0.95, 1.0, 1.2,
    1.4, 1.35, 1.3, 1.25, 0.95, 0.85, 0.8, 0.75
  ],
  "seasonal_multiplier": {
    "winter": 1.3,
    "spring": 1.0,
    "summer": 0.9,
    "fall": 1.1
  }
}
```

### `server/battery/models.json`
```json
{
  "battery_specs": {
    "capacity_kwh": 150,
    "max_charge_kw": 10,
    "max_discharge_kw": 10,
    "efficiency": 0.95,
    "min_soc_percent": 10,
    "max_soc_percent": 95
  },
  "solar_panel_specs": {
    "area_m2": 50,
    "capacity_kw": 10,
    "efficiency": 0.18,
    "temperature_coefficient": -0.004
  }
}
```

---

## API Endpoints to Create

### Weather
- `GET /api/weather/current` - Current simulated weather
- `GET /api/weather/forecast?hours=24` - 24h weather forecast

### Solar/Wind Generation
- `GET /api/solar/generation` - Current solar generation
- `GET /api/solar/forecast?hours=24` - Solar forecast
- `GET /api/wind/generation` - Current wind generation

### Battery Simulation
- `GET /api/battery/simulation` - Current battery state
- `GET /api/battery/history?days=7` - Last 7 days

### Grid & Pricing
- `GET /api/grid/prices` - Current simulated prices
- `GET /api/grid/forecast?hours=24` - Price forecast

### Strategy
- `GET /api/strategy/recommendation` - Should charge or discharge?
- `GET /api/strategy/analysis` - Performance metrics

### Pipeline Status
- `GET /api/pipeline/status` - Is simulator running?
- `GET /api/pipeline/results?days=7` - Last 7 days of results

---

## Dashboard Components to Create/Update

### New Pages/Sections
1. **Weather Dashboard** - Current weather + forecast
2. **Generation Dashboard** - Solar + wind output
3. **Simulation Results** - Historical performance
4. **Strategy Analysis** - Algorithm decisions + outcomes

### Updated Components
1. **Price Chart** - Show simulated vs real prices
2. **Battery Chart** - Show SOC simulation + actual
3. **Savings Dashboard** - Show simulation savings

---

## Testing Strategy

### Unit Tests
- Weather generator produces realistic values
- Solar/wind calculations correct
- Battery SOC updates correctly
- Price patterns match expectations
- Optimization algorithm makes sense

### Integration Tests
- All components work together
- Data flows from weather to dashboard
- Hourly simulations complete successfully
- Results stored correctly

### Validation Tests
- Simulated prices realistic (not too high/low)
- Battery SOC never goes negative/over 100%
- Solar generation correlates with cloud cover
- Savings calculations accurate

---

## Files Summary

**New files to create:** ~15 total
**Lines of code:** ~2,000-3,000
**Time estimate:** 6-10 hours total
**Complexity:** Medium (physics/optimization)

**Critical path:**
1. Weather simulator (foundation)
2. Solar generator (depends on weather)
3. Battery + Price (independent)
4. Optimizer (depends on price + battery)
5. Dashboard integration (depends on all above)

---

## Dependencies

- Node.js modules: None new (use existing)
- Data: Historical weather/price patterns (create synthetic)
- ML: Optional (for advanced forecasting)

---

## Success Metrics

✅ Weather varies realistically over 24h cycle  
✅ Solar generation peaks at midday, zero at night  
✅ Battery SOC tracked accurately  
✅ Prices follow daily pattern (cheap off-peak, expensive peak)  
✅ Strategy makes optimal decisions (buys cheap, sells expensive)  
✅ Dashboard shows realistic simulation data  
✅ Historical data shows meaningful trends  
✅ System ready for ML model training  

---

**Status:** Ready to start after Phase 2 dashboard fixes  
**Prerequisite:** Phase 2 branch merged  
**Next:** Create new branch `feature/ml-pipeline-weather-simulation`
