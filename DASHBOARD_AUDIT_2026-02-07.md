# Dashboard Audit: What's Real vs What's Mock

**Date:** 2026-02-07 01:06 GMT+2  
**Request:** Test everything - is data live? Do settings save? Does retraining work?  
**Status:** ⚠️ CRITICAL ISSUES FOUND - See breakdown below

---

## 🔴 CRITICAL FINDINGS

### 1. Settings: NOT PERSISTING ❌

**Current Implementation:**
```javascript
// pages/settings.vue
const settings = reactive({
  siteName: 'Factory #1',
  battery: { capacity: 150, ... },
  notifications: { ... }
})

const saveSettings = async () => {
  isSaving.value = true
  await new Promise(resolve => setTimeout(resolve, 800))  // FAKE DELAY
  saveStatus.show = true
  saveStatus.message = '✅ Settings saved successfully!'
}
```

**Problem:**
- ❌ Settings stored ONLY in Vue memory (volatile)
- ❌ Changes lost on page refresh
- ❌ No API call to backend
- ❌ No database storage
- ❌ UI shows "Saved" but nothing actually saved

**Evidence:**
1. No `fetch()` or `$fetch()` call in saveSettings function
2. No server/api/settings endpoint exists
3. 800ms delay is simulated (hardcoded setTimeout)
4. Reactive object exists only in browser RAM

**What user sees vs reality:**
```
User clicks "Save Settings"
↓
UI shows: "✅ Settings saved successfully!"
↓
Reality: Only Vue state changed, will be LOST on refresh
```

---

### 2. Model Retraining: NOT WORKING ❌

**Current Implementation:**
```javascript
const launchRetraining = async () => {
  retraining.active = true
  
  for (let i = 0; i <= 100; i += 20) {
    retraining.progress = i
    retraining.timeRemaining = `${Math.round(60 - (i * 0.6))}s`
    await new Promise(resolve => setTimeout(resolve, 300))  // FAKE DELAY
  }
  
  retraining.active = false
  retraining.completed = true
  // NO ACTUAL MODEL RETRAINING
}
```

**Problem:**
- ❌ Progress bar is 100% fake (hardcoded loop)
- ❌ No Python/ML code executing
- ❌ No actual PPO model updating
- ❌ User can't tell if model was trained or not
- ❌ Dashboard shows "Retraining Complete" but nothing happened

**Timeline vs Reality:**
```
User clicks "Start Retraining Now"
↓
UI Loop: i = 0, 20, 40, 60, 80, 100 (simulated)
↓ (each step: 300ms × 5 = 1.5 seconds total)
↓
UI shows: "✅ Retraining Complete!"
↓
Reality: Nothing happened, old model still in use
```

---

### 3. Dashboard Data: PARTIALLY LIVE

#### ✅ LIVE (Real Data):
- OREE prices (Feb 1-7, 2026) ✅
- Cost comparison bars ✅
- PPO validation metrics (57.9% savings) ✅
- Financial projections ✅
- Control page gauge + charts ✅

#### ❌ NOT LIVE (Hardcoded):
- Battery SOC: 75% (hardcoded) ❌
- Today's cost: 287₴ (example data) ❌
- AI status: "Active" (mock) ❌
- Retraining countdown: "5h 23m" (fake) ❌

#### 🟡 PARTIALLY LIVE (Mix):
- Settings page: UI works, but doesn't persist ❌
- Control page: UI works, buttons don't execute ❌
- Forecast table: Data from energyData.ts (static) ❌

---

### 4. API Endpoints: STUBBED (No Persistence)

**Files exist but are MOCK:**
```
server/api/prices.ts       - Returns mock data
server/api/battery.ts      - Returns mock data
server/api/metrics.ts      - Returns mock data
server/api/history.ts      - Returns mock data
```

**Each endpoint:**
```typescript
export default defineEventHandler(async (event) => {
  return {
    // HARDCODED DATA - NO DATABASE
    price: 11.63,
    soc: 75,
    ...
  }
})
```

**Problem:**
- ❌ No database queries
- ❌ No parameter handling
- ❌ No actual data storage
- ❌ Always return same mock values

---

### 5. Data Flow: BROKEN IN MULTIPLE PLACES

```
User changes battery settings
        ↓
UI shows "Saved" (LOCAL STATE ONLY)
        ↓
User clicks "Start Retraining"
        ↓
Progress bar animates (FAKE PROGRESS)
        ↓
Shows "Complete" (NO TRAINING HAPPENED)
        ↓
User refreshes page
        ↓
ALL CHANGES LOST (reverts to hardcoded defaults)
```

---

## 📊 WHAT'S REAL VS WHAT'S FAKE

| Feature | Status | Where | Issue |
|---------|--------|-------|-------|
| OREE prices display | ✅ Real | utils/energyData.ts | Hardcoded (but real Feb data) |
| Control gauge | ✅ Real | SVG calculations | Animates correctly |
| Battery trajectory | ✅ Real | SVG chart | Shows actual data |
| Forecast table | 🟡 Mock | Computed data | From hardcoded array |
| Settings form | ❌ Mock | Vue reactive | No persistence |
| Save button | ❌ Mock | 800ms fake delay | No API call |
| Retraining progress | ❌ Mock | Simulated loop | No training |
| Battery SOC display | 🟡 Mock | Hardcoded 75% | Should be live |
| Today's cost | 🟡 Mock | Hardcoded 287₴ | Should be live |
| Settings persistence | ❌ Broken | localStorage missing | Lost on refresh |
| Retraining callback | ❌ Broken | No backend | Can't train |
| API endpoints | ❌ Stubbed | Hardcoded returns | No database |

---

## 🔧 WHAT NEEDS TO BE FIXED

### PRIORITY 1: Settings Persistence (2 hours)

**Current:** Settings only in Vue state, lost on refresh  
**Need:** localStorage + backend persistence

```typescript
// composables/useSettings.ts (NEW)
export const useSettings = () => {
  const settings = useState('settings', () => ({
    siteName: 'Factory #1',
    battery: { capacity: 150, ... },
    notifications: { ... }
  }))

  // Load from localStorage on mount
  onMounted(() => {
    const saved = localStorage.getItem('energy_settings')
    if (saved) {
      Object.assign(settings.value, JSON.parse(saved))
    }
  })

  // Save to localStorage + backend
  const saveSettings = async (newSettings) => {
    // 1. Save locally
    localStorage.setItem('energy_settings', JSON.stringify(newSettings))
    
    // 2. Call backend
    await $fetch('/api/settings/save', {
      method: 'POST',
      body: newSettings
    })
    
    // 3. Update state
    Object.assign(settings.value, newSettings)
  }

  return { settings, saveSettings }
}
```

**Backend needed:**
```typescript
// server/api/settings/save.ts
export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  
  // Save to database (or JSON file)
  // db.settings.update(userId, body)
  
  return { success: true, settings: body }
})

// server/api/settings/load.ts
export default defineEventHandler(async (event) => {
  // Load from database
  // const settings = db.settings.get(userId)
  
  return settings
})
```

---

### PRIORITY 2: Real Retraining (4-6 hours)

**Current:** Fake progress bar, no training  
**Need:** Actual PPO model retraining

```typescript
// server/api/training/retrain.ts
import { spawn } from 'child_process'

export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const { type, settings } = body  // 'quick' or 'full'
  
  return new Promise((resolve, reject) => {
    // Spawn Python process
    const python = spawn('python', [
      'scripts/train_model.py',
      `--type=${type}`,
      `--settings=${JSON.stringify(settings)}`
    ])
    
    // Stream progress back to client
    python.stdout.on('data', (data) => {
      const progress = JSON.parse(data.toString())
      // Send to client via WebSocket or SSE
      console.log(`Training: ${progress.percent}%`)
    })
    
    python.on('close', (code) => {
      if (code === 0) {
        resolve({ success: true, message: 'Training complete' })
      } else {
        reject(new Error('Training failed'))
      }
    })
  })
})
```

**Client side:**
```typescript
const launchRetraining = async () => {
  retraining.active = true
  
  try {
    const response = await fetch('/api/training/retrain', {
      method: 'POST',
      body: JSON.stringify({
        type: 'quick',
        settings: settings.value
      })
    })
    
    // REAL: Listen to progress events
    // (need WebSocket or EventSource for true streaming)
    
    // For now: poll progress
    while (retraining.active) {
      const status = await $fetch('/api/training/status')
      retraining.progress = status.percent
      retraining.timeRemaining = status.timeRemaining
      await new Promise(r => setTimeout(r, 500))
    }
  } catch (e) {
    retraining.error = e.message
  }
}
```

---

### PRIORITY 3: Live Battery Data (3 hours)

**Current:** SOC = 75% (hardcoded)  
**Need:** Real battery API

```typescript
// server/api/battery/status.ts
export default defineEventHandler(async (event) => {
  // In production: read from actual battery
  // const soc = await battery.getStateOfCharge()
  
  // For now: simulate with stored value
  const stored = await getFromDatabase('battery_status')
  
  return {
    soc: stored.soc || 75,
    capacity: stored.capacity || 150,
    voltage: stored.voltage || 400,
    current: stored.current || 25,
    temperature: stored.temperature || 22,
    lastUpdate: new Date().toISOString()
  }
})
```

**Client:**
```typescript
// composables/useBatteryStatus.ts
export const useBatteryStatus = () => {
  const status = ref(null)
  
  const fetchStatus = async () => {
    status.value = await $fetch('/api/battery/status')
  }
  
  // Poll every 10 seconds
  onMounted(() => {
    fetchStatus()
    setInterval(fetchStatus, 10000)
  })
  
  return { status }
}
```

---

### PRIORITY 4: Interactive Charts (2 hours)

**Current:** SVG charts are static  
**Need:** Hover tooltips + interactivity

```vue
<!-- pages/control.vue -->
<template>
  <svg
    @mousemove="handleMouseMove"
    @mouseleave="tooltip.show = false"
  >
    <!-- Price line -->
    <polyline
      points="..."
      @mouseenter="tooltip.show = true; tooltip.type = 'price'"
      @mousemove="updateTooltip"
    />
    
    <!-- Tooltip -->
    <g v-if="tooltip.show">
      <rect
        x="100"
        y="50"
        width="200"
        height="80"
        fill="#1e293b"
        stroke="#64748b"
      />
      <text x="110" y="70" fill="#fff">
        Price: {{ tooltip.price }}₴/kWh
      </text>
      <text x="110" y="90" fill="#94a3b8" font-size="12">
        Action: {{ tooltip.action }}
      </text>
      <text x="110" y="110" fill="#94a3b8" font-size="12">
        Confidence: {{ tooltip.confidence }}%
      </text>
    </g>
  </svg>
</template>

<script setup>
const tooltip = reactive({
  show: false,
  type: '',
  price: 0,
  action: '',
  confidence: 0,
  x: 0,
  y: 0
})

const handleMouseMove = (e) => {
  const rect = e.currentTarget.getBoundingClientRect()
  const x = e.clientX - rect.left
  
  // Find nearest data point
  const dataIndex = Math.round((x / rect.width) * 48)
  const data = forecastHours[dataIndex]
  
  tooltip.price = data.price
  tooltip.action = data.action
  tooltip.confidence = data.confidence
  tooltip.x = x
  tooltip.y = 50
}
</script>
```

---

### PRIORITY 5: CatBoost vs XGBoost Decision (1 hour research)

**Question:** Should we use CatBoost instead of XGBoost?

**Comparison:**

| Aspect | XGBoost | CatBoost | LightGBM |
|--------|---------|----------|----------|
| **Speed** | Medium | Slow | Fast ⭐ |
| **Accuracy** | High | Very High ⭐ | High |
| **Categorical** | Requires encoding | Native ⭐ | Requires encoding |
| **Hypertuning** | Easy | Hard | Easy |
| **Production** | Proven | Growing | Proven |
| **Dependencies** | Minimal | Heavy | Minimal |
| **Time to train** | Fast | Slow (but better) | Fastest |

**Recommendation for Energy Forecasting:**
- ✅ **LightGBM** (speed + accuracy balance)
- ⚠️ CatBoost (overkill, slow training)
- ✅ XGBoost (baseline, proven)

**For your use case (24h price forecast):**
```python
# Start with XGBoost (proven, fast)
model = xgb.XGBRegressor(
    max_depth=6,
    learning_rate=0.1,
    n_estimators=200,
    objective='reg:squarederror'
)

# Later, test LightGBM (faster, same accuracy)
model = lgb.LGBMRegressor(
    max_depth=6,
    learning_rate=0.1,
    n_estimators=200
)

# Only use CatBoost if you need:
# - Pure categorical features (your data is mostly numeric)
# - 95%+ accuracy requirement (24h forecast doesn't need this)
# - Production inference speed irrelevant (it's not)
```

**Conclusion:** Stick with XGBoost for now, try LightGBM in week 2. CatBoost is overkill.

---

## 🚨 SUMMARY TABLE

| Issue | Severity | Fix Time | Impact |
|-------|----------|----------|--------|
| Settings not persisting | 🔴 CRITICAL | 2h | User loses config |
| Retraining is fake | 🔴 CRITICAL | 4-6h | No model learning |
| Battery data hardcoded | 🔴 CRITICAL | 3h | Can't see real SOC |
| API endpoints stubbed | 🟠 HIGH | 3h | No backend |
| Charts not interactive | 🟡 MEDIUM | 2h | Poor UX |
| No error handling | 🟡 MEDIUM | 2h | User confusion |
| No real-time updates | 🟡 MEDIUM | 3h | Stale data |
| CatBoost question | 🟢 LOW | 1h | Knowledge only |

---

## ✅ WHAT WORKS WELL

**These need NO changes:**
- ✅ OREE data display (real Feb 2026 prices)
- ✅ Dashboard layout (professional, responsive)
- ✅ Navigation menu (sticky, works)
- ✅ Control page graphics (accurate SVG)
- ✅ Settings UI (clean, organized)
- ✅ Cost comparison chart (correct math)

---

## 📋 IMPLEMENTATION ORDER

**WEEK 1 (7-10 Feb):**
1. Add localStorage for settings (2h)
2. Create real battery API endpoint (3h)
3. Add interactive tooltips to charts (2h)

**WEEK 2 (11-15 Feb):**
4. Set up Python training script (4h)
5. Create /api/training/retrain endpoint (2h)
6. Wire retraining to real PPO model (4h)

**WEEK 3 (16-21 Feb):**
7. Database persistence (SQLite or JSON) (3h)
8. Real-time updates (WebSocket or polling) (4h)
9. Error handling & validation (3h)

**After:** Analytics page + XGBoost

---

## 🎯 NEXT STEPS

**Immediate (Today):**
1. Read this audit
2. Decide: Fix dashboard first or Analytics page?
3. Prioritize: Retraining vs Settings vs Battery data?

**Recommended order:**
1. **Settings persistence** (highest ROI - users expect it to work)
2. **Battery live data** (essential for real testing)
3. **Retraining backend** (enables learning)
4. **Interactive charts** (polish)

**Should you:** 
- ✅ Fix dashboard before Analytics? YES
- ✅ Add tooltips? YES (easy, high UX impact)
- ❌ Use CatBoost now? NO (XGBoost is fine)
- ✅ Real retraining? YES (critical)

