<template>
  <div class="space-y-6">
    <!-- Solar Configuration -->
    <div class="bg-slate-800 bg-opacity-40 border border-slate-700 rounded-lg p-6">
      <div class="flex items-center justify-between mb-6">
        <div>
          <h2 class="text-xl font-bold text-white mb-2">☀️ Solar Configuration</h2>
          <p class="text-sm text-slate-400">Configure your photovoltaic system parameters</p>
        </div>
        <div class="flex items-center gap-3">
          <span class="text-sm text-slate-400">Enable Solar</span>
          <input 
            v-model="solarConfig.enabled"
            type="checkbox"
            class="w-5 h-5 rounded"
          />
        </div>
      </div>

      <div v-if="solarConfig.enabled" class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <!-- Solar System Parameters -->
        <div class="space-y-4">
          <h3 class="text-lg font-semibold text-white">⚡ System Specifications</h3>
          
          <div>
            <label class="block text-sm font-semibold text-slate-300 mb-2">
              Panel Capacity (kW)
            </label>
            <input 
              v-model.number="solarConfig.capacity"
              type="number"
              min="0"
              max="1000"
              step="0.1"
              class="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-energy-400"
            />
            <p class="text-xs text-slate-400 mt-1">Total installed solar panel capacity</p>
          </div>

          <div>
            <label class="block text-sm font-semibold text-slate-300 mb-2">
              Panel Efficiency (%)
            </label>
            <input 
              v-model.number="solarConfig.efficiency"
              type="number"
              min="10"
              max="30"
              step="0.1"
              class="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-energy-400"
            />
            <p class="text-xs text-slate-400 mt-1">Solar panel conversion efficiency</p>
          </div>

          <div>
            <label class="block text-sm font-semibold text-slate-300 mb-2">
              Tilt Angle (degrees)
            </label>
            <input 
              v-model.number="solarConfig.tiltAngle"
              type="number"
              min="0"
              max="90"
              step="1"
              class="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-energy-400"
            />
            <p class="text-xs text-slate-400 mt-1">Optimal: 30° for Ukraine latitude</p>
          </div>
        </div>

        <!-- Solar Performance -->
        <div class="space-y-4">
          <h3 class="text-lg font-semibold text-white">📊 Performance Factors</h3>
          
          <div>
            <label class="block text-sm font-semibold text-slate-300 mb-2">
              System Losses (%)
            </label>
            <input 
              v-model.number="solarConfig.systemLosses"
              type="number"
              min="5"
              max="30"
              step="0.5"
              class="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-energy-400"
            />
            <p class="text-xs text-slate-400 mt-1">Inverter, wiring, and shading losses</p>
          </div>

          <div>
            <label class="block text-sm font-semibold text-slate-300 mb-2">
              Temperature Coefficient (%/°C)
            </label>
            <input 
              v-model.number="solarConfig.tempCoefficient"
              type="number"
              min="-1"
              max="0"
              step="0.01"
              class="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-energy-400"
            />
            <p class="text-xs text-slate-400 mt-1">Power reduction per degree above 25°C</p>
          </div>

          <div class="flex items-center gap-3">
            <input 
              v-model="solarConfig.tracking"
              type="checkbox"
              id="solar-tracking"
              class="w-4 h-4 rounded"
            />
            <label for="solar-tracking" class="text-sm text-slate-300">
              Single-axis tracking system
            </label>
          </div>
        </div>
      </div>

      <!-- Solar Generation Preview -->
      <div v-if="solarConfig.enabled" class="mt-6 p-4 bg-slate-900 bg-opacity-50 rounded-lg">
        <h3 class="text-sm font-semibold text-slate-300 mb-3">☀️ Current Solar Status</h3>
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <span class="text-slate-400 text-sm">Current Output:</span>
            <div class="font-semibold text-yellow-400 text-lg">{{ currentSolarPower.toFixed(1) }} kW</div>
          </div>
          <div>
            <span class="text-slate-400 text-sm">Today's Generation:</span>
            <div class="font-semibold text-white text-lg">{{ dailySolarEnergy.toFixed(1) }} kWh</div>
          </div>
          <div>
            <span class="text-slate-400 text-sm">Capacity Factor:</span>
            <div class="font-semibold text-blue-400 text-lg">{{ solarCapacityFactor.toFixed(1) }}%</div>
          </div>
          <div>
            <span class="text-slate-400 text-sm">Annual Estimate:</span>
            <div class="font-semibold text-green-400 text-lg">{{ estimatedAnnualSolar.toLocaleString() }} kWh</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Wind Configuration -->
    <div class="bg-slate-800 bg-opacity-40 border border-slate-700 rounded-lg p-6">
      <div class="flex items-center justify-between mb-6">
        <div>
          <h2 class="text-xl font-bold text-white mb-2">🌬️ Wind Configuration</h2>
          <p class="text-sm text-slate-400">Configure your wind turbine system parameters</p>
        </div>
        <div class="flex items-center gap-3">
          <span class="text-sm text-slate-400">Enable Wind</span>
          <input 
            v-model="windConfig.enabled"
            type="checkbox"
            class="w-5 h-5 rounded"
          />
        </div>
      </div>

      <div v-if="windConfig.enabled" class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <!-- Wind System Parameters -->
        <div class="space-y-4">
          <h3 class="text-lg font-semibold text-white">💨 Turbine Specifications</h3>
          
          <div>
            <label class="block text-sm font-semibold text-slate-300 mb-2">
              Turbine Capacity (kW)
            </label>
            <input 
              v-model.number="windConfig.capacity"
              type="number"
              min="0"
              max="100"
              step="0.1"
              class="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-energy-400"
            />
            <p class="text-xs text-slate-400 mt-1">Rated power output of wind turbine</p>
          </div>

          <div>
            <label class="block text-sm font-semibold text-slate-300 mb-2">
              Cut-in Speed (m/s)
            </label>
            <input 
              v-model.number="windConfig.cutInSpeed"
              type="number"
              min="1"
              max="10"
              step="0.1"
              class="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-energy-400"
            />
            <p class="text-xs text-slate-400 mt-1">Minimum wind speed for power generation</p>
          </div>

          <div>
            <label class="block text-sm font-semibold text-slate-300 mb-2">
              Rated Speed (m/s)
            </label>
            <input 
              v-model.number="windConfig.ratedSpeed"
              type="number"
              min="5"
              max="25"
              step="0.1"
              class="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-energy-400"
            />
            <p class="text-xs text-slate-400 mt-1">Wind speed for rated power output</p>
          </div>
        </div>

        <!-- Wind Performance -->
        <div class="space-y-4">
          <h3 class="text-lg font-semibold text-white">⚡ Performance Settings</h3>
          
          <div>
            <label class="block text-sm font-semibold text-slate-300 mb-2">
              Hub Height (m)
            </label>
            <input 
              v-model.number="windConfig.hubHeight"
              type="number"
              min="5"
              max="100"
              step="1"
              class="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-energy-400"
            />
            <p class="text-xs text-slate-400 mt-1">Height of turbine hub above ground</p>
          </div>

          <div>
            <label class="block text-sm font-semibold text-slate-300 mb-2">
              Average Wind Speed (m/s)
            </label>
            <input 
              v-model.number="windConfig.avgWindSpeed"
              type="number"
              min="1"
              max="15"
              step="0.1"
              class="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-energy-400"
            />
            <p class="text-xs text-slate-400 mt-1">Long-term average wind speed at site</p>
          </div>

          <div>
            <label class="block text-sm font-semibold text-slate-300 mb-2">
              Air Density (kg/m³)
            </label>
            <input 
              v-model.number="windConfig.airDensity"
              type="number"
              min="1.0"
              max="1.3"
              step="0.01"
              class="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-energy-400"
            />
            <p class="text-xs text-slate-400 mt-1">Air density affects power output (1.225 at sea level)</p>
          </div>
        </div>
      </div>

      <!-- Wind Generation Preview -->
      <div v-if="windConfig.enabled" class="mt-6 p-4 bg-slate-900 bg-opacity-50 rounded-lg">
        <h3 class="text-sm font-semibold text-slate-300 mb-3">🌬️ Current Wind Status</h3>
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <span class="text-slate-400 text-sm">Current Output:</span>
            <div class="font-semibold text-cyan-400 text-lg">{{ currentWindPower.toFixed(1) }} kW</div>
          </div>
          <div>
            <span class="text-slate-400 text-sm">Wind Speed:</span>
            <div class="font-semibold text-white text-lg">{{ currentWindSpeed.toFixed(1) }} m/s</div>
          </div>
          <div>
            <span class="text-slate-400 text-sm">Capacity Factor:</span>
            <div class="font-semibold text-blue-400 text-lg">{{ windCapacityFactor.toFixed(1) }}%</div>
          </div>
          <div>
            <span class="text-slate-400 text-sm">Annual Estimate:</span>
            <div class="font-semibold text-green-400 text-lg">{{ estimatedAnnualWind.toLocaleString() }} kWh</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Combined Generation Summary -->
    <div v-if="solarConfig.enabled || windConfig.enabled" class="bg-gradient-to-r from-slate-800 to-slate-700 bg-opacity-40 border border-slate-600 rounded-lg p-6">
      <h2 class="text-xl font-bold text-white mb-4">🌟 Combined Generation Summary</h2>
      
      <div class="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div class="text-center">
          <div class="text-3xl font-bold text-energy-400">{{ totalCurrentGeneration.toFixed(1) }}</div>
          <div class="text-sm text-slate-400">Current Generation (kW)</div>
        </div>
        <div class="text-center">
          <div class="text-3xl font-bold text-green-400">{{ totalInstalledCapacity.toFixed(1) }}</div>
          <div class="text-sm text-slate-400">Installed Capacity (kW)</div>
        </div>
        <div class="text-center">
          <div class="text-3xl font-bold text-blue-400">{{ averageCapacityFactor.toFixed(1) }}%</div>
          <div class="text-sm text-slate-400">Combined Capacity Factor</div>
        </div>
        <div class="text-center">
          <div class="text-3xl font-bold text-yellow-400">{{ totalAnnualGeneration.toLocaleString() }}</div>
          <div class="text-sm text-slate-400">Estimated Annual (kWh)</div>
        </div>
      </div>

      <!-- Visual Generation Bar -->
      <div class="mt-6">
        <div class="flex items-center justify-between text-sm text-slate-300 mb-2">
          <span>Generation Mix</span>
          <span>{{ totalCurrentGeneration.toFixed(1) }} kW / {{ totalInstalledCapacity.toFixed(1) }} kW</span>
        </div>
        <div class="w-full bg-slate-900 rounded-full h-4 overflow-hidden">
          <div class="h-full flex">
            <div 
              v-if="solarConfig.enabled"
              class="bg-gradient-to-r from-yellow-500 to-orange-400 transition-all duration-1000"
              :style="{ width: solarPercentage + '%' }"
              :title="`Solar: ${currentSolarPower.toFixed(1)} kW`"
            ></div>
            <div 
              v-if="windConfig.enabled"
              class="bg-gradient-to-r from-cyan-500 to-blue-400 transition-all duration-1000"
              :style="{ width: windPercentage + '%' }"
              :title="`Wind: ${currentWindPower.toFixed(1)} kW`"
            ></div>
          </div>
        </div>
        <div class="flex justify-between text-xs text-slate-400 mt-1">
          <span v-if="solarConfig.enabled">☀️ Solar: {{ solarPercentage.toFixed(0) }}%</span>
          <span v-if="windConfig.enabled">🌬️ Wind: {{ windPercentage.toFixed(0) }}%</span>
        </div>
      </div>
    </div>

    <!-- Action Buttons -->
    <div class="flex gap-4">
      <button 
        @click="saveConfiguration"
        :disabled="isUpdating"
        class="flex-1 px-6 py-3 bg-energy-400 hover:bg-cyan-300 text-slate-950 font-semibold rounded-lg transition disabled:opacity-50"
      >
        {{ isUpdating ? 'Updating...' : '💾 Save Generation Config' }}
      </button>
      
      <button 
        @click="simulateGeneration"
        class="px-6 py-3 bg-green-600 hover:bg-green-500 text-white font-semibold rounded-lg transition"
      >
        🔄 Simulate
      </button>
    </div>

    <!-- Status Messages -->
    <div v-if="message" class="p-3 rounded-lg" :class="messageClass">
      <p class="text-sm">{{ message }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'

// Configuration state
const solarConfig = ref({
  enabled: true,
  capacity: 10, // kW
  efficiency: 20, // %
  tiltAngle: 30, // degrees
  systemLosses: 15, // %
  tempCoefficient: -0.4, // %/°C
  tracking: false
})

const windConfig = ref({
  enabled: false,
  capacity: 5, // kW
  cutInSpeed: 3, // m/s
  ratedSpeed: 12, // m/s
  hubHeight: 20, // m
  avgWindSpeed: 6, // m/s
  airDensity: 1.225 // kg/m³
})

// Simulation state
const currentSolarPower = ref(0)
const currentWindPower = ref(0)
const currentWindSpeed = ref(0)
const dailySolarEnergy = ref(0)
const isUpdating = ref(false)
const message = ref('')
const messageType = ref<'success' | 'error'>('success')

// Computed properties
const solarCapacityFactor = computed(() => {
  if (!solarConfig.value.enabled || solarConfig.value.capacity === 0) return 0
  return (currentSolarPower.value / solarConfig.value.capacity) * 100
})

const windCapacityFactor = computed(() => {
  if (!windConfig.value.enabled || windConfig.value.capacity === 0) return 0
  return (currentWindPower.value / windConfig.value.capacity) * 100
})

const estimatedAnnualSolar = computed(() => {
  if (!solarConfig.value.enabled) return 0
  // Simplified calculation: capacity * hours * capacity factor
  const hoursPerYear = 8760
  const avgCapacityFactor = 0.15 // 15% typical for Ukraine
  return solarConfig.value.capacity * hoursPerYear * avgCapacityFactor
})

const estimatedAnnualWind = computed(() => {
  if (!windConfig.value.enabled) return 0
  const hoursPerYear = 8760
  const avgCapacityFactor = 0.25 // 25% typical for moderate wind
  return windConfig.value.capacity * hoursPerYear * avgCapacityFactor
})

const totalCurrentGeneration = computed(() => {
  return currentSolarPower.value + currentWindPower.value
})

const totalInstalledCapacity = computed(() => {
  let total = 0
  if (solarConfig.value.enabled) total += solarConfig.value.capacity
  if (windConfig.value.enabled) total += windConfig.value.capacity
  return total
})

const totalAnnualGeneration = computed(() => {
  return estimatedAnnualSolar.value + estimatedAnnualWind.value
})

const averageCapacityFactor = computed(() => {
  if (totalInstalledCapacity.value === 0) return 0
  return (totalCurrentGeneration.value / totalInstalledCapacity.value) * 100
})

const solarPercentage = computed(() => {
  if (totalInstalledCapacity.value === 0) return 0
  return (currentSolarPower.value / totalInstalledCapacity.value) * 100
})

const windPercentage = computed(() => {
  if (totalInstalledCapacity.value === 0) return 0
  return (currentWindPower.value / totalInstalledCapacity.value) * 100
})

const messageClass = computed(() => ({
  'bg-green-900 bg-opacity-30 border border-green-700 text-green-300': messageType.value === 'success',
  'bg-red-900 bg-opacity-30 border border-red-700 text-red-300': messageType.value === 'error'
}))

// Methods
const simulateSolarGeneration = () => {
  if (!solarConfig.value.enabled) {
    currentSolarPower.value = 0
    return
  }

  // Simple solar simulation based on time of day
  const now = new Date()
  const hour = now.getHours()
  const minute = now.getMinutes()
  const timeOfDay = hour + minute / 60
  
  // Solar irradiance curve (simplified)
  let irradiance = 0
  if (timeOfDay >= 6 && timeOfDay <= 18) {
    const solarNoon = 12
    const hourFromNoon = Math.abs(timeOfDay - solarNoon)
    irradiance = Math.max(0, Math.cos((hourFromNoon * Math.PI) / 12)) * 1000 // W/m²
  }
  
  // Add some randomness for clouds
  irradiance *= (0.7 + Math.random() * 0.3)
  
  // Calculate power output
  const panelArea = solarConfig.value.capacity / 0.2 // Assume 200W/m²
  const efficiency = solarConfig.value.efficiency / 100
  const systemEfficiency = 1 - (solarConfig.value.systemLosses / 100)
  
  currentSolarPower.value = (irradiance / 1000) * panelArea * efficiency * systemEfficiency
  currentSolarPower.value = Math.max(0, Math.min(currentSolarPower.value, solarConfig.value.capacity))
}

const simulateWindGeneration = () => {
  if (!windConfig.value.enabled) {
    currentWindPower.value = 0
    currentWindSpeed.value = 0
    return
  }

  // Simulate wind speed with some randomness
  const baseWindSpeed = windConfig.value.avgWindSpeed
  currentWindSpeed.value = baseWindSpeed * (0.5 + Math.random() * 1.0) // 50-150% of average
  
  // Wind power calculation
  if (currentWindSpeed.value < windConfig.value.cutInSpeed) {
    currentWindPower.value = 0
  } else if (currentWindSpeed.value >= windConfig.value.ratedSpeed) {
    currentWindPower.value = windConfig.value.capacity
  } else {
    // Cubic relationship between wind speed and power
    const powerCurve = Math.pow(currentWindSpeed.value / windConfig.value.ratedSpeed, 3)
    currentWindPower.value = windConfig.value.capacity * powerCurve
  }
}

const simulateGeneration = () => {
  simulateSolarGeneration()
  simulateWindGeneration()
  showMessage('Generation simulation updated', 'success')
}

const saveConfiguration = async () => {
  isUpdating.value = true
  
  try {
    // Here you would save to API
    // await $fetch('/api/generation/config', { method: 'POST', body: { solar: solarConfig.value, wind: windConfig.value } })
    
    // Simulate save delay
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    showMessage('Generation configuration saved successfully!', 'success')
  } catch (error) {
    showMessage('Failed to save configuration', 'error')
  } finally {
    isUpdating.value = false
  }
}

const showMessage = (text: string, type: 'success' | 'error') => {
  message.value = text
  messageType.value = type
  
  setTimeout(() => {
    message.value = ''
  }, 5000)
}

// Simulation interval
let simulationInterval: NodeJS.Timeout | null = null

onMounted(() => {
  // Start simulation
  simulateGeneration()
  
  // Update every 30 seconds
  simulationInterval = setInterval(simulateGeneration, 30000)
})

onUnmounted(() => {
  if (simulationInterval) {
    clearInterval(simulationInterval)
  }
})
</script>