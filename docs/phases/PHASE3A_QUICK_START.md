# Phase 3A: Quick Start - 7 Tasks to Complete

**Estimated time: 3-4 hours**  
**Status: Ready to execute**  
**Branch: `feature/ml-pipeline`**

---

## 🎯 Mission

Get real-time weather, solar, and wind generation data flowing into the dashboard with user settings for capacities and discharge schedule.

---

## 📝 7-Task Execution Plan

### TASK 1: API Key Setup (5 min)
1. Go to https://openweathermap.org/api
2. Sign up (free tier)
3. Get API key from https://openweathermap.org/api/one-call-3
4. Create `.env.local` in `dashboard/` folder:
```env
OPENWEATHER_API_KEY=your_key_here
OPENWEATHER_LAT=50.45
OPENWEATHER_LON=30.52
OPENWEATHER_UNITS=metric
OPENWEATHER_CACHE_TTL=21600
```
5. Update `nuxt.config.ts` to read these env vars

### TASK 2: Weather API Endpoint (20 min)
- Create `server/api/weather/current.ts` (code in PHASE3A_DATA_INTEGRATION.md)
- Create `server/api/weather/forecast.ts` (code in PHASE3A_DATA_INTEGRATION.md)
- Test: `curl http://localhost:3001/api/weather/current` → Should return JSON

### TASK 3: Solar Model (15 min)
- Create `server/ml/models/solarPosition.ts` (solar position algorithm)
- Create `server/api/solar/potential.ts` (calculates generation from irradiance)
- Test: `curl http://localhost:3001/api/solar/potential` → Should return { current: { generation, irradiance }, forecast24h: [...] }

### TASK 4: Wind Model (10 min)
- Create `server/api/wind/potential.ts` (simple power curve model)
- Test: `curl http://localhost:3001/api/wind/potential` → Should return { current: { generation }, forecast24h: [...] }

### TASK 5: Settings Store Update (20 min)
- Update `app/stores/settingsStore.ts`:
  - Add: `solarCapacity` (kW)
  - Add: `windCapacity` (kW)
  - Add: `dischargeSchedule` (hours array)
  - Add: `scenario` (enum)
  - Update `saveSettings()` and `loadSettings()` to handle new fields
- Update `server/api/settings/save.ts` and `load.ts`

### TASK 6: Settings UI (30 min)
- Update `app/pages/settings.vue`:
  - Add sliders for solar/wind capacity (0-50 kW)
  - Add hour checkboxes for discharge schedule
  - Add radio buttons for scenario selection (Winter, MaxProfit, MaxSafety, EnergySafe, Blackout)
- Test: Change settings, refresh page → Settings should persist

### TASK 7: Dashboard Weather Display (20 min)
- Create `app/components/Weather/WeatherCard.vue` (displays temp, wind, humidity, cloud cover, solar/wind generation)
- Add to `app/pages/index.vue` at top of dashboard
- Test: Page loads, shows weather and generation data

---

## 🔍 Testing Checklist

```
- [ ] Weather API: Shows real-time temp, wind, humidity from Kyiv
- [ ] Solar model: Shows generation > 0 during day, 0 at night
- [ ] Wind model: Shows generation based on wind speed
- [ ] Settings save: Change capacity values, refresh → values persist
- [ ] Discharge schedule: Select hours, refresh → checked hours persist
- [ ] Scenario: Select different scenarios, refresh → selected scenario persists
- [ ] Dashboard: WeatherCard displays all data without errors
- [ ] Fallback: If weather API fails, dashboard still loads (with cached/default values)
```

---

## 📂 Files to Create

```
dashboard/
├── .env.local (NEW)
├── server/
│   ├── api/
│   │   ├── weather/
│   │   │   ├── current.ts (NEW)
│   │   │   └── forecast.ts (NEW)
│   │   ├── solar/
│   │   │   └── potential.ts (NEW)
│   │   ├── wind/
│   │   │   └── potential.ts (NEW)
│   │   └── settings/
│   │       ├── save.ts (MODIFY - add new fields)
│   │       └── load.ts (MODIFY - add new fields)
│   └── ml/
│       └── models/
│           └── solarPosition.ts (NEW)
└── app/
    ├── stores/
    │   └── settingsStore.ts (MODIFY - add fields)
    ├── components/
    │   └── Weather/
    │       └── WeatherCard.vue (NEW)
    └── pages/
        └── settings.vue (MODIFY - add UI)
```

---

## 💾 Git Workflow

```bash
# Already on feature/ml-pipeline branch
# After completing all 7 tasks:

git add .
git commit -m "feat: Phase 3A - Real-time weather, solar/wind generation, settings UI"
git push origin feature/ml-pipeline
```

---

## 🚀 Success Criteria

✅ **Dashboard shows:**
- Current temperature, wind speed, humidity, cloud cover (from weather API)
- Current solar generation based on sun position and capacity (from user settings)
- Current wind generation based on wind speed and capacity (from user settings)
- 24-hour forecast for solar and wind generation

✅ **Settings saved:**
- Solar capacity persists across refresh
- Wind capacity persists across refresh
- Discharge hours persist across refresh
- Selected scenario persists across refresh

✅ **No errors:**
- Console shows no errors (except maybe network if API is down)
- Page loads completely in <3s
- Weather API fails gracefully (shows cached data or defaults)

---

## 🤝 Questions?

Refer to PHASE3A_DATA_INTEGRATION.md for detailed code and explanations.

