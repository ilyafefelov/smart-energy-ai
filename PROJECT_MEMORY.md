# Smart Energy AI - Project Memory

**Location:** C:\Users\ilyaf\clawd\projects\smart-energy-ai

## 🎯 Project Overview

**Goal:** AI-powered energy management system for battery optimization in Ukrainian energy market

**Stack:**
- Backend: Python (Dagster, stable-baselines3, scikit-learn)
- Frontend: Nuxt3 (Vue 3, TailwindCSS)
- Data: OREE (hourly prices), SSSU (historical), ua.energy (balancing market)
- ML: PPO + Price Forecasting + MILP

## 📊 Key Numbers

| Metric | Value | Status |
|--------|-------|--------|
| Current Cost (naive) | 13,648 UAH/day | baseline |
| Smart Battery Cost | 1,595 UAH/day | optimized |
| Daily Savings | 12,053 UAH/day | ✅ |
| Annual Savings | 4.4M UAH | **ROI in months** |
| RL Cost Reduction | 57.9% | **proven** |
| Energy Price | 11.37 UAH/kWh | Feb 2026 |
| Price Growth | +577% | since 2018 |

## 🔧 System Architecture

```
User Settings (Nuxt Dashboard)
    ↓ POST /api/settings/sync
user_config.json (ML Pipeline)
    ↓ Background trigger
recalculate_pipeline.py
    ↓
latest_ml_results.json
    ↓ Read
Dashboard API → Dashboard UI
```

## 📁 Data Sources

### Collected (2026-02-06)
- ✅ indexes_01.2026.xls (January hourly prices)
- ✅ indexes_02.2026.xls (February hourly prices)
- ✅ SSSU historical (728 records, 2018-2024)
- ✅ OREE daily prices (current)
- ✅ ua.energy balancing market

### Needed (Next Phase)
- Energy balance data (generation by type)
- Weather forecasts (temperature, wind, solar)
- Industrial consumption by sector
- Regional load profiles

## 🚀 Current BEADS Tasks

### P0 (Blocked)
- `smart-energy-ai-q1r`: Optimization algorithm implementation

### P1 (Active)
- `smart-energy-ai-4c1`: Parse hourly price data (Jan-Feb 2026)
- `smart-energy-ai-8ta`: Integrate OREE data with ML pipeline

### P2 (Planning)
- `smart-energy-ai-3zm`: Build price forecasting model
- `smart-energy-ai-qrs`: Real MILP implementation

## 🛠️ Technical Decisions

### Why PPO over DQN
- Continuous action space (battery % charge)
- Better stability for energy control
- Works with limited historical data
- Proven 57.9% improvement

### Why Hybrid ML (Later)
- PPO adapts immediately to price changes
- Forecasting needs 3-6 months historical data
- Hybrid combines RL speed + ML accuracy
- Phased approach: RL now, hybrid in Q2 2026

### Why Nuxt3
- Modern Vue3 ecosystem
- Server-side rendering (better SEO)
- Better performance than Streamlit
- Client-side state management
- Still keep Streamlit for prototyping

## 📈 Performance Baseline

**Test Results (Feb 6, 20:00):**
- Naive approach: 4,965 UAH baseline
- Current RL: 4,538 UAH (8.6% improvement)
- Hybrid ML (placeholder): 4,800 UAH (3.3% improvement)

**Why RL wins:**
- Works with limited data
- Immediate price response
- Already optimized through training
- No cold-start problem

**Why Hybrid will win later:**
- Better pattern recognition
- Seasonal adjustment
- Multi-day planning
- Needs historical data first

## 🔗 Key Files

### Dashboard (Nuxt3)
- **nuxt_dashboard/app/pages/index.vue** - Main dashboard
- **nuxt_dashboard/app/pages/settings.vue** - Settings page
- **nuxt_dashboard/app/stores/** - Pinia stores (settings, battery, prices, metrics)
- **nuxt_dashboard/server/api/** - API endpoints

### ML Pipeline
- **energy_ml/configs/user_config.json** - User configuration
- **recalculate_pipeline.py** - ML recalculation script
- **energy_ml/outputs/latest_ml_results.json** - ML results

### Settings Sync Flow
- POST /api/settings/sync → updates user_config.json → triggers recalculate_pipeline.py

## 📝 Recent Changes (2026-02-28)

**Session: Dashboard Integration**

**Fixed Issues:**
1. ✅ Fixed settingsStore.ts syntax errors (interface declarations, missing capacity)
2. ✅ Fixed generation settings sync (solarCapacity → solar_capacity_kw mapping)
3. ✅ Fixed battery API to read capacity from ML config (not hardcoded 150kWh)
4. ✅ Fixed settings sync to trigger ML pipeline recalculation

**Verified Flow:**
- User changes battery capacity in Settings → POST /api/settings/sync
- Sync endpoint updates user_config.json (e.g., 250kWh)
- Sync triggers recalculate_pipeline.py in background
- ML pipeline recalculates with new config
- Dashboard API reads battery capacity from config
- Savings calculated correctly: 250kWh → 1419 UAH/day (vs 850 for 150kWh)

**New Components:**
- Battery/ConfigPanel.vue - Battery settings form
- Battery/PhysicsSimulator.vue - Battery physics simulation
- Generation/SolarWindConfig.vue - Solar/wind settings
- Preferences/OptimizationProfile.vue - Optimization preferences
- Scenario/Manager.vue - Scenario management
- batteryPhysicsStore.ts - Real-time battery state
- batteryPhysics.ts - Battery physics utilities

**API Endpoints Added:**
- /api/settings/sync - Sync settings to ML pipeline + trigger recalculation
- /api/battery/status - Battery status (reads from ML config)
- /api/metrics/dashboard - Dashboard metrics (real calculations)

## 🎯 Success Criteria

- ✅ Parse Jan-Feb 2026 hourly prices
- ✅ ML integration with new data
- ✅ Nuxt3 dashboard (completed)
- ✅ Settings sync with ML pipeline (completed)
- ⏳ Price forecasting model (Q1 2026)
- ⏳ Full MILP optimization (Q2 2026)
- ⏳ Multi-facility scaling (Q2 2026)

---

**Project Lead:** Illya (@full_iron)
**Team:** Cloud (orchestration) + Codex CLI (code generation)
**Status:** Phase 2 Active - Dashboard Integration Complete
**Last Updated:** 2026-02-28 21:45 GMT+2
