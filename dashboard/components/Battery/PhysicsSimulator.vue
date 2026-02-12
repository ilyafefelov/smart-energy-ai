<template>
  <div class="space-y-6">
    <!-- Battery Status Display -->
    <div class="bg-gradient-to-r from-slate-800 to-slate-700 bg-opacity-60 border border-slate-600 rounded-lg p-6">
      <div class="flex items-center justify-between mb-6">
        <div>
          <h2 class="text-2xl font-bold text-white mb-2">🔋 Battery Control System</h2>
          <p class="text-sm text-slate-400">Real-time battery monitoring and control</p>
        </div>
        <div class="flex items-center gap-4">
          <div :class="[
            'px-3 py-1 rounded-full text-xs font-semibold',
            batteryPhysicsStore.state.isSimulationRunning 
              ? 'bg-green-900 bg-opacity-50 text-green-300 border border-green-700' 
              : 'bg-red-900 bg-opacity-50 text-red-300 border border-red-700'
          ]">
            {{ batteryPhysicsStore.state.isSimulationRunning ? '🟢 Live' : '🔴 Offline' }}
          </div>
        </div>
      </div>

      <!-- Main Battery Visualization -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <!-- SOC Display -->
        <div class="lg:col-span-1">
          <div class="bg-slate-900 bg-opacity-50 rounded-lg p-6">
            <h3 class="text-lg font-semibold text-white mb-4">State of Charge</h3>
            
            <!-- Battery Visual -->
            <div class="relative">
              <!-- Battery outline -->
              <div class="w-32 h-48 mx-auto border-4 border-slate-400 rounded-lg relative bg-slate-800">
                <!-- Battery terminal -->
                <div class="absolute -top-2 left-1/2 transform -translate-x-1/2 w-8 h-3 bg-slate-400 rounded-t"></div>
                
                <!-- SOC fill with animation -->
                <div 
                  class="absolute bottom-0 left-0 right-0 rounded-lg transition-all duration-1000 ease-out"
                  :class="batteryPhysicsStore.socGradient"
                  :style="{ 
                    height: batteryPhysicsStore.state.socPercentage + '%',
                    background: `linear-gradient(to top, ${getSocColor(batteryPhysicsStore.state.soc)})`
                  }"
                >
                  <!-- Charging animation -->
                  <div 
                    v-if="batteryPhysicsStore.state.isCharging"
                    class="absolute inset-0 rounded-lg bg-gradient-to-t from-transparent via-white to-transparent opacity-30 animate-pulse"
                  ></div>
                  
                  <!-- Discharging animation -->
                  <div 
                    v-if="batteryPhysicsStore.state.isDischarging"
                    class="absolute inset-0 rounded-lg"
                  >
                    <div class="absolute inset-0 bg-gradient-to-b from-transparent via-red-400 to-transparent opacity-20 animate-bounce"></div>
                  </div>
                </div>
                
                <!-- SOC percentage overlay -->
                <div class="absolute inset-0 flex items-center justify-center">
                  <div class="text-white font-bold text-lg drop-shadow-lg">
                    {{ batteryPhysicsStore.state.socPercentage.toFixed(1) }}%
                  </div>
                </div>
              </div>
              
              <!-- Status indicators -->
              <div class="mt-4 text-center">
                <div :class="batteryPhysicsStore.powerStatus.color" class="text-sm font-semibold">
                  {{ batteryPhysicsStore.powerStatus.icon }} {{ batteryPhysicsStore.powerStatus.text }}
                </div>
                <div class="text-xs text-slate-400 mt-1">
                  {{ batteryPhysicsStore.state.power > 0 ? 'Storing' : batteryPhysicsStore.state.power < 0 ? 'Supplying' : 'Standby' }} Power
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Battery Metrics -->
        <div class="lg:col-span-2">
          <div class="grid grid-cols-2 gap-4 h-full">
            <!-- Power -->
            <div class="bg-slate-900 bg-opacity-50 rounded-lg p-4">
              <h4 class="text-sm font-semibold text-slate-300 mb-3">⚡ Power Flow</h4>
              <div class="space-y-3">
                <div class="flex justify-between items-center">
                  <span class="text-xs text-slate-400">Current Power:</span>
                  <span :class="getPowerColor(batteryPhysicsStore.state.power)" class="font-bold">
                    {{ batteryPhysicsStore.state.power > 0 ? '+' : '' }}{{ batteryPhysicsStore.state.power.toFixed(1) }} kW
                  </span>
                </div>
                <div class="flex justify-between items-center">
                  <span class="text-xs text-slate-400">Voltage:</span>
                  <span class="text-white font-semibold">{{ batteryPhysicsStore.state.voltage.toFixed(1) }} V</span>
                </div>
                <div class="flex justify-between items-center">
                  <span class="text-xs text-slate-400">Current:</span>
                  <span class="text-white font-semibold">{{ batteryPhysicsStore.state.current.toFixed(1) }} A</span>
                </div>
              </div>
            </div>

            <!-- Health & Status -->
            <div class="bg-slate-900 bg-opacity-50 rounded-lg p-4">
              <h4 class="text-sm font-semibold text-slate-300 mb-3">🏥 Health Status</h4>
              <div class="space-y-3">
                <div class="flex justify-between items-center">
                  <span class="text-xs text-slate-400">Battery Health:</span>
                  <span :class="batteryPhysicsStore.healthStatus.color" class="font-bold">
                    {{ batteryPhysicsStore.state.health }}%
                  </span>
                </div>
                <div class="flex justify-between items-center">
                  <span class="text-xs text-slate-400">Cycle Count:</span>
                  <span class="text-white font-semibold">{{ batteryPhysicsStore.state.cycleCount.toFixed(0) }}</span>
                </div>
                <div class="flex justify-between items-center">
                  <span class="text-xs text-slate-400">Temperature:</span>
                  <span :class="getTemperatureColor(batteryPhysicsStore.state.temperature)" class="font-semibold">
                    {{ batteryPhysicsStore.state.temperature.toFixed(1) }}°C
                  </span>
                </div>
              </div>
            </div>

            <!-- Capacity Info -->
            <div class="bg-slate-900 bg-opacity-50 rounded-lg p-4">
              <h4 class="text-sm font-semibold text-slate-300 mb-3">📊 Capacity Info</h4>
              <div class="space-y-3">
                <div class="flex justify-between items-center">
                  <span class="text-xs text-slate-400">Total Capacity:</span>
                  <span class="text-white font-semibold">{{ batteryPhysicsStore.state.capacity }} kWh</span>
                </div>
                <div class="flex justify-between items-center">
                  <span class="text-xs text-slate-400">Usable Capacity:</span>
                  <span class="text-energy-400 font-semibold">{{ batteryPhysicsStore.state.usableCapacity.toFixed(1) }} kWh</span>
                </div>
                <div class="flex justify-between items-center">
                  <span class="text-xs text-slate-400">Available Energy:</span>
                  <span class="text-blue-400 font-semibold">
                    {{ (batteryPhysicsStore.state.soc * batteryPhysicsStore.state.capacity).toFixed(1) }} kWh
                  </span>
                </div>
              </div>
            </div>

            <!-- Runtime Estimates -->
            <div class="bg-slate-900 bg-opacity-50 rounded-lg p-4">
              <h4 class="text-sm font-semibold text-slate-300 mb-3">⏱️ Time Estimates</h4>
              <div class="space-y-3">
                <div class="flex justify-between items-center">
                  <span class="text-xs text-slate-400">Runtime:</span>
                  <span class="text-orange-400 font-semibold">
                    {{ batteryPhysicsStore.state.estimatedRuntime ? batteryPhysicsStore.state.estimatedRuntime + ' min' : 'N/A' }}
                  </span>
                </div>
                <div class="flex justify-between items-center">
                  <span class="text-xs text-slate-400">Charge Time:</span>
                  <span class="text-green-400 font-semibold">
                    {{ batteryPhysicsStore.state.estimatedChargeTime ? batteryPhysicsStore.state.estimatedChargeTime + ' min' : 'N/A' }}
                  </span>
                </div>
                <div class="flex justify-between items-center">
                  <span class="text-xs text-slate-400">Last Updated:</span>
                  <span class="text-slate-400 text-xs">
                    {{ formatTime(batteryPhysicsStore.state.lastUpdated) }}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Manual Control Panel -->
    <div class="bg-slate-800 bg-opacity-40 border border-slate-700 rounded-lg p-6">
      <div class="flex items-center justify-between mb-6">
        <div>
          <h3 class="text-xl font-bold text-white mb-2">🎮 Manual Control</h3>
          <p class="text-sm text-slate-400">Direct battery charge/discharge control</p>
        </div>
        <div class="flex items-center gap-4">
          <div class="flex items-center gap-2">
            <span class="text-sm text-slate-400">Manual Mode:</span>
            <input 
              :checked="batteryPhysicsStore.state.manualMode"
              @change="toggleManualMode"
              type="checkbox"
              class="w-4 h-4 rounded"
            />
          </div>
          <div class="flex items-center gap-2">
            <span class="text-sm text-slate-400">Auto Optimize:</span>
            <input 
              :checked="batteryPhysicsStore.state.autoOptimization"
              @change="toggleAutoMode"
              type="checkbox"
              class="w-4 h-4 rounded"
            />
          </div>
        </div>
      </div>

      <!-- Power Control Slider -->
      <div class="mb-6">
        <div class="flex justify-between items-center mb-4">
          <label class="text-sm font-semibold text-slate-300">Power Command (kW)</label>
          <div class="text-right">
            <div class="text-lg font-bold text-white">{{ powerCommand }} kW</div>
            <div class="text-xs text-slate-400">
              {{ powerCommand > 0 ? 'Charging' : powerCommand < 0 ? 'Discharging' : 'Idle' }}
            </div>
          </div>
        </div>
        
        <div class="relative">
          <!-- Power slider -->
          <input 
            v-model.number="powerCommand"
            type="range"
            :min="-batteryPhysicsStore.state.maxDischargePower"
            :max="batteryPhysicsStore.state.maxChargePower"
            step="0.1"
            :disabled="!batteryPhysicsStore.state.manualMode"
            class="w-full h-3 bg-slate-700 rounded-lg appearance-none cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
          />
          
          <!-- Slider track markings -->
          <div class="flex justify-between text-xs text-slate-500 mt-2">
            <span>-{{ batteryPhysicsStore.state.maxDischargePower }}kW</span>
            <span>0kW</span>
            <span>+{{ batteryPhysicsStore.state.maxChargePower }}kW</span>
          </div>
        </div>
      </div>

      <!-- Quick Action Buttons -->
      <div class="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
        <button 
          @click="setQuickPower(-batteryPhysicsStore.state.maxDischargePower)"
          :disabled="!batteryPhysicsStore.canDischarge || !batteryPhysicsStore.state.manualMode"
          class="px-4 py-2 bg-red-600 hover:bg-red-500 text-white font-semibold rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed"
        >
          🔻 Max Discharge
        </button>
        
        <button 
          @click="setQuickPower(-batteryPhysicsStore.state.maxDischargePower / 2)"
          :disabled="!batteryPhysicsStore.canDischarge || !batteryPhysicsStore.state.manualMode"
          class="px-4 py-2 bg-orange-600 hover:bg-orange-500 text-white font-semibold rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed"
        >
          📉 Half Discharge
        </button>
        
        <button 
          @click="setQuickPower(0)"
          :disabled="!batteryPhysicsStore.state.manualMode"
          class="px-4 py-2 bg-slate-600 hover:bg-slate-500 text-white font-semibold rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed"
        >
          ⏸️ Idle
        </button>
        
        <button 
          @click="setQuickPower(batteryPhysicsStore.state.maxChargePower / 2)"
          :disabled="!batteryPhysicsStore.canCharge || !batteryPhysicsStore.state.manualMode"
          class="px-4 py-2 bg-green-600 hover:bg-green-500 text-white font-semibold rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed"
        >
          📈 Half Charge
        </button>
        
        <button 
          @click="setQuickPower(batteryPhysicsStore.state.maxChargePower)"
          :disabled="!batteryPhysicsStore.canCharge || !batteryPhysicsStore.state.manualMode"
          class="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white font-semibold rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed"
        >
          🔺 Max Charge
        </button>
      </div>

      <!-- Apply Changes Button -->
      <button 
        @click="applyPowerCommand"
        :disabled="!batteryPhysicsStore.state.manualMode || isApplying"
        class="w-full px-6 py-3 bg-energy-400 hover:bg-cyan-300 text-slate-950 font-bold rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {{ isApplying ? 'Applying...' : '⚡ Apply Power Command' }}
      </button>
    </div>

    <!-- Optimization Presets -->
    <div class="bg-slate-800 bg-opacity-40 border border-slate-700 rounded-lg p-6">
      <div class="flex items-center justify-between mb-6">
        <div>
          <h3 class="text-xl font-bold text-white mb-2">🤖 Smart Operation Modes</h3>
          <p class="text-sm text-slate-400">Automated battery optimization strategies</p>
        </div>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div class="bg-slate-900 bg-opacity-50 rounded-lg p-4 border-2 border-transparent hover:border-green-600 transition cursor-pointer" @click="batteryPhysicsStore.startArbitrageCharge()">
          <div class="text-2xl mb-2">💰</div>
          <h4 class="font-semibold text-white mb-2">Max Earn</h4>
          <p class="text-xs text-slate-400 mb-3">Maximize arbitrage profits by charging during low prices and discharging during high prices</p>
          <div class="text-green-400 text-sm font-semibold">Focus: 70% Profit</div>
        </div>

        <div class="bg-slate-900 bg-opacity-50 rounded-lg p-4 border-2 border-transparent hover:border-blue-600 transition cursor-pointer" @click="batteryPhysicsStore.startBalancedOperation()">
          <div class="text-2xl mb-2">⚖️</div>
          <h4 class="font-semibold text-white mb-2">Balanced</h4>
          <p class="text-xs text-slate-400 mb-3">Balance between profit, battery health, and grid reliability</p>
          <div class="text-blue-400 text-sm font-semibold">Focus: 40% Profit, 30% Health, 30% Reliability</div>
        </div>

        <div class="bg-slate-900 bg-opacity-50 rounded-lg p-4 border-2 border-transparent hover:border-purple-600 transition cursor-pointer" @click="healthOptimizationMode()">
          <div class="text-2xl mb-2">💊</div>
          <h4 class="font-semibold text-white mb-2">Max Battery Health</h4>
          <p class="text-xs text-slate-400 mb-3">Minimize battery degradation by reducing deep cycles and high C-rates</p>
          <div class="text-purple-400 text-sm font-semibold">Focus: Minimize Degradation</div>
        </div>

        <div class="bg-slate-900 bg-opacity-50 rounded-lg p-4 border-2 border-transparent hover:border-yellow-600 transition cursor-pointer" @click="backupPowerMode()">
          <div class="text-2xl mb-2">🔋</div>
          <h4 class="font-semibold text-white mb-2">Max Charge</h4>
          <p class="text-xs text-slate-400 mb-3">Keep battery as full as possible for backup power and outage protection</p>
          <div class="text-yellow-400 text-sm font-semibold">Focus: Backup Power Ready</div>
        </div>
      </div>
    </div>

    <!-- Error/Success Messages -->
    <div v-if="message" class="p-3 rounded-lg" :class="messageClass">
      <p class="text-sm">{{ message }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useBatteryPhysicsStore } from '~/stores/batteryPhysicsStore'

const batteryPhysicsStore = useBatteryPhysicsStore()

// Local state
const powerCommand = ref(0)
const isApplying = ref(false)
const message = ref('')
const messageType = ref<'success' | 'error'>('success')

// Computed
const messageClass = computed(() => ({
  'bg-green-900 bg-opacity-30 border border-green-700 text-green-300': messageType.value === 'success',
  'bg-red-900 bg-opacity-30 border border-red-700 text-red-300': messageType.value === 'error'
}))

// Methods
const getSocColor = (soc: number) => {
  if (soc < 0.2) return '#ef4444, #dc2626' // red
  if (soc < 0.4) return '#f97316, #ea580c' // orange  
  if (soc < 0.8) return '#22c55e, #16a34a' // green
  return '#3b82f6, #2563eb' // blue
}

const getPowerColor = (power: number) => {
  if (power > 0) return 'text-green-400'
  if (power < 0) return 'text-orange-400'
  return 'text-slate-400'
}

const getTemperatureColor = (temp: number) => {
  if (temp > 40) return 'text-red-400'
  if (temp > 30) return 'text-yellow-400'
  if (temp < 0) return 'text-blue-400'
  return 'text-green-400'
}

const formatTime = (date: Date | null) => {
  if (!date) return 'Never'
  return new Intl.DateTimeFormat('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  }).format(date)
}

const setQuickPower = (power: number) => {
  powerCommand.value = power
}

const applyPowerCommand = async () => {
  isApplying.value = true
  try {
    await batteryPhysicsStore.setPowerCommand(powerCommand.value)
    showMessage(`Power command applied: ${powerCommand.value}kW`, 'success')
  } catch (error) {
    showMessage('Failed to apply power command', 'error')
  } finally {
    isApplying.value = false
  }
}

const toggleManualMode = (event: Event) => {
  const enabled = (event.target as HTMLInputElement).checked
  batteryPhysicsStore.setAutoMode(!enabled)
}

const toggleAutoMode = (event: Event) => {
  const enabled = (event.target as HTMLInputElement).checked
  batteryPhysicsStore.setAutoMode(enabled)
}

const healthOptimizationMode = () => {
  // Conservative charging/discharging to preserve battery health
  batteryPhysicsStore.setAutoMode(true)
  showMessage('Battery Health Optimization mode activated', 'success')
}

const backupPowerMode = () => {
  // Keep battery charged for backup power
  const chargePower = batteryPhysicsStore.state.maxChargePower * 0.5 // 50% charge rate
  batteryPhysicsStore.charge(chargePower)
  showMessage('Backup Power mode activated - charging battery', 'success')
}

const showMessage = (text: string, type: 'success' | 'error') => {
  message.value = text
  messageType.value = type
  
  setTimeout(() => {
    message.value = ''
  }, 5000)
}

// Initialize and start real-time updates
onMounted(() => {
  batteryPhysicsStore.startRealTimeUpdates(5000) // Update every 5 seconds
  // Sync local power command with store state
  powerCommand.value = batteryPhysicsStore.state.powerCommand
})

onUnmounted(() => {
  batteryPhysicsStore.stopRealTimeUpdates()
})
</script>