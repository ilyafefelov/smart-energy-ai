<template>
  <div class="min-h-screen bg-slate-950 text-white p-8">
    <div class="max-w-7xl mx-auto space-y-8">
      <!-- Header -->
      <div>
        <NuxtLink to="/" class="text-blue-400 hover:text-blue-300 text-sm mb-2 inline-block">
          ← Back to Dashboard
        </NuxtLink>
        <h1 class="text-4xl font-bold text-energy-400 mt-2">🎮 Battery Control</h1>
        <p class="text-slate-400 mt-2">Real-time battery management and manual control</p>
      </div>

      <!-- Battery Status -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          label="Current SOC"
          :value="batteryStore.socPercentage"
          icon="🔋"
          color="yellow"
          :description="`${batteryStore.power.toFixed(2)} kW`"
        >
          <div class="mt-4 w-full bg-slate-700 rounded-full h-3">
            <div 
              class="h-full bg-gradient-to-r from-green-500 to-yellow-500 rounded-full transition-all"
              :style="{ width: batteryStore.soc + '%' }"
            ></div>
          </div>
        </MetricCard>

        <MetricCard
          label="Temperature"
          :value="batteryStore.temperature.toFixed(1) + '°C'"
          icon="🌡️"
          :color="batteryStore.temperature > 45 ? 'red' : 'blue'"
          :description="temperatureStatus"
        />

        <MetricCard
          label="Battery Health"
          :value="batteryStore.health.toFixed(1) + '%'"
          icon="❤️"
          color="green"
          :trend="batteryStore.health > 90 ? 'stable' : 'down'"
          :trendValue="-0.5"
        />

        <MetricCard
          label="Status"
          :value="batteryStatus"
          :icon="batteryStatusIcon"
          :color="batteryStatusColor as any"
          :description="batteryStatusMessage"
        />
      </div>

      <!-- Error Handling -->
      <div v-if="batteryStore.error" class="bg-red-900 bg-opacity-30 border border-red-700 rounded-lg p-4">
        <p class="text-red-300 font-semibold">⚠️ {{ batteryStore.error }}</p>
        <button @click="batteryStore.clearError" class="text-xs text-red-400 hover:text-red-300 mt-2">Dismiss</button>
      </div>

      <!-- Manual Controls -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <!-- Quick Action Buttons -->
        <div class="bg-slate-800 bg-opacity-40 border border-slate-700 rounded-lg p-6">
          <h2 class="text-lg font-bold text-white mb-6">⚡ Quick Actions</h2>

          <div class="space-y-3">
            <button 
              @click="chargeNow"
              :disabled="batteryStore.soc > 95 || batteryStore.isCharging"
              class="w-full px-6 py-3 bg-green-600 hover:bg-green-500 disabled:bg-slate-700 disabled:text-slate-500 text-white font-semibold rounded-lg transition"
            >
              ⬆️ Charge Now
            </button>

            <button 
              @click="dischargeNow"
              :disabled="batteryStore.soc < 20 || batteryStore.isDischarging"
              class="w-full px-6 py-3 bg-red-600 hover:bg-red-500 disabled:bg-slate-700 disabled:text-slate-500 text-white font-semibold rounded-lg transition"
            >
              ⬇️ Discharge Now
            </button>

            <button 
              @click="stopOperation"
              :disabled="batteryStore.isIdle"
              class="w-full px-6 py-3 bg-yellow-600 hover:bg-yellow-500 disabled:bg-slate-700 disabled:text-slate-500 text-white font-semibold rounded-lg transition"
            >
              ⏸️ Stop Operation
            </button>

            <button 
              @click="enableAutoMode"
              class="w-full px-6 py-3 bg-blue-600 hover:bg-blue-500 text-white font-semibold rounded-lg transition"
            >
              🤖 Auto Mode
            </button>
          </div>

          <div class="mt-6 pt-6 border-t border-slate-700">
            <p class="text-xs text-slate-400">
              ℹ️ Auto mode uses AI to optimize charge/discharge cycles based on price forecasts
            </p>
          </div>
        </div>

        <!-- Manual Charge Rate Control -->
        <div class="bg-slate-800 bg-opacity-40 border border-slate-700 rounded-lg p-6">
          <h2 class="text-lg font-bold text-white mb-6">⚙️ Charge Rate Control</h2>

          <div class="space-y-4">
            <div>
              <label class="block text-sm font-semibold text-slate-300 mb-3">Target Charge Rate (kW)</label>
              <input 
                v-model.number="targetChargeRate"
                type="range"
                min="0"
                :max="settingsStore.batterySettings.maxChargeRate"
                class="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer"
              />
              <div class="flex justify-between text-xs text-slate-400 mt-2">
                <span>0 kW</span>
                <span class="font-semibold text-energy-400">{{ targetChargeRate.toFixed(1) }} kW</span>
                <span>{{ settingsStore.batterySettings.maxChargeRate }} kW</span>
              </div>
            </div>

            <div>
              <label class="block text-sm font-semibold text-slate-300 mb-3">Target Discharge Rate (kW)</label>
              <input 
                v-model.number="targetDischargeRate"
                type="range"
                min="0"
                :max="settingsStore.batterySettings.maxDischargeRate"
                class="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer"
              />
              <div class="flex justify-between text-xs text-slate-400 mt-2">
                <span>0 kW</span>
                <span class="font-semibold text-energy-400">{{ targetDischargeRate.toFixed(1) }} kW</span>
                <span>{{ settingsStore.batterySettings.maxDischargeRate }} kW</span>
              </div>
            </div>

            <button 
              @click="applyChargeRates"
              class="w-full px-6 py-3 bg-energy-400 hover:bg-cyan-300 text-slate-950 font-semibold rounded-lg transition mt-4"
            >
              ✓ Apply Settings
            </button>
          </div>
        </div>
      </div>

      <!-- Battery Status Details -->
      <div class="bg-slate-800 bg-opacity-40 border border-slate-700 rounded-lg p-6">
        <h2 class="text-lg font-bold text-white mb-6">📊 Detailed Status</h2>

        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div class="bg-slate-900 rounded-lg p-4">
            <p class="text-xs text-slate-400 mb-2">Voltage</p>
            <p class="text-2xl font-bold text-slate-200">{{ batteryStore.state.voltage.toFixed(1) }} V</p>
          </div>

          <div class="bg-slate-900 rounded-lg p-4">
            <p class="text-xs text-slate-400 mb-2">Current</p>
            <p class="text-2xl font-bold" :class="batteryStore.isCharging ? 'text-green-400' : batteryStore.isDischarging ? 'text-red-400' : 'text-slate-200'">
              {{ batteryStore.state.current.toFixed(1) }} A
            </p>
          </div>

          <div class="bg-slate-900 rounded-lg p-4">
            <p class="text-xs text-slate-400 mb-2">Power</p>
            <p class="text-2xl font-bold" :class="batteryStore.power > 0 ? 'text-green-400' : batteryStore.power < 0 ? 'text-red-400' : 'text-slate-200'">
              {{ batteryStore.power.toFixed(1) }} kW
            </p>
          </div>

          <div class="bg-slate-900 rounded-lg p-4">
            <p class="text-xs text-slate-400 mb-2">Capacity</p>
            <p class="text-2xl font-bold text-slate-200">{{ batteryStore.state.capacity }} kWh</p>
          </div>
        </div>
      </div>

      <!-- SOC History Chart -->
      <div class="bg-slate-800 bg-opacity-40 border border-slate-700 rounded-lg p-6">
        <h2 class="text-lg font-bold text-white mb-4">📈 SOC History (Last 30 min)</h2>

        <svg v-if="batteryStore.history.length > 0" viewBox="0 0 1200 300" class="w-full h-48 mb-4">
          <!-- Grid -->
          <line x1="0" y1="75" x2="1200" y2="75" stroke="#475569" stroke-width="1" stroke-dasharray="4" />
          <line x1="0" y1="150" x2="1200" y2="150" stroke="#475569" stroke-width="1" stroke-dasharray="4" />
          <line x1="0" y1="225" x2="1200" y2="225" stroke="#475569" stroke-width="1" stroke-dasharray="4" />

          <!-- Line chart -->
          <polyline
            :points="historyPoints"
            fill="none"
            stroke="#fbbf24"
            stroke-width="3"
            stroke-linecap="round"
            stroke-linejoin="round"
          />

          <!-- Min/Max bounds -->
          <line x1="0" y1="30" x2="1200" y2="30" stroke="#ef4444" stroke-width="2" stroke-dasharray="4" opacity="0.3" />
          <line x1="0" y1="270" x2="1200" y2="270" stroke="#22c55e" stroke-width="2" stroke-dasharray="4" opacity="0.3" />

          <!-- Labels -->
          <text x="10" y="25" font-size="12" fill="#94a3b8">100%</text>
          <text x="10" y="290" font-size="12" fill="#94a3b8">0%</text>
        </svg>

        <div v-else class="flex items-center justify-center h-48 text-slate-400">
          <p>Loading history...</p>
        </div>
      </div>

      <!-- Recommendations -->
      <div class="bg-blue-900 bg-opacity-20 border border-blue-700 rounded-lg p-6">
        <h2 class="text-lg font-bold text-blue-300 mb-4">💡 AI Recommendations</h2>

        <div class="space-y-3">
          <div class="flex items-start gap-3">
            <span class="text-lg">✓</span>
            <div>
              <p class="font-semibold text-blue-200">Current price is above average</p>
              <p class="text-xs text-blue-300 mt-1">Consider discharging to grid to capitalize on high prices</p>
            </div>
          </div>

          <div class="flex items-start gap-3">
            <span class="text-lg">✓</span>
            <div>
              <p class="font-semibold text-blue-200">Battery health is excellent</p>
              <p class="text-xs text-blue-300 mt-1">Safe to increase discharge rate for higher profits</p>
            </div>
          </div>

          <div class="flex items-start gap-3">
            <span class="text-lg">✓</span>
            <div>
              <p class="font-semibold text-blue-200">Low price expected in 3 hours</p>
              <p class="text-xs text-blue-300 mt-1">Wait to charge during the low-price window</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useBatteryStore } from '~/stores/batteryStore'
import { useSettingsStore } from '~/stores/settingsStore'

const batteryStore = useBatteryStore()
const settingsStore = useSettingsStore()

const targetChargeRate = ref(0)
const targetDischargeRate = ref(0)

const batteryStatus = computed(() => {
  if (batteryStore.isCharging) return 'Charging'
  if (batteryStore.isDischarging) return 'Discharging'
  return 'Idle'
})

const batteryStatusIcon = computed(() => {
  if (batteryStore.isCharging) return '⬆️'
  if (batteryStore.isDischarging) return '⬇️'
  return '⏸️'
})

const batteryStatusColor = computed(() => {
  if (batteryStore.isCharging) return 'green'
  if (batteryStore.isDischarging) return 'red'
  return 'yellow'
})

const batteryStatusMessage = computed(() => {
  if (batteryStore.isCharging) return 'Charging from grid'
  if (batteryStore.isDischarging) return 'Discharging to grid'
  return 'Not operating'
})

const temperatureStatus = computed(() => {
  const temp = batteryStore.temperature
  if (temp < 10) return '❄️ Cold'
  if (temp < 20) return '🌤️ Cool'
  if (temp < 35) return '✓ Optimal'
  if (temp < 45) return '⚠️ Warm'
  return '🔥 Hot'
})

// History chart points
const historyPoints = computed(() => {
  if (batteryStore.history.length === 0) return ''

  const maxHistory = 30 // Show last 30 samples
  const hist = batteryStore.history.slice(-maxHistory)

  return hist.map((h, i) => {
    const x = (i / Math.max(hist.length - 1, 1)) * 1200
    const y = 300 - (h.soc / 100) * 270
    return `${x},${y}`
  }).join(' ')
})

const chargeNow = async () => {
  console.log('Charging started')
  // In production, would call battery control API
}

const dischargeNow = async () => {
  console.log('Discharging started')
  // In production, would call battery control API
}

const stopOperation = async () => {
  console.log('Operation stopped')
  // In production, would call battery control API
}

const enableAutoMode = async () => {
  console.log('Auto mode enabled')
  // In production, would save to settings
}

const applyChargeRates = async () => {
  console.log('Charge rates applied', {
    charge: targetChargeRate.value,
    discharge: targetDischargeRate.value
  })
}

onMounted(async () => {
  await Promise.all([
    batteryStore.fetchBatteryStatus(),
    settingsStore.loadSettings()
  ])

  // Start real-time updates
  batteryStore.startRealTimeUpdates(2000)

  // Initialize rates from settings
  targetChargeRate.value = settingsStore.batterySettings.maxChargeRate / 2
  targetDischargeRate.value = settingsStore.batterySettings.maxDischargeRate / 2
})

onUnmounted(() => {
  batteryStore.stopRealTimeUpdates()
})
</script>
