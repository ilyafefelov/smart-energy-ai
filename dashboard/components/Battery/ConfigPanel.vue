<template>
  <div class="bg-slate-800 bg-opacity-40 border border-slate-700 rounded-lg p-6">
    <div class="flex items-center justify-between mb-6">
      <div>
        <h2 class="text-xl font-bold text-white mb-2">🔋 Battery Configuration</h2>
        <p class="text-sm text-slate-400">Configure your battery system parameters</p>
      </div>
      <div class="flex gap-2">
        <button 
          @click="resetToDefaults"
          class="px-3 py-1 text-xs bg-slate-700 hover:bg-slate-600 text-white rounded transition"
        >
          Reset
        </button>
        <button 
          @click="applyPreset('residential')"
          class="px-3 py-1 text-xs bg-blue-600 hover:bg-blue-500 text-white rounded transition"
        >
          Residential
        </button>
        <button 
          @click="applyPreset('commercial')"
          class="px-3 py-1 text-xs bg-purple-600 hover:bg-purple-500 text-white rounded transition"
        >
          Commercial
        </button>
      </div>
    </div>

    <!-- Battery Type Selection -->
    <div class="mb-6 p-4 bg-slate-900 bg-opacity-50 rounded-lg">
      <label class="block text-sm font-semibold text-slate-300 mb-3">Battery Technology</label>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
        <div 
          v-for="type in batteryTypes"
          :key="type.id"
          @click="localConfig.type = type.id"
          :class="[
            'p-4 border-2 rounded-lg cursor-pointer transition',
            localConfig.type === type.id
              ? 'border-energy-400 bg-energy-400 bg-opacity-10'
              : 'border-slate-600 hover:border-slate-500'
          ]"
        >
          <div class="flex items-start gap-3">
            <span class="text-2xl">{{ type.icon }}</span>
            <div>
              <h3 class="font-semibold text-white text-sm">{{ type.name }}</h3>
              <p class="text-xs text-slate-400 mb-2">{{ type.description }}</p>
              <div class="space-y-1">
                <div class="flex justify-between text-xs">
                  <span class="text-slate-500">Cycles:</span>
                  <span class="text-white">{{ type.cycles.toLocaleString() }}</span>
                </div>
                <div class="flex justify-between text-xs">
                  <span class="text-slate-500">Efficiency:</span>
                  <span class="text-white">{{ (type.efficiency * 100).toFixed(0) }}%</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Battery Parameters -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
      <!-- Capacity Configuration -->
      <div class="space-y-4">
        <h3 class="text-lg font-semibold text-white">⚡ Capacity & Power</h3>
        
        <div>
          <label class="block text-sm font-semibold text-slate-300 mb-2">
            Total Capacity (kWh)
          </label>
          <input 
            v-model.number="localConfig.capacity"
            type="number"
            min="1"
            max="1000"
            step="0.1"
            class="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-energy-400"
          />
          <p class="text-xs text-slate-400 mt-1">Total energy storage capacity</p>
        </div>

        <div>
          <label class="block text-sm font-semibold text-slate-300 mb-2">
            Max Charge Rate (kW)
          </label>
          <input 
            v-model.number="localConfig.maxChargeRate"
            type="number"
            min="0.1"
            max="1000"
            step="0.1"
            class="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-energy-400"
          />
          <p class="text-xs text-slate-400 mt-1">Maximum charging power ({{ (localConfig.maxChargeRate / localConfig.capacity).toFixed(1) }}C rate)</p>
        </div>

        <div>
          <label class="block text-sm font-semibold text-slate-300 mb-2">
            Max Discharge Rate (kW)
          </label>
          <input 
            v-model.number="localConfig.maxDischargeRate"
            type="number"
            min="0.1"
            max="1000"
            step="0.1"
            class="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-energy-400"
          />
          <p class="text-xs text-slate-400 mt-1">Maximum discharge power ({{ (localConfig.maxDischargeRate / localConfig.capacity).toFixed(1) }}C rate)</p>
        </div>
      </div>

      <!-- SOC & Safety -->
      <div class="space-y-4">
        <h3 class="text-lg font-semibold text-white">🛡️ Safety & Limits</h3>
        
        <div>
          <label class="block text-sm font-semibold text-slate-300 mb-2">
            SOC Limits ({{ localConfig.socMin }}% - {{ localConfig.socMax }}%)
          </label>
          <div class="px-4 py-3 bg-slate-900 rounded-lg">
            <div class="flex items-center gap-4 mb-2">
              <span class="text-xs text-slate-400 w-8">Min</span>
              <input 
                v-model.number="localConfig.socMin"
                type="range"
                min="0"
                max="50"
                step="1"
                class="flex-1"
              />
              <span class="text-xs text-white w-8">{{ localConfig.socMin }}%</span>
            </div>
            <div class="flex items-center gap-4">
              <span class="text-xs text-slate-400 w-8">Max</span>
              <input 
                v-model.number="localConfig.socMax"
                type="range"
                min="50"
                max="100"
                step="1"
                class="flex-1"
              />
              <span class="text-xs text-white w-8">{{ localConfig.socMax }}%</span>
            </div>
          </div>
          <p class="text-xs text-slate-400 mt-1">
            Usable capacity: {{ ((localConfig.socMax - localConfig.socMin) / 100 * localConfig.capacity).toFixed(1) }} kWh
          </p>
        </div>

        <div>
          <label class="block text-sm font-semibold text-slate-300 mb-2">
            Battery Efficiency (%)
          </label>
          <input 
            v-model.number="localConfig.efficiency"
            type="number"
            min="50"
            max="99"
            step="1"
            class="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-energy-400"
          />
          <p class="text-xs text-slate-400 mt-1">Round-trip efficiency (charging + discharging)</p>
        </div>

        <div class="flex items-center gap-3 pt-2">
          <input 
            v-model="localConfig.temperatureCompensation"
            type="checkbox"
            id="temp-comp"
            class="w-4 h-4 rounded"
          />
          <label for="temp-comp" class="text-sm text-slate-300">
            Enable temperature compensation
          </label>
        </div>
      </div>
    </div>

    <!-- Battery Status Preview -->
    <div class="mb-6 p-4 bg-slate-900 bg-opacity-50 rounded-lg">
      <h3 class="text-sm font-semibold text-slate-300 mb-3">📊 Configuration Summary</h3>
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
        <div>
          <span class="text-slate-400">Technology:</span>
          <div class="font-semibold text-white">{{ selectedBatteryType?.name }}</div>
        </div>
        <div>
          <span class="text-slate-400">Usable Energy:</span>
          <div class="font-semibold text-energy-400">{{ usableCapacity.toFixed(1) }} kWh</div>
        </div>
        <div>
          <span class="text-slate-400">Max Power:</span>
          <div class="font-semibold text-white">{{ localConfig.maxDischargeRate }}kW out / {{ localConfig.maxChargeRate }}kW in</div>
        </div>
        <div>
          <span class="text-slate-400">Estimated Cost:</span>
          <div class="font-semibold text-yellow-400">{{ estimatedCost.toLocaleString() }} ₴</div>
        </div>
      </div>
    </div>

    <!-- Action Buttons -->
    <div class="flex gap-4">
      <button 
        @click="saveConfiguration"
        :disabled="isUpdating"
        class="flex-1 px-6 py-3 bg-energy-400 hover:bg-cyan-300 text-slate-950 font-semibold rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {{ isUpdating ? 'Updating...' : '💾 Save Configuration' }}
      </button>
      
      <button 
        @click="testConfiguration"
        :disabled="isUpdating"
        class="px-6 py-3 bg-blue-600 hover:bg-blue-500 text-white font-semibold rounded-lg transition disabled:opacity-50"
      >
        🧪 Test
      </button>
      
      <button 
        @click="showAdvanced = !showAdvanced"
        class="px-6 py-3 bg-slate-700 hover:bg-slate-600 text-white font-semibold rounded-lg transition"
      >
        {{ showAdvanced ? '🔼' : '🔽' }} Advanced
      </button>
    </div>

    <!-- Advanced Configuration -->
    <div v-if="showAdvanced" class="mt-6 p-4 border-t border-slate-700 space-y-4">
      <h3 class="text-lg font-semibold text-white">⚙️ Advanced Parameters</h3>
      
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div>
          <label class="block text-sm font-semibold text-slate-300 mb-2">
            Degradation Rate (%/cycle)
          </label>
          <input 
            v-model.number="localConfig.degradationRate"
            type="number"
            min="0.0001"
            max="1"
            step="0.0001"
            class="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-energy-400"
          />
        </div>

        <div>
          <label class="block text-sm font-semibold text-slate-300 mb-2">
            Max Cycles
          </label>
          <input 
            v-model.number="localConfig.maxCycles"
            type="number"
            min="100"
            max="50000"
            step="100"
            class="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-energy-400"
          />
        </div>

        <div>
          <label class="block text-sm font-semibold text-slate-300 mb-2">
            Operating Temperature (°C)
          </label>
          <input 
            v-model.number="localConfig.temperature"
            type="number"
            min="-20"
            max="60"
            step="1"
            class="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-energy-400"
          />
        </div>
      </div>
    </div>

    <!-- Success/Error Messages -->
    <div v-if="message" class="mt-4 p-3 rounded-lg" :class="messageClass">
      <p class="text-sm">{{ message }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useBatteryPhysicsStore } from '~/stores/batteryPhysicsStore'

const batteryPhysicsStore = useBatteryPhysicsStore()

// Local configuration state
const localConfig = ref({
  type: 'LFP' as 'LFP' | 'Lead-Acid' | 'VRFB',
  capacity: 10,
  maxChargeRate: 5,
  maxDischargeRate: 10,
  socMin: 10,
  socMax: 90,
  efficiency: 95,
  degradationRate: 0.0000125,
  maxCycles: 8000,
  temperature: 25,
  temperatureCompensation: true
})

// UI state
const showAdvanced = ref(false)
const isUpdating = ref(false)
const message = ref('')
const messageType = ref<'success' | 'error'>('success')

// Battery type definitions
const batteryTypes = [
  {
    id: 'LFP' as const,
    name: 'LFP',
    description: 'Lithium Iron Phosphate',
    icon: '🔋',
    cycles: 8000,
    efficiency: 0.95,
    costPerKwh: 13000
  },
  {
    id: 'Lead-Acid' as const,
    name: 'Lead-Acid',
    description: 'Deep Cycle Lead-Acid',
    icon: '🪫',
    cycles: 600,
    efficiency: 0.85,
    costPerKwh: 5500
  },
  {
    id: 'VRFB' as const,
    name: 'VRFB',
    description: 'Vanadium Redox Flow',
    icon: '🌊',
    cycles: 20000,
    efficiency: 0.75,
    costPerKwh: 22000
  }
]

// Computed properties
const selectedBatteryType = computed(() => 
  batteryTypes.find(type => type.id === localConfig.value.type)
)

const usableCapacity = computed(() => 
  (localConfig.value.socMax - localConfig.value.socMin) / 100 * localConfig.value.capacity
)

const estimatedCost = computed(() => {
  const type = selectedBatteryType.value
  return type ? type.costPerKwh * localConfig.value.capacity : 0
})

const messageClass = computed(() => ({
  'bg-green-900 bg-opacity-30 border border-green-700 text-green-300': messageType.value === 'success',
  'bg-red-900 bg-opacity-30 border border-red-700 text-red-300': messageType.value === 'error'
}))

// Watch for battery type changes to update defaults
watch(() => localConfig.value.type, (newType) => {
  const typeDefaults = {
    'LFP': {
      efficiency: 95,
      degradationRate: 0.0000125,
      maxCycles: 8000
    },
    'Lead-Acid': {
      efficiency: 85,
      degradationRate: 0.00083,
      maxCycles: 600
    },
    'VRFB': {
      efficiency: 75,
      degradationRate: 0.000025,
      maxCycles: 20000
    }
  }
  
  const defaults = typeDefaults[newType]
  Object.assign(localConfig.value, defaults)
})

// Initialize with current battery state
const initializeConfig = () => {
  const currentState = batteryPhysicsStore.state
  localConfig.value = {
    type: currentState.type,
    capacity: currentState.capacity,
    maxChargeRate: currentState.maxChargePower,
    maxDischargeRate: currentState.maxDischargePower,
    socMin: currentState.socMin,
    socMax: currentState.socMax,
    efficiency: 95, // Default, will be updated from API
    degradationRate: 0.0000125,
    maxCycles: 8000,
    temperature: currentState.temperature,
    temperatureCompensation: true
  }
}

// Methods
const saveConfiguration = async () => {
  isUpdating.value = true
  message.value = ''
  
  try {
    await batteryPhysicsStore.updateBatteryConfig({
      type: localConfig.value.type,
      capacity: localConfig.value.capacity,
      cRateCharge: localConfig.value.maxChargeRate / localConfig.value.capacity,
      cRateDischarge: localConfig.value.maxDischargeRate / localConfig.value.capacity,
      socMin: localConfig.value.socMin / 100,
      socMax: localConfig.value.socMax / 100,
      efficiency: localConfig.value.efficiency / 100
    })
    
    showMessage('Configuration saved successfully!', 'success')
  } catch (error) {
    showMessage('Failed to save configuration', 'error')
    console.error('Config save error:', error)
  } finally {
    isUpdating.value = false
  }
}

const testConfiguration = async () => {
  try {
    // Test with a small charge command
    await batteryPhysicsStore.charge(1) // 1kW charge
    showMessage('Test charge command sent successfully!', 'success')
    
    // Reset to idle after 5 seconds
    setTimeout(() => {
      batteryPhysicsStore.idle()
    }, 5000)
  } catch (error) {
    showMessage('Test failed', 'error')
  }
}

const resetToDefaults = () => {
  localConfig.value = {
    type: 'LFP',
    capacity: 10,
    maxChargeRate: 5,
    maxDischargeRate: 10,
    socMin: 10,
    socMax: 90,
    efficiency: 95,
    degradationRate: 0.0000125,
    maxCycles: 8000,
    temperature: 25,
    temperatureCompensation: true
  }
  showMessage('Reset to default values', 'success')
}

const applyPreset = (preset: 'residential' | 'commercial') => {
  const presets = {
    residential: {
      type: 'LFP' as const,
      capacity: 13.5,
      maxChargeRate: 5,
      maxDischargeRate: 5,
      socMin: 10,
      socMax: 95,
      efficiency: 95
    },
    commercial: {
      type: 'LFP' as const,
      capacity: 100,
      maxChargeRate: 50,
      maxDischargeRate: 50,
      socMin: 15,
      socMax: 85,
      efficiency: 92
    }
  }
  
  Object.assign(localConfig.value, presets[preset])
  showMessage(`Applied ${preset} preset configuration`, 'success')
}

const showMessage = (text: string, type: 'success' | 'error') => {
  message.value = text
  messageType.value = type
  
  setTimeout(() => {
    message.value = ''
  }, 5000)
}

// Initialize on mount
onMounted(() => {
  initializeConfig()
})
</script>