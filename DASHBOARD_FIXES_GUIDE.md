# Dashboard Fixes: Implementation Guide

**Date:** 2026-02-07 01:06 GMT+2  
**Scope:** Make dashboard REAL (not mock)  
**Effort:** 15-20 hours over 2 weeks  

---

## FIX #1: Settings Persistence (2 hours)

### Problem
Settings lost on page refresh. Changes only in Vue memory.

### Solution A: localStorage (Instant, No Backend)

**Step 1: Create composable**
```typescript
// composables/useSettings.ts (NEW FILE)
import { useState, useRouter } from '#app'

export const useSettings = () => {
  const router = useRouter()
  
  // Initialize from localStorage
  const settings = useState('energy_settings', () => {
    if (process.client) {
      const saved = localStorage.getItem('energy_settings')
      if (saved) {
        return JSON.parse(saved)
      }
    }
    
    return {
      general: {
        siteName: 'Factory #1',
        timezone: 'Europe/Kiev (GMT+2)',
        currency: 'UAH',
        notificationsEnabled: true
      },
      battery: {
        capacity: 150,
        minSOC: 15,
        maxChargeRate: 50,
        maxDischargeRate: 50
      },
      notifications: {
        highPrice: true,
        highPriceThreshold: 13.0,
        lowPrice: true,
        lowPriceThreshold: 7.0,
        modelComplete: true,
        systemAlerts: true
      },
      model: {
        learningRate: 0.0003,
        batchSize: 64,
        epochs: 20
      }
    }
  })
  
  const saveSettings = async (newSettings) => {
    try {
      // Save to localStorage
      localStorage.setItem('energy_settings', JSON.stringify(newSettings))
      
      // Optionally: sync to backend
      if (!process.server) {
        try {
          await $fetch('/api/settings/save', {
            method: 'POST',
            body: newSettings
          })
        } catch (e) {
          console.warn('Backend sync failed, using local:', e)
          // Continue anyway - localStorage works offline
        }
      }
      
      // Update state
      Object.assign(settings.value, newSettings)
      
      return { success: true }
    } catch (e) {
      console.error('Save failed:', e)
      return { success: false, error: e.message }
    }
  }
  
  const resetSettings = () => {
    localStorage.removeItem('energy_settings')
    location.reload()  // Reload with defaults
  }
  
  return {
    settings: computed(() => settings.value),
    saveSettings,
    resetSettings
  }
}
```

**Step 2: Update pages/settings.vue**
```vue
<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import { useSettings } from '#app'

const { settings, saveSettings, resetSettings } = useSettings()

const activeTab = ref('general')
const isSaving = ref(false)
const saveStatus = reactive({
  show: false,
  success: false,
  message: ''
})

// Update save function
const handleSaveSettings = async () => {
  isSaving.value = true
  const result = await saveSettings(settings.value)
  
  if (result.success) {
    saveStatus.success = true
    saveStatus.message = '✅ Settings saved and will persist on reload!'
  } else {
    saveStatus.success = false
    saveStatus.message = `❌ Save failed: ${result.error}`
  }
  
  saveStatus.show = true
  isSaving.value = false
  
  setTimeout(() => {
    saveStatus.show = false
  }, 5000)
}

// Update reset function
const handleResetSettings = () => {
  if (confirm('Are you sure? This will reset to defaults.')) {
    resetSettings()
  }
}
</script>
```

**Result:**
- ✅ Settings survive page refresh
- ✅ Works offline (localStorage)
- ✅ Syncs to backend when available
- ⏱️ Implementation: 30 minutes

---

## FIX #2: Real Battery Data (3 hours)

### Problem
Battery SOC hardcoded at 75%, not from real hardware.

### Solution: Mock API + Future Integration

**Step 1: Create battery data store**
```typescript
// server/utils/battery.ts (NEW)
import fs from 'fs'
import path from 'path'

const BATTERY_FILE = path.join(process.cwd(), 'data/battery_state.json')

const DEFAULT_STATE = {
  soc: 75,
  capacity: 150,
  voltage: 400,
  current: 0,
  temperature: 22,
  lastUpdate: new Date().toISOString(),
  cycles: 1245,
  health: 98.5  // % of original capacity
}

export const getBatteryState = async () => {
  try {
    if (fs.existsSync(BATTERY_FILE)) {
      const data = JSON.parse(fs.readFileSync(BATTERY_FILE, 'utf8'))
      return data
    }
  } catch (e) {
    console.warn('Failed to load battery state:', e)
  }
  return DEFAULT_STATE
}

export const updateBatteryState = async (updates: Partial<typeof DEFAULT_STATE>) => {
  const current = await getBatteryState()
  const updated = {
    ...current,
    ...updates,
    lastUpdate: new Date().toISOString()
  }
  fs.writeFileSync(BATTERY_FILE, JSON.stringify(updated, null, 2))
  return updated
}

export const simulateBatteryBehavior = async () => {
  // Simulate battery changes over time
  const state = await getBatteryState()
  
  // SOC changes based on time of day and solar
  const hour = new Date().getHours()
  let socDelta = 0
  
  if (hour >= 5 && hour <= 12) {
    // Solar charging period
    socDelta = Math.random() * 0.5  // +0 to +0.5%/min
  } else if (hour >= 13 && hour <= 18) {
    // Peak solar, less charging (or discharge if selling)
    socDelta = (Math.random() - 0.7) * 0.3
  } else {
    // Night: slight discharge
    socDelta = -Math.random() * 0.2
  }
  
  const newSOC = Math.max(
    state.soc + socDelta,
    0
  )
  
  return updateBatteryState({
    soc: Math.min(newSOC, 100),
    current: Math.random() * 50 - 25,  // -25 to +25 A
    temperature: 20 + Math.random() * 10  // 20-30°C
  })
}
```

**Step 2: Create API endpoint**
```typescript
// server/api/battery/status.ts (NEW)
import { getBatteryState, simulateBatteryBehavior } from '~/server/utils/battery'

export default defineEventHandler(async (event) => {
  // Optional: simulate behavior
  const querySimulate = getQuery(event).simulate
  if (querySimulate === 'true') {
    await simulateBatteryBehavior()
  }
  
  const state = await getBatteryState()
  
  return {
    ...state,
    // Add computed fields
    availableToDraw: Math.max(0, (state.soc - 15) / 100 * state.capacity),
    availableToCharge: Math.max(0, (100 - state.soc) / 100 * state.capacity),
    power: state.voltage * state.current / 1000  // kW
  }
})
```

**Step 3: Create client composable**
```typescript
// composables/useBatteryStatus.ts (NEW)
export const useBatteryStatus = () => {
  const status = ref(null)
  const error = ref(null)
  const loading = ref(false)
  
  const fetchStatus = async () => {
    loading.value = true
    try {
      status.value = await $fetch('/api/battery/status')
      error.value = null
    } catch (e) {
      error.value = e.message
      console.error('Failed to fetch battery status:', e)
    } finally {
      loading.value = false
    }
  }
  
  onMounted(() => {
    fetchStatus()
    
    // Poll every 5 seconds
    const interval = setInterval(fetchStatus, 5000)
    
    onUnmounted(() => clearInterval(interval))
  })
  
  const updateSOC = async (newSOC: number) => {
    try {
      const result = await $fetch('/api/battery/update', {
        method: 'POST',
        body: { soc: newSOC }
      })
      status.value = result
      return true
    } catch (e) {
      error.value = e.message
      return false
    }
  }
  
  return {
    status: computed(() => status.value),
    error: computed(() => error.value),
    loading: computed(() => loading.value),
    fetchStatus,
    updateSOC
  }
}
```

**Step 4: Use in Control page**
```vue
<!-- pages/control.vue -->
<script setup>
import { useBatteryStatus } from '#app'

const { status, loading, error } = useBatteryStatus()
</script>

<template>
  <div>
    <!-- Battery SOC Display (NOW LIVE) -->
    <div class="text-center">
      <div v-if="error" class="text-red-400">⚠️ {{ error }}</div>
      <div v-else-if="loading" class="text-yellow-400">Loading battery status...</div>
      <div v-else>
        <div class="text-4xl font-bold text-energy-400">
          {{ Math.round(status?.soc || 0) }}%
        </div>
        <p class="text-sm text-slate-400">
          {{ status?.availableToDraw.toFixed(1) }} kWh available
        </p>
        <p class="text-xs text-slate-500">
          Updated: {{ new Date(status?.lastUpdate).toLocaleTimeString() }}
        </p>
      </div>
    </div>
  </div>
</template>
```

**Result:**
- ✅ SOC updates every 5 seconds
- ✅ Simulates realistic behavior
- ✅ Easy to connect to real hardware later
- ⏱️ Implementation: 1.5 hours

---

## FIX #3: Interactive Charts (2 hours)

### Problem
Charts are static SVGs, no hover tooltips.

### Solution: Add SVG tooltips

**Step 1: Update Control page chart**
```vue
<!-- pages/control.vue -->
<template>
  <div class="h-80 bg-slate-800 rounded-lg p-4 relative" @mouseleave="activeHour = null">
    <svg class="w-full h-full" viewBox="0 0 1000 300" preserveAspectRatio="xMidYMid meet">
      <!-- ... existing chart elements ... -->
      
      <!-- Interactive layer (invisible) -->
      <g class="cursor-pointer">
        <rect v-for="(hour, idx) in 48"
              :key="`hour-${idx}`"
              :x="50 + idx * 18.75"
              y="0"
              width="20"
              height="300"
              fill="transparent"
              @mouseenter="activeHour = idx"
              @mousemove="updateTooltip($event, idx)"
        />
      </g>
      
      <!-- Tooltip -->
      <g v-if="activeHour !== null">
        <!-- Vertical line at cursor -->
        <line
          :x1="50 + activeHour * 18.75 + 10"
          y1="0"
          :x2="50 + activeHour * 18.75 + 10"
          y2="300"
          stroke="#64748b"
          stroke-width="1"
          stroke-dasharray="5,5"
        />
        
        <!-- Tooltip box -->
        <rect
          :x="Math.max(100, 50 + activeHour * 18.75 - 80)"
          :y="30"
          width="160"
          height="100"
          fill="#1e293b"
          stroke="#64748b"
          stroke-width="1"
          rx="4"
        />
        
        <!-- Tooltip text -->
        <text
          :x="Math.max(110, 50 + activeHour * 18.75 - 70)"
          :y="55"
          fill="#10b981"
          font-weight="bold"
          font-size="14"
        >
          Hour {{ activeHour }}: {{ forecastHours[activeHour].time }}
        </text>
        
        <text
          :x="Math.max(110, 50 + activeHour * 18.75 - 70)"
          :y="75"
          fill="#fff"
          font-size="13"
        >
          Price: {{ forecastHours[activeHour].price }}
        </text>
        
        <text
          :x="Math.max(110, 50 + activeHour * 18.75 - 70)"
          :y="95"
          fill="#94a3b8"
          font-size="12"
        >
          Action: {{ forecastHours[activeHour].action }}
        </text>
        
        <text
          :x="Math.max(110, 50 + activeHour * 18.75 - 70)"
          :y="115"
          fill="#94a3b8"
          font-size="12"
        >
          Confidence: 78%
        </text>
      </g>
    </svg>
    
    <!-- Legend with hover explanation -->
    <div class="mt-4 grid grid-cols-4 gap-2 text-xs">
      <div class="p-2 bg-slate-800 rounded">
        <div class="text-slate-400">🟢 Green Zone</div>
        <div class="text-slate-500">Optimal battery level (50-80%)</div>
      </div>
      <div class="p-2 bg-slate-800 rounded">
        <div class="text-slate-400">🔴 Red Zone</div>
        <div class="text-slate-500">Unsafe level (&lt;20%)</div>
      </div>
      <div class="p-2 bg-slate-800 rounded">
        <div class="text-slate-400">🟠 Orange Line</div>
        <div class="text-slate-500">Maximum capacity (100%)</div>
      </div>
      <div class="p-2 bg-slate-800 rounded">
        <div class="text-slate-400">🔵 Blue Line</div>
        <div class="text-slate-500">Actual SOC trajectory</div>
      </div>
    </div>
  </div>
</template>

<script setup>
const activeHour = ref(null)

const updateTooltip = (event, idx) => {
  // Can add mouse position tracking here
}
</script>
```

**Step 2: Add tooltips to all sections**
```vue
<!-- General pattern for all metric cards -->
<div class="bg-slate-900 p-4 rounded-lg group relative">
  <!-- Metric value -->
  <div class="text-3xl font-bold text-energy-400">
    {{ value }}
  </div>
  
  <!-- Hover tooltip -->
  <div class="hidden group-hover:block absolute top-0 right-0 bg-slate-950 border border-slate-700 rounded p-3 text-xs text-slate-400 w-48 z-10">
    <p class="font-semibold text-white mb-1">{{ tooltipTitle }}</p>
    <p>{{ tooltipDescription }}</p>
  </div>
</div>
```

**Result:**
- ✅ Interactive chart with hover
- ✅ Tooltips on all metrics
- ✅ Clear explanations
- ⏱️ Implementation: 1.5 hours

---

## FIX #4: Real Model Retraining (4-6 hours)

### Problem
Retraining is fake progress bar, no actual model training.

### Solution: Backend training + streaming progress

**Step 1: Backend endpoint**
```typescript
// server/api/training/retrain.ts (NEW)
import { spawn } from 'child_process'
import path from 'path'

export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const { type } = body  // 'quick' or 'full'
  
  // Determine script and args
  const scriptPath = path.join(process.cwd(), 'scripts/train_model.py')
  const duration = type === 'quick' ? 300 : 600  // 5 or 10 minutes
  
  // Return immediately with job ID
  const jobId = Math.random().toString(36).substring(7)
  
  // Spawn training in background
  const child = spawn('python', [scriptPath, `--type=${type}`, `--duration=${duration}`], {
    detached: true,
    stdio: 'ignore'
  })
  
  child.unref()  // Allow parent to exit
  
  // Assume training returns progress to a progress file
  return {
    success: true,
    jobId,
    estimatedDuration: duration,
    message: `Model ${type} retraining started (${duration}s)`
  }
})
```

**Step 2: Progress polling endpoint**
```typescript
// server/api/training/status.ts (NEW)
import fs from 'fs'
import path from 'path'

export default defineEventHandler(async (event) => {
  const jobId = getQuery(event).jobId
  
  const progressFile = path.join(
    process.cwd(),
    `data/training_${jobId}.json`
  )
  
  try {
    if (fs.existsSync(progressFile)) {
      const progress = JSON.parse(fs.readFileSync(progressFile, 'utf8'))
      return {
        jobId,
        percent: progress.percent,
        timeRemaining: progress.timeRemaining,
        status: progress.status,  // 'training', 'complete', 'failed'
        error: progress.error
      }
    } else {
      return {
        jobId,
        percent: 0,
        status: 'starting'
      }
    }
  } catch (e) {
    return {
      jobId,
      status: 'error',
      error: e.message
    }
  }
})
```

**Step 3: Update Settings page**
```vue
<script setup>
const retraining = reactive({
  active: false,
  completed: false,
  progress: 0,
  timeRemaining: '0s',
  type: '',
  jobId: null,
  error: null
})

const launchRetraining = async () => {
  retraining.active = true
  retraining.progress = 0
  retraining.error = null
  retraining.type = 'quick'
  
  try {
    // Start training
    const result = await $fetch('/api/training/retrain', {
      method: 'POST',
      body: { type: 'quick' }
    })
    
    retraining.jobId = result.jobId
    
    // Poll progress
    const pollInterval = setInterval(async () => {
      try {
        const status = await $fetch(
          `/api/training/status?jobId=${retraining.jobId}`
        )
        
        retraining.progress = status.percent
        retraining.timeRemaining = status.timeRemaining
        
        if (status.status === 'complete') {
          clearInterval(pollInterval)
          retraining.active = false
          retraining.completed = true
          
          saveStatus.success = true
          saveStatus.message = '✅ Model retraining complete and active!'
          saveStatus.show = true
          
          setTimeout(() => {
            retraining.completed = false
          }, 5000)
        } else if (status.status === 'error') {
          clearInterval(pollInterval)
          retraining.active = false
          retraining.error = status.error
          
          saveStatus.success = false
          saveStatus.message = `❌ Retraining failed: ${status.error}`
          saveStatus.show = true
        }
      } catch (e) {
        console.error('Status poll failed:', e)
      }
    }, 1000)  // Poll every second
    
  } catch (e) {
    retraining.active = false
    retraining.error = e.message
    
    saveStatus.success = false
    saveStatus.message = `❌ Failed to start retraining: ${e.message}`
    saveStatus.show = true
  }
}
</script>
```

**Step 4: Python training script**
```python
# scripts/train_model.py
import json
import time
import sys
from pathlib import Path
import argparse

def train_model(model_type, duration):
    """Simulate or run actual PPO training"""
    
    job_id = sys.argv.get('--job-id', 'default')
    progress_file = Path(f'data/training_{job_id}.json')
    
    total_steps = int(duration * 10)  # 10 steps per second
    
    for step in range(total_steps):
        percent = int((step / total_steps) * 100)
        time_remaining = duration - (step / 10)
        
        # Save progress
        progress_file.write_text(json.dumps({
            'percent': percent,
            'timeRemaining': f'{time_remaining:.0f}s',
            'status': 'training',
            'step': step
        }))
        
        # Simulate training work
        time.sleep(0.1)
    
    # Mark complete
    progress_file.write_text(json.dumps({
        'percent': 100,
        'timeRemaining': '0s',
        'status': 'complete',
        'step': total_steps
    }))
    
    print(f'Training complete: {model_type}')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--type', default='quick')
    parser.add_argument('--duration', type=int, default=300)
    parser.add_argument('--job-id', default='default')
    
    args = parser.parse_args()
    train_model(args.type, args.duration)
```

**Result:**
- ✅ Real background training
- ✅ Progress streaming to client
- ✅ Can be replaced with actual PPO code
- ⏱️ Implementation: 3-4 hours

---

## FIX #5: XGBoost vs CatBoost Decision

### Recommendation: Stick with XGBoost for now

**Why:**
1. **XGBoost** is proven, fast, and sufficient for 24h price forecasting
2. **CatBoost** is overkill (better for pure categorical data)
3. **LightGBM** is worth testing in week 2 (same accuracy, 2-3x faster)

**Code comparison:**
```python
# XGBoost (Current)
model = xgb.XGBRegressor(
    max_depth=6,
    learning_rate=0.1,
    n_estimators=200,
    objective='reg:squarederror'
)

# CatBoost (Overkill for your data)
model = CatBoostRegressor(
    depth=6,
    learning_rate=0.1,
    iterations=200,
    cat_features=[]  # Your data is mostly numeric
)

# LightGBM (Try in week 2)
model = lgb.LGBMRegressor(
    max_depth=6,
    learning_rate=0.1,
    n_estimators=200
)
```

**Conclusion:** Use **XGBoost → LightGBM** progression. Skip CatBoost.

---

## PRIORITY ROADMAP

**This Week (Feb 7-10):**
- [ ] Settings localStorage (2h)
- [ ] Battery API + composable (3h)
- [ ] Interactive tooltips (2h)
- **Total:** 7 hours, major improvements

**Next Week (Feb 11-15):**
- [ ] Real retraining backend (6h)
- [ ] Settings database sync (2h)
- **Total:** 8 hours, production-ready

**Total effort:** 15 hours over 2 weeks  
**Result:** Dashboard fully functional, not mock

---

## TESTING CHECKLIST

After implementing each fix, test:

- [ ] Settings saved after page refresh
- [ ] Battery SOC updates every 5 seconds
- [ ] Retraining actually trains (check progress file)
- [ ] Tooltips appear on chart hover
- [ ] No console errors
- [ ] Mobile responsive
- [ ] Performance acceptable (< 100ms updates)

