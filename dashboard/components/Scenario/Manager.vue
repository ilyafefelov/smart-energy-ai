<template>
  <div class="bg-slate-800 bg-opacity-40 border border-slate-700 rounded-lg p-6">
    <div class="flex items-center justify-between mb-6">
      <div>
        <h2 class="text-xl font-bold text-white mb-2">📋 Scenario Management</h2>
        <p class="text-sm text-slate-400">Configure different operational scenarios and load profiles</p>
      </div>
      <div class="flex gap-2">
        <button 
          @click="showCreateModal = true"
          class="px-4 py-2 bg-green-600 hover:bg-green-500 text-white font-semibold rounded-lg transition"
        >
          ➕ New Scenario
        </button>
      </div>
    </div>

    <!-- Scenario Selector -->
    <div class="mb-6">
      <label class="block text-sm font-semibold text-slate-300 mb-3">Active Scenario</label>
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div 
          v-for="scenario in scenarios"
          :key="scenario.id"
          @click="selectScenario(scenario.id)"
          :class="[
            'p-4 border-2 rounded-lg cursor-pointer transition',
            activeScenario === scenario.id
              ? 'border-energy-400 bg-energy-400 bg-opacity-10'
              : 'border-slate-600 hover:border-slate-500'
          ]"
        >
          <div class="flex items-start gap-3">
            <span class="text-2xl">{{ scenario.icon }}</span>
            <div>
              <h3 class="font-semibold text-white text-sm">{{ scenario.name }}</h3>
              <p class="text-xs text-slate-400 mb-2">{{ scenario.description }}</p>
              <div class="space-y-1">
                <div class="flex justify-between text-xs">
                  <span class="text-slate-500">Peak Load:</span>
                  <span class="text-white">{{ scenario.peakLoad }} kW</span>
                </div>
                <div class="flex justify-between text-xs">
                  <span class="text-slate-500">Base Load:</span>
                  <span class="text-white">{{ scenario.baseLoad }} kW</span>
                </div>
                <div class="flex justify-between text-xs">
                  <span class="text-slate-500">Daily Energy:</span>
                  <span class="text-energy-400">{{ scenario.dailyEnergy.toFixed(1) }} kWh</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Load Profile Visualization -->
    <div class="mb-6 p-4 bg-slate-900 bg-opacity-50 rounded-lg">
      <h3 class="text-lg font-semibold text-white mb-4">📈 Load Profile Preview</h3>
      
      <div class="relative h-48 bg-slate-800 rounded-lg p-4">
        <!-- Chart placeholder - in real implementation would use Chart.js or similar -->
        <div class="w-full h-full flex items-end justify-between gap-1">
          <div 
            v-for="(hour, index) in 24"
            :key="index"
            class="flex-1 bg-gradient-to-t from-blue-600 to-blue-400 rounded-t"
            :style="{ height: (getHourlyLoad(index) / selectedScenario.peakLoad * 100) + '%' }"
            :title="`${index}:00 - ${getHourlyLoad(index).toFixed(1)} kW`"
          ></div>
        </div>
        
        <!-- X-axis labels -->
        <div class="flex justify-between text-xs text-slate-400 mt-2">
          <span>0</span>
          <span>6</span>
          <span>12</span>
          <span>18</span>
          <span>24</span>
        </div>
      </div>

      <!-- Load Statistics -->
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
        <div>
          <span class="text-slate-400 text-sm">Peak Load:</span>
          <div class="font-semibold text-red-400 text-lg">{{ selectedScenario.peakLoad }} kW</div>
        </div>
        <div>
          <span class="text-slate-400 text-sm">Average Load:</span>
          <div class="font-semibold text-blue-400 text-lg">{{ averageLoad.toFixed(1) }} kW</div>
        </div>
        <div>
          <span class="text-slate-400 text-sm">Load Factor:</span>
          <div class="font-semibold text-green-400 text-lg">{{ loadFactor.toFixed(1) }}%</div>
        </div>
        <div>
          <span class="text-slate-400 text-sm">Daily Energy:</span>
          <div class="font-semibold text-energy-400 text-lg">{{ selectedScenario.dailyEnergy.toFixed(0) }} kWh</div>
        </div>
      </div>
    </div>

    <!-- Scenario Configuration -->
    <div v-if="selectedScenario" class="space-y-6">
      <!-- Basic Parameters -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div class="bg-slate-900 bg-opacity-50 rounded-lg p-4">
          <h4 class="text-lg font-semibold text-white mb-4">⚡ Load Parameters</h4>
          
          <div class="space-y-4">
            <div>
              <label class="block text-sm font-semibold text-slate-300 mb-2">
                Peak Load (kW)
              </label>
              <input 
                v-model.number="selectedScenario.peakLoad"
                type="number"
                min="0"
                step="0.1"
                class="w-full bg-slate-800 border border-slate-600 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-energy-400"
              />
            </div>

            <div>
              <label class="block text-sm font-semibold text-slate-300 mb-2">
                Base Load (kW)
              </label>
              <input 
                v-model.number="selectedScenario.baseLoad"
                type="number"
                min="0"
                step="0.1"
                class="w-full bg-slate-800 border border-slate-600 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-energy-400"
              />
            </div>

            <div>
              <label class="block text-sm font-semibold text-slate-300 mb-2">
                Load Variability
              </label>
              <input 
                v-model.number="selectedScenario.variability"
                type="range"
                min="0"
                max="100"
                step="5"
                class="w-full"
              />
              <div class="flex justify-between text-xs text-slate-400 mt-1">
                <span>Constant</span>
                <span>{{ selectedScenario.variability }}%</span>
                <span>Highly Variable</span>
              </div>
            </div>
          </div>
        </div>

        <div class="bg-slate-900 bg-opacity-50 rounded-lg p-4">
          <h4 class="text-lg font-semibold text-white mb-4">🕐 Time Factors</h4>
          
          <div class="space-y-4">
            <div>
              <label class="block text-sm font-semibold text-slate-300 mb-2">
                Peak Hours Start
              </label>
              <input 
                v-model.number="selectedScenario.peakHoursStart"
                type="number"
                min="0"
                max="23"
                class="w-full bg-slate-800 border border-slate-600 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-energy-400"
              />
            </div>

            <div>
              <label class="block text-sm font-semibold text-slate-300 mb-2">
                Peak Hours End
              </label>
              <input 
                v-model.number="selectedScenario.peakHoursEnd"
                type="number"
                min="0"
                max="23"
                class="w-full bg-slate-800 border border-slate-600 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-energy-400"
              />
            </div>

            <div>
              <label class="block text-sm font-semibold text-slate-300 mb-2">
                Weekend Factor (%)
              </label>
              <input 
                v-model.number="selectedScenario.weekendFactor"
                type="number"
                min="10"
                max="150"
                step="5"
                class="w-full bg-slate-800 border border-slate-600 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-energy-400"
              />
              <p class="text-xs text-slate-400 mt-1">Weekend load as % of weekday load</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Advanced Configuration -->
      <div v-if="showAdvanced" class="bg-slate-900 bg-opacity-50 rounded-lg p-4">
        <h4 class="text-lg font-semibold text-white mb-4">⚙️ Advanced Parameters</h4>
        
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label class="block text-sm font-semibold text-slate-300 mb-2">
              Seasonal Variation (%)
            </label>
            <input 
              v-model.number="selectedScenario.seasonalVariation"
              type="number"
              min="0"
              max="50"
              step="1"
              class="w-full bg-slate-800 border border-slate-600 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-energy-400"
            />
          </div>

          <div>
            <label class="block text-sm font-semibold text-slate-300 mb-2">
              Power Factor
            </label>
            <input 
              v-model.number="selectedScenario.powerFactor"
              type="number"
              min="0.7"
              max="1.0"
              step="0.01"
              class="w-full bg-slate-800 border border-slate-600 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-energy-400"
            />
          </div>

          <div>
            <label class="block text-sm font-semibold text-slate-300 mb-2">
              Emergency Load (kW)
            </label>
            <input 
              v-model.number="selectedScenario.emergencyLoad"
              type="number"
              min="0"
              step="0.1"
              class="w-full bg-slate-800 border border-slate-600 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-energy-400"
            />
          </div>
        </div>
      </div>

      <!-- Scenario Actions -->
      <div class="flex gap-4">
        <button 
          @click="saveScenario"
          :disabled="isSaving"
          class="flex-1 px-6 py-3 bg-energy-400 hover:bg-cyan-300 text-slate-950 font-semibold rounded-lg transition disabled:opacity-50"
        >
          {{ isSaving ? 'Saving...' : '💾 Save Scenario' }}
        </button>
        
        <button 
          @click="testScenario"
          class="px-6 py-3 bg-blue-600 hover:bg-blue-500 text-white font-semibold rounded-lg transition"
        >
          🧪 Test Load
        </button>
        
        <button 
          @click="duplicateScenario"
          class="px-6 py-3 bg-purple-600 hover:bg-purple-500 text-white font-semibold rounded-lg transition"
        >
          📋 Duplicate
        </button>
        
        <button 
          @click="showAdvanced = !showAdvanced"
          class="px-6 py-3 bg-slate-700 hover:bg-slate-600 text-white font-semibold rounded-lg transition"
        >
          {{ showAdvanced ? '🔼' : '🔽' }} Advanced
        </button>
      </div>
    </div>

    <!-- Create New Scenario Modal -->
    <div v-if="showCreateModal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div class="bg-slate-800 rounded-lg p-6 w-full max-w-md">
        <h3 class="text-lg font-bold text-white mb-4">Create New Scenario</h3>
        
        <div class="space-y-4">
          <div>
            <label class="block text-sm font-semibold text-slate-300 mb-2">Scenario Name</label>
            <input 
              v-model="newScenario.name"
              type="text"
              class="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-energy-400"
              placeholder="e.g., Office Building"
            />
          </div>

          <div>
            <label class="block text-sm font-semibold text-slate-300 mb-2">Description</label>
            <textarea 
              v-model="newScenario.description"
              class="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-energy-400"
              rows="3"
              placeholder="Brief description of this load profile"
            ></textarea>
          </div>

          <div>
            <label class="block text-sm font-semibold text-slate-300 mb-2">Base Template</label>
            <select 
              v-model="newScenario.template"
              class="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-energy-400"
            >
              <option value="standard">Standard Workday</option>
              <option value="manufacturing">Manufacturing</option>
              <option value="retail">Retail Store</option>
              <option value="residential">Residential</option>
            </select>
          </div>
        </div>

        <div class="flex gap-3 mt-6">
          <button 
            @click="createScenario"
            class="flex-1 px-4 py-2 bg-green-600 hover:bg-green-500 text-white font-semibold rounded-lg transition"
          >
            Create
          </button>
          <button 
            @click="showCreateModal = false"
            class="px-4 py-2 bg-slate-600 hover:bg-slate-500 text-white font-semibold rounded-lg transition"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>

    <!-- Status Messages -->
    <div v-if="message" class="mt-4 p-3 rounded-lg" :class="messageClass">
      <p class="text-sm">{{ message }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

interface Scenario {
  id: string
  name: string
  description: string
  icon: string
  peakLoad: number
  baseLoad: number
  dailyEnergy: number
  peakHoursStart: number
  peakHoursEnd: number
  variability: number
  weekendFactor: number
  seasonalVariation: number
  powerFactor: number
  emergencyLoad: number
  customProfile?: number[] // 24-hour profile
}

// Default scenarios
const scenarios = ref<Scenario[]>([
  {
    id: 'standard',
    name: 'Standard Workday',
    description: '9-18 office hours with moderate peaks',
    icon: '🏢',
    peakLoad: 10.0,
    baseLoad: 2.0,
    dailyEnergy: 120,
    peakHoursStart: 9,
    peakHoursEnd: 18,
    variability: 20,
    weekendFactor: 30,
    seasonalVariation: 15,
    powerFactor: 0.95,
    emergencyLoad: 3.0
  },
  {
    id: 'manufacturing',
    name: 'Multi-Shift Manufacturing',
    description: '24/7 operation with shift peaks',
    icon: '🏭',
    peakLoad: 50.0,
    baseLoad: 20.0,
    dailyEnergy: 800,
    peakHoursStart: 6,
    peakHoursEnd: 22,
    variability: 40,
    weekendFactor: 80,
    seasonalVariation: 25,
    powerFactor: 0.85,
    emergencyLoad: 15.0
  },
  {
    id: 'retail',
    name: 'Retail Store',
    description: '10-21 operation with evening peaks',
    icon: '🛒',
    peakLoad: 25.0,
    baseLoad: 5.0,
    dailyEnergy: 300,
    peakHoursStart: 10,
    peakHoursEnd: 21,
    variability: 35,
    weekendFactor: 120,
    seasonalVariation: 30,
    powerFactor: 0.92,
    emergencyLoad: 8.0
  },
  {
    id: 'residential',
    name: 'Residential Complex',
    description: 'Morning/evening peaks, low midday',
    icon: '🏠',
    peakLoad: 15.0,
    baseLoad: 3.0,
    dailyEnergy: 180,
    peakHoursStart: 18,
    peakHoursEnd: 22,
    variability: 25,
    weekendFactor: 110,
    seasonalVariation: 40,
    powerFactor: 0.98,
    emergencyLoad: 5.0
  }
])

// UI state
const activeScenario = ref('standard')
const showAdvanced = ref(false)
const showCreateModal = ref(false)
const isSaving = ref(false)
const message = ref('')
const messageType = ref<'success' | 'error'>('success')

// New scenario form
const newScenario = ref({
  name: '',
  description: '',
  template: 'standard'
})

// Computed properties
const selectedScenario = computed(() => 
  scenarios.value.find(s => s.id === activeScenario.value) || scenarios.value[0]
)

const averageLoad = computed(() => {
  const profile = Array.from({ length: 24 }, (_, i) => getHourlyLoad(i))
  return profile.reduce((sum, load) => sum + load, 0) / 24
})

const loadFactor = computed(() => {
  if (selectedScenario.value.peakLoad === 0) return 0
  return (averageLoad.value / selectedScenario.value.peakLoad) * 100
})

const messageClass = computed(() => ({
  'bg-green-900 bg-opacity-30 border border-green-700 text-green-300': messageType.value === 'success',
  'bg-red-900 bg-opacity-30 border border-red-700 text-red-300': messageType.value === 'error'
}))

// Methods
const getHourlyLoad = (hour: number): number => {
  const scenario = selectedScenario.value
  
  // Generate load profile based on scenario parameters
  let load = scenario.baseLoad
  
  // Add peak hours boost
  if (hour >= scenario.peakHoursStart && hour <= scenario.peakHoursEnd) {
    const peakProgress = 1 - Math.abs(hour - (scenario.peakHoursStart + scenario.peakHoursEnd) / 2) / 
                           ((scenario.peakHoursEnd - scenario.peakHoursStart) / 2)
    load += (scenario.peakLoad - scenario.baseLoad) * Math.max(0, peakProgress)
  }
  
  // Add variability
  const variation = (Math.random() - 0.5) * (scenario.variability / 100) * scenario.peakLoad
  load += variation
  
  return Math.max(scenario.baseLoad * 0.5, Math.min(load, scenario.peakLoad * 1.1))
}

const selectScenario = (scenarioId: string) => {
  activeScenario.value = scenarioId
  showMessage(`Switched to ${selectedScenario.value.name} scenario`, 'success')
}

const saveScenario = async () => {
  isSaving.value = true
  try {
    // Here you would save to API
    // await $fetch('/api/scenarios/save', { method: 'POST', body: selectedScenario.value })
    
    // Update daily energy calculation
    selectedScenario.value.dailyEnergy = averageLoad.value * 24
    
    // Simulate save delay
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    showMessage('Scenario saved successfully!', 'success')
  } catch (error) {
    showMessage('Failed to save scenario', 'error')
  } finally {
    isSaving.value = false
  }
}

const testScenario = () => {
  // Simulate applying the load profile
  showMessage(`Testing ${selectedScenario.value.name} load profile...`, 'success')
  
  // In real implementation, this would send the load profile to the simulation
  setTimeout(() => {
    showMessage('Load profile applied successfully!', 'success')
  }, 2000)
}

const duplicateScenario = () => {
  const original = selectedScenario.value
  const duplicate: Scenario = {
    ...original,
    id: `${original.id}_copy_${Date.now()}`,
    name: `${original.name} (Copy)`,
    description: `Copy of ${original.description}`
  }
  
  scenarios.value.push(duplicate)
  activeScenario.value = duplicate.id
  showMessage('Scenario duplicated successfully!', 'success')
}

const createScenario = () => {
  if (!newScenario.value.name.trim()) {
    showMessage('Please enter a scenario name', 'error')
    return
  }
  
  const template = scenarios.value.find(s => s.id === newScenario.value.template)
  if (!template) return
  
  const newId = `custom_${Date.now()}`
  const newScenarioObj: Scenario = {
    ...template,
    id: newId,
    name: newScenario.value.name,
    description: newScenario.value.description || 'Custom scenario',
    icon: '⚙️'
  }
  
  scenarios.value.push(newScenarioObj)
  activeScenario.value = newId
  showCreateModal.value = false
  
  // Reset form
  newScenario.value = {
    name: '',
    description: '',
    template: 'standard'
  }
  
  showMessage('New scenario created successfully!', 'success')
}

const showMessage = (text: string, type: 'success' | 'error') => {
  message.value = text
  messageType.value = type
  
  setTimeout(() => {
    message.value = ''
  }, 5000)
}
</script>