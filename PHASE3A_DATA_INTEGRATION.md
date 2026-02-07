# Phase 3A: Data Integration - Implementation Guide

**Status:** Ready to execute  
**Estimated Duration:** 3-4 hours  
**Target:** Get real-time weather, solar, wind data flowing into dashboard  

---

## 🎯 Goals

By end of Phase 3A:
1. ✅ Weather API (OpenWeatherMap) integrated and cached
2. ✅ Solar irradiance model running (position-based, cloud-adjusted)
3. ✅ Wind generation model built (from weather API data)
4. ✅ Settings schema extended (solar/wind capacity, discharge schedule, scenario, location)
5. ✅ Dashboard displays real-time weather + generation forecasts
6. ✅ Settings page allows editing all new parameters

---

## 📋 Step-by-Step Tasks

### Task 1: OpenWeatherMap API Setup (15 minutes)

**1.1 Get API Key**
- Visit: https://openweathermap.org/api
- Sign up for free account
- Navigate to API keys section
- Copy your API key
- Store in `.env.local` as `OPENWEATHER_API_KEY`

**1.2 Create environment file**

Location: `projects/smart-energy-ai/dashboard/.env.local`

```env
# Weather API
OPENWEATHER_API_KEY=your_api_key_here
OPENWEATHER_LAT=50.45          # Kyiv latitude
OPENWEATHER_LON=30.52          # Kyiv longitude
OPENWEATHER_UNITS=metric       # Use Celsius
OPENWEATHER_CACHE_TTL=21600    # 6 hours cache
```

**1.3 Load env in nuxt.config.ts**
- Add `runtimeConfig` section to read these variables
- Make them available to both server and client

---

### Task 2: Weather API Integration (45 minutes)

**2.1 Create weather data API endpoint**

File: `projects/smart-energy-ai/dashboard/server/api/weather/current.ts`

```typescript
// GET /api/weather/current
// Returns: { temp, humidity, cloudCover, windSpeed, windDirection, pressure }
// Uses cache with 6-hour TTL

import { eventHandler, useRuntimeConfig } from 'h3'

interface WeatherData {
  temp: number
  humidity: number
  cloudCover: number
  windSpeed: number
  windDirection: number
  pressure: number
  description: string
  lastUpdated: string
}

const CACHE_TTL = 6 * 60 * 60 * 1000 // 6 hours
let cachedWeather: WeatherData | null = null
let cacheTime = 0

export default eventHandler(async (event) => {
  const config = useRuntimeConfig()
  
  // Check cache
  if (cachedWeather && Date.now() - cacheTime < CACHE_TTL) {
    return cachedWeather
  }
  
  try {
    const apiKey = config.openwetherApiKey
    const lat = config.openwetherLat
    const lon = config.openwetherLon
    
    const url = `https://api.openweathermap.org/data/2.5/weather?lat=${lat}&lon=${lon}&appid=${apiKey}&units=metric`
    
    const response = await fetch(url)
    const data = await response.json()
    
    const weather: WeatherData = {
      temp: data.main.temp,
      humidity: data.main.humidity,
      cloudCover: data.clouds.all,
      windSpeed: data.wind.speed,
      windDirection: data.wind.deg || 0,
      pressure: data.main.pressure,
      description: data.weather[0].description,
      lastUpdated: new Date().toISOString()
    }
    
    cachedWeather = weather
    cacheTime = Date.now()
    
    return weather
  } catch (error) {
    console.error('Weather API error:', error)
    // Return cached data if available, even if expired
    if (cachedWeather) return cachedWeather
    // Fallback to defaults
    return {
      temp: 15,
      humidity: 60,
      cloudCover: 50,
      windSpeed: 3,
      windDirection: 180,
      pressure: 1013,
      description: 'Unknown',
      lastUpdated: new Date().toISOString()
    }
  }
})
```

**2.2 Create weather forecast endpoint**

File: `projects/smart-energy-ai/dashboard/server/api/weather/forecast.ts`

```typescript
// GET /api/weather/forecast
// Returns: 5-day forecast with 3-hour intervals
// Uses same cache as current weather

interface ForecastHour {
  time: string
  temp: number
  cloudCover: number
  windSpeed: number
  precipitation: number
}

export default eventHandler(async (event) => {
  const config = useRuntimeConfig()
  
  try {
    const apiKey = config.openwetherApiKey
    const lat = config.openwetherLat
    const lon = config.openwetherLon
    
    const url = `https://api.openweathermap.org/data/2.5/forecast?lat=${lat}&lon=${lon}&appid=${apiKey}&units=metric`
    
    const response = await fetch(url)
    const data = await response.json()
    
    const forecast = data.list.slice(0, 40).map((item: any) => ({
      time: new Date(item.dt * 1000).toISOString(),
      temp: item.main.temp,
      cloudCover: item.clouds.all,
      windSpeed: item.wind.speed,
      precipitation: item.rain?.['3h'] || 0
    }))
    
    return { forecast, lastUpdated: new Date().toISOString() }
  } catch (error) {
    console.error('Weather forecast error:', error)
    return { forecast: [], lastUpdated: new Date().toISOString() }
  }
})
```

---

### Task 3: Solar Irradiance Model (30 minutes)

**3.1 Create solar position calculation**

File: `projects/smart-energy-ai/dashboard/server/ml/models/solarPosition.ts`

```typescript
// Solar position algorithm for Kyiv, Ukraine
// Based on NOAA algorithm (simplified)

import * as math from 'mathjs'

interface SolarPosition {
  elevation: number        // Angle above horizon (degrees)
  azimuth: number         // Direction from north (degrees)
  isNight: boolean
  solarNoon: Date
}

interface IrradianceData {
  clearSkyGHI: number     // Global Horizontal Irradiance (W/m²)
  actualGHI: number       // Adjusted for cloud cover
  DNI: number             // Direct Normal Irradiance
  DHI: number             // Diffuse Horizontal Irradiance
}

export function getSolarPosition(lat: number, lon: number, date: Date): SolarPosition {
  // Simplified algorithm
  const now = date.getTime()
  const year = date.getUTCFullYear()
  const month = date.getUTCMonth() + 1
  const day = date.getUTCDate()
  const hour = date.getUTCHours()
  
  // Day of year (1-366)
  const dayOfYear = Math.floor(
    (Date.UTC(year, month - 1, day) - Date.UTC(year, 0, 0)) / 86400000
  )
  
  // Solar declination angle (degrees)
  const B = (360 / 365) * (dayOfYear - 81)
  const declination = 23.45 * math.sin(math.unit(B, 'deg').toNumber('rad'))
  
  // Hour angle (degrees, 15° per hour)
  const hourAngle = 15 * (hour - 12)
  
  // Elevation angle (degrees)
  const elevationRad = math.sin(math.unit(lat, 'deg').toNumber('rad')) *
    math.sin(math.unit(declination, 'deg').toNumber('rad')) +
    math.cos(math.unit(lat, 'deg').toNumber('rad')) *
    math.cos(math.unit(declination, 'deg').toNumber('rad')) *
    math.cos(math.unit(hourAngle, 'deg').toNumber('rad'))
  
  const elevation = math.atan(elevationRad / math.sqrt(1 - elevationRad * elevationRad))
  const elevationDeg = elevation * (180 / Math.PI)
  
  // Azimuth angle (degrees from north)
  const cosAzimuthNum = (math.sin(math.unit(declination, 'deg').toNumber('rad')) *
    math.cos(math.unit(lat, 'deg').toNumber('rad')) -
    math.cos(math.unit(declination, 'deg').toNumber('rad')) *
    math.sin(math.unit(lat, 'deg').toNumber('rad')) *
    math.cos(math.unit(hourAngle, 'deg').toNumber('rad')))
  
  const azimuthRad = Math.atan2(
    math.sin(math.unit(hourAngle, 'deg').toNumber('rad')),
    cosAzimuthNum
  )
  let azimuth = azimuthRad * (180 / Math.PI) + 180
  if (azimuth < 0) azimuth += 360
  
  const isNight = elevationDeg <= 0
  
  return {
    elevation: Math.max(0, elevationDeg),
    azimuth,
    isNight,
    solarNoon: new Date(date.getTime() - (hour - 12) * 3600000)
  }
}

export function calculateIrradiance(
  position: SolarPosition,
  cloudCover: number,
  pressure: number = 1013
): IrradianceData {
  if (position.isNight) {
    return { clearSkyGHI: 0, actualGHI: 0, DNI: 0, DHI: 0 }
  }
  
  // Clear-sky GHI model (simplified)
  const sinElevation = Math.sin(position.elevation * (Math.PI / 180))
  const airMass = 1 / (sinElevation + 0.50572 * Math.pow(96.07995 - position.elevation, -1.6364))
  
  // Clear-sky irradiance
  const Io = 1361 // Solar constant (W/m²)
  const clearSkyGHI = Math.max(
    0,
    Io * 0.7 * Math.pow(0.678, airMass * (pressure / 1013)) * sinElevation
  )
  
  // Adjust for cloud cover
  const cloudFactor = 1 - (cloudCover / 100) * 0.75 // Clouds reduce by max 75%
  const actualGHI = clearSkyGHI * cloudFactor
  
  // Split into direct and diffuse
  const DNI = position.isNight ? 0 : Math.max(0, clearSkyGHI / sinElevation * 0.8)
  const DHI = actualGHI * 0.15 // Simplified
  
  return {
    clearSkyGHI: Math.round(clearSkyGHI),
    actualGHI: Math.round(actualGHI),
    DNI: Math.round(DNI),
    DHI: Math.round(DHI)
  }
}
```

**3.2 Create solar generation endpoint**

File: `projects/smart-energy-ai/dashboard/server/api/solar/potential.ts`

```typescript
// GET /api/solar/potential
// Returns: Current + forecasted solar generation based on capacity & weather

import { eventHandler } from 'h3'
import { getSolarPosition, calculateIrradiance } from '../../ml/models/solarPosition'
import { useSettingsStore } from '../../../app/stores/settingsStore'

export default eventHandler(async (event) => {
  try {
    // Get user's solar capacity from settings
    const settingsStore = useSettingsStore()
    const solarCapacity = settingsStore.solarCapacity || 10 // Default 10 kW
    
    // Get weather data
    const weather = await $fetch('/api/weather/current')
    
    // Kyiv coordinates
    const LAT = 50.45
    const LON = 30.52
    
    // Calculate current solar position & generation
    const now = new Date()
    const position = getSolarPosition(LAT, LON, now)
    const irradiance = calculateIrradiance(position, weather.cloudCover, weather.pressure)
    
    // Convert irradiance to generation
    const panelEfficiency = 0.18 // Typical modern panels
    const currentGeneration = (irradiance.actualGHI * solarCapacity * panelEfficiency) / 1000
    
    // Forecast for next 24 hours
    const forecast = await $fetch('/api/weather/forecast')
    const generation24h = forecast.forecast.slice(0, 8).map((f: any) => {
      const forecastTime = new Date(f.time)
      const fPos = getSolarPosition(LAT, LON, forecastTime)
      const fIrr = calculateIrradiance(fPos, f.cloudCover, weather.pressure)
      return {
        time: f.time,
        generation: Math.max(0, (fIrr.actualGHI * solarCapacity * panelEfficiency) / 1000),
        irradiance: fIrr.actualGHI
      }
    })
    
    return {
      current: {
        generation: Math.max(0, currentGeneration),
        irradiance: irradiance.actualGHI,
        elevation: position.elevation,
        azimuth: position.azimuth
      },
      capacity: solarCapacity,
      forecast24h: generation24h,
      lastUpdated: now.toISOString()
    }
  } catch (error) {
    console.error('Solar potential error:', error)
    return {
      current: { generation: 0, irradiance: 0, elevation: 0, azimuth: 0 },
      capacity: 0,
      forecast24h: [],
      lastUpdated: new Date().toISOString()
    }
  }
})
```

---

### Task 4: Wind Generation Model (20 minutes)

**4.1 Create wind model**

File: `projects/smart-energy-ai/dashboard/server/api/wind/potential.ts`

```typescript
// GET /api/wind/potential
// Returns: Current + forecasted wind generation based on capacity & weather

import { eventHandler } from 'h3'

interface WindTurbineData {
  windSpeed: number
  generation: number
  capacity: number
}

// Simple power curve model for small wind turbines
function windGenerationModel(windSpeed: number, capacity: number): number {
  // Typical small turbine curve
  if (windSpeed < 3) return 0 // Cut-in speed
  if (windSpeed > 25) return 0 // Cut-out speed
  if (windSpeed >= 15) return capacity // Rated capacity
  
  // Linear interpolation between 3 and 15 m/s
  const rampStart = 3
  const rampEnd = 15
  const rampFactor = (windSpeed - rampStart) / (rampEnd - rampStart)
  return capacity * Math.min(1, rampFactor)
}

export default eventHandler(async (event) => {
  try {
    // Get user's wind capacity from settings
    const settingsStore = useSettingsStore()
    const windCapacity = settingsStore.windCapacity || 5 // Default 5 kW
    
    // Get weather data
    const weather = await $fetch('/api/weather/current')
    const forecast = await $fetch('/api/weather/forecast')
    
    // Current generation
    const currentGeneration = windGenerationModel(weather.windSpeed, windCapacity)
    
    // Forecast for next 24 hours
    const generation24h = forecast.forecast.slice(0, 8).map((f: any) => ({
      time: f.time,
      generation: windGenerationModel(f.windSpeed, windCapacity),
      windSpeed: f.windSpeed
    }))
    
    return {
      current: {
        generation: currentGeneration,
        windSpeed: weather.windSpeed,
        windDirection: weather.windDirection
      },
      capacity: windCapacity,
      forecast24h: generation24h,
      lastUpdated: new Date().toISOString()
    }
  } catch (error) {
    console.error('Wind potential error:', error)
    return {
      current: { generation: 0, windSpeed: 0, windDirection: 0 },
      capacity: 0,
      forecast24h: [],
      lastUpdated: new Date().toISOString()
    }
  }
})
```

---

### Task 5: Settings Schema Update (30 minutes)

**5.1 Update settings store**

File: `projects/smart-energy-ai/dashboard/app/stores/settingsStore.ts`

Add these fields:

```typescript
// Add to state
export const useSettingsStore = defineStore('settings', () => {
  const state = ref({
    // ... existing fields ...
    
    // NEW: Generation settings
    solarCapacity: 10,          // kW
    windCapacity: 5,            // kW
    
    // NEW: Discharge schedule
    dischargeSchedule: {
      enabled: false,
      hours: [14, 15, 16, 17],  // Example: discharge at 2-5 PM
      minSOC: 20                 // Min battery level to maintain
    },
    
    // NEW: Location
    location: {
      name: 'Kyiv, Ukraine',
      lat: 50.45,
      lon: 30.52
    },
    
    // NEW: Scenario
    scenario: 'MaxSafety' as 'Winter' | 'MaxProfit' | 'MaxSafety' | 'EnergySafe' | 'Blackout'
  })
  
  // Add to save/load logic
})
```

**5.2 Update settings API**

Update `server/api/settings/save.ts` and `server/api/settings/load.ts` to handle new fields.

---

### Task 6: Settings UI Updates (60 minutes)

**6.1 Add new settings controls**

File: `projects/smart-energy-ai/dashboard/app/pages/settings.vue`

Add sections:

```vue
<template>
  <div class="space-y-6">
    <!-- ... existing sections ... -->
    
    <!-- NEW: Generation Settings -->
    <div class="bg-slate-800 rounded-lg p-6 border border-slate-700">
      <h2 class="text-xl font-bold mb-4">⚡ Generation Capacity</h2>
      
      <div class="space-y-4">
        <!-- Solar Capacity -->
        <div>
          <label class="block text-sm font-medium mb-2">
            Solar Capacity: {{ settingsStore.solarCapacity }} kW
          </label>
          <input
            v-model.number="settingsStore.solarCapacity"
            type="range"
            min="0"
            max="50"
            step="0.5"
            class="w-full"
            @change="saveSettings"
          />
          <p class="text-xs text-slate-400 mt-1">Max capacity of installed solar panels</p>
        </div>
        
        <!-- Wind Capacity -->
        <div>
          <label class="block text-sm font-medium mb-2">
            Wind Capacity: {{ settingsStore.windCapacity }} kW
          </label>
          <input
            v-model.number="settingsStore.windCapacity"
            type="range"
            min="0"
            max="50"
            step="0.5"
            class="w-full"
            @change="saveSettings"
          />
          <p class="text-xs text-slate-400 mt-1">Max capacity of wind turbine</p>
        </div>
      </div>
    </div>
    
    <!-- NEW: Discharge Schedule -->
    <div class="bg-slate-800 rounded-lg p-6 border border-slate-700">
      <h2 class="text-xl font-bold mb-4">🔋 Discharge Schedule</h2>
      
      <div class="space-y-4">
        <label class="flex items-center space-x-3">
          <input
            v-model="settingsStore.dischargeSchedule.enabled"
            type="checkbox"
            class="w-4 h-4"
            @change="saveSettings"
          />
          <span>Enable automatic discharge</span>
        </label>
        
        <div v-if="settingsStore.dischargeSchedule.enabled">
          <p class="text-sm mb-2">Discharge hours (check to enable):</p>
          <div class="grid grid-cols-6 gap-2">
            <label v-for="hour in 24" :key="hour" class="flex items-center space-x-1">
              <input
                :checked="settingsStore.dischargeSchedule.hours.includes(hour)"
                type="checkbox"
                @change="toggleDischargeHour(hour)"
              />
              <span class="text-xs">{{ String(hour).padStart(2, '0') }}:00</span>
            </label>
          </div>
          
          <label class="block mt-4">
            <span class="text-sm mb-2 block">Min Battery Level During Discharge: {{ settingsStore.dischargeSchedule.minSOC }}%</span>
            <input
              v-model.number="settingsStore.dischargeSchedule.minSOC"
              type="range"
              min="10"
              max="60"
              step="5"
              class="w-full"
              @change="saveSettings"
            />
          </label>
        </div>
      </div>
    </div>
    
    <!-- NEW: Scenario Selection -->
    <div class="bg-slate-800 rounded-lg p-6 border border-slate-700">
      <h2 class="text-xl font-bold mb-4">📊 Operating Scenario</h2>
      
      <div class="space-y-3">
        <label
          v-for="scenario in ['Winter', 'MaxProfit', 'MaxSafety', 'EnergySafe', 'Blackout']"
          :key="scenario"
          class="flex items-center space-x-3 p-3 rounded cursor-pointer hover:bg-slate-700"
        >
          <input
            :checked="settingsStore.scenario === scenario"
            type="radio"
            :value="scenario"
            @change="settingsStore.scenario = scenario; saveSettings()"
          />
          <div>
            <p class="font-medium">{{ scenario }}</p>
            <p class="text-xs text-slate-400">{{ getScenarioDescription(scenario) }}</p>
          </div>
        </label>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const settingsStore = useSettingsStore()

function toggleDischargeHour(hour: number) {
  const idx = settingsStore.dischargeSchedule.hours.indexOf(hour)
  if (idx >= 0) {
    settingsStore.dischargeSchedule.hours.splice(idx, 1)
  } else {
    settingsStore.dischargeSchedule.hours.push(hour)
  }
  saveSettings()
}

function getScenarioDescription(scenario: string) {
  const descriptions: Record<string, string> = {
    'Winter': 'Minimize discharge, preserve battery for emergencies',
    'MaxProfit': 'Maximize arbitrage opportunities, trade aggressively',
    'MaxSafety': 'Keep battery above 60%, conservative trading',
    'EnergySafe': 'Maximize self-sufficiency, store all generation',
    'Blackout': 'Emergency mode, emergency discharge only'
  }
  return descriptions[scenario] || ''
}

async function saveSettings() {
  await settingsStore.saveSettings()
}
</script>
```

---

### Task 7: Dashboard Weather Display (30 minutes)

**7.1 Create weather card component**

File: `projects/smart-energy-ai/dashboard/app/components/Weather/WeatherCard.vue`

```vue
<template>
  <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
    <!-- Current Weather -->
    <div class="bg-gradient-to-br from-blue-900 to-slate-900 rounded-lg p-6 border border-slate-700">
      <h3 class="text-lg font-semibold mb-4">🌤️ Current Weather (Kyiv)</h3>
      
      <div class="grid grid-cols-2 gap-4">
        <div>
          <p class="text-sm text-slate-400">Temperature</p>
          <p class="text-3xl font-bold">{{ weather.temp }}°C</p>
        </div>
        <div>
          <p class="text-sm text-slate-400">Wind Speed</p>
          <p class="text-3xl font-bold">{{ weather.windSpeed }} m/s</p>
        </div>
        <div>
          <p class="text-sm text-slate-400">Humidity</p>
          <p class="text-3xl font-bold">{{ weather.humidity }}%</p>
        </div>
        <div>
          <p class="text-sm text-slate-400">Cloud Cover</p>
          <p class="text-3xl font-bold">{{ weather.cloudCover }}%</p>
        </div>
      </div>
      
      <p class="text-sm text-slate-400 mt-4">Last updated: {{ formatTime(weather.lastUpdated) }}</p>
    </div>
    
    <!-- Solar + Wind Generation -->
    <div class="bg-gradient-to-br from-yellow-900 to-slate-900 rounded-lg p-6 border border-slate-700">
      <h3 class="text-lg font-semibold mb-4">⚡ Generation Now</h3>
      
      <div class="space-y-4">
        <div class="flex justify-between items-center">
          <span class="text-sm">☀️ Solar: {{ solar.current.generation.toFixed(2) }} kW</span>
          <span class="text-xs text-slate-400">({{ solar.capacity }} kW capacity)</span>
        </div>
        <div class="w-full bg-slate-700 rounded h-2">
          <div
            class="bg-yellow-400 h-2 rounded"
            :style="{ width: (solar.current.generation / solar.capacity) * 100 + '%' }"
          />
        </div>
        
        <div class="flex justify-between items-center mt-6">
          <span class="text-sm">💨 Wind: {{ wind.current.generation.toFixed(2) }} kW</span>
          <span class="text-xs text-slate-400">({{ wind.capacity }} kW capacity)</span>
        </div>
        <div class="w-full bg-slate-700 rounded h-2">
          <div
            class="bg-blue-400 h-2 rounded"
            :style="{ width: (wind.current.generation / wind.capacity) * 100 + '%' }"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'

interface WeatherData {
  temp: number
  humidity: number
  cloudCover: number
  windSpeed: number
  windDirection: number
  pressure: number
  description: string
  lastUpdated: string
}

const weather = ref<WeatherData>({
  temp: 0,
  humidity: 0,
  cloudCover: 0,
  windSpeed: 0,
  windDirection: 0,
  pressure: 0,
  description: '',
  lastUpdated: ''
})

const solar = ref({ current: { generation: 0, irradiance: 0 }, capacity: 0 })
const wind = ref({ current: { generation: 0, windSpeed: 0 }, capacity: 0 })

onMounted(async () => {
  try {
    weather.value = await $fetch('/api/weather/current')
    solar.value = await $fetch('/api/solar/potential')
    wind.value = await $fetch('/api/wind/potential')
  } catch (error) {
    console.error('Failed to load weather data:', error)
  }
})

function formatTime(isoString: string) {
  return new Date(isoString).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
}
</script>
```

**7.2 Add to dashboard**

Update `app/pages/index.vue` to include:

```vue
<template>
  <div>
    <!-- Navigation (already there) -->
    
    <!-- NEW: Weather Card -->
    <WeatherCard />
    
    <!-- Existing dashboard content -->
  </div>
</template>
```

---

## ✅ Checklist

- [ ] Create `.env.local` with OpenWeatherMap API key
- [ ] Implement `/api/weather/current.ts` with caching
- [ ] Implement `/api/weather/forecast.ts`
- [ ] Implement solar position & irradiance model
- [ ] Implement `/api/solar/potential.ts`
- [ ] Implement wind generation model
- [ ] Implement `/api/wind/potential.ts`
- [ ] Update settings store with new fields
- [ ] Update `/server/api/settings/save.ts` and `load.ts`
- [ ] Create settings.vue UI for new controls
- [ ] Create WeatherCard.vue component
- [ ] Add WeatherCard to dashboard
- [ ] Test: Settings save/load across refresh
- [ ] Test: Weather API working with fallback
- [ ] Test: Solar/wind generation updates with weather
- [ ] Commit: "feat: Phase 3A - Real-time weather and generation data integration"

---

## 🧪 Testing

1. **Weather API**
   - Navigate to http://localhost:3001
   - Check weather card shows temp, humidity, wind speed, cloud cover
   - Refresh page, should show cached data (same values if < 6h)
   - Change cloud cover in manually (if testing locally)

2. **Solar Generation**
   - Settings: Set Solar Capacity to 10 kW
   - Dashboard: Check Solar widget shows generation
   - At night (elevation < 0): Should show 0 generation
   - At midday: Should show non-zero generation

3. **Wind Generation**
   - Settings: Set Wind Capacity to 5 kW
   - Dashboard: Check Wind widget shows generation
   - Check rationale: If wind < 3 m/s, should be 0
   - If wind > 15 m/s, should show full capacity

4. **Settings Persistence**
   - Change all settings
   - Refresh page
   - All settings should persist

5. **Scenario Selection**
   - Select each scenario
   - Verify selected state persists on refresh

---

**Next Phase:** Phase 3B - Feature Engineering (Featuretools integration)

