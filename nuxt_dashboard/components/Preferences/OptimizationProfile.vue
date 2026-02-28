<template>
  <div class="bg-slate-800 bg-opacity-40 border border-slate-700 rounded-lg p-6">
    <div class="flex items-center justify-between mb-6">
      <div>
        <h2 class="text-xl font-bold text-white mb-2">🎯 Optimization Preferences</h2>
        <p class="text-sm text-slate-400">Configure your energy optimization strategy and priorities</p>
      </div>
    </div>

    <!-- Strategy Selection -->
    <div class="mb-6">
      <h3 class="text-lg font-semibold text-white mb-4">Choose Your Optimization Strategy</h3>
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div 
          v-for="strategy in strategies"
          :key="strategy.id"
          @click="selectStrategy(strategy.id)"
          :class="[
            'p-5 border-2 rounded-lg cursor-pointer transition',
            selectedStrategy === strategy.id
              ? 'border-energy-400 bg-energy-400 bg-opacity-10'
              : 'border-slate-600 hover:border-slate-500'
          ]"
        >
          <div class="text-center">
            <div class="text-3xl mb-3">{{ strategy.icon }}</div>
            <h4 class="font-semibold text-white mb-2">{{ strategy.name }}</h4>
            <p class="text-xs text-slate-400 mb-3">{{ strategy.description }}</p>
            
            <!-- Strategy Priorities -->
            <div class="space-y-2">
              <div class="flex justify-between text-xs">
                <span class="text-slate-500">Profit:</span>
                <span class="text-green-400 font-semibold">{{ strategy.priorities.profit }}%</span>
              </div>
              <div class="flex justify-between text-xs">
                <span class="text-slate-500">Battery Health:</span>
                <span class="text-purple-400 font-semibold">{{ strategy.priorities.health }}%</span>
              </div>
              <div class="flex justify-between text-xs">
                <span class="text-slate-500">Reliability:</span>
                <span class="text-blue-400 font-semibold">{{ strategy.priorities.reliability }}%</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Custom Strategy Configuration -->
    <div v-if="selectedStrategy === 'custom'" class="mb-6 p-4 bg-slate-900 bg-opacity-50 rounded-lg">
      <h3 class="text-lg font-semibold text-white mb-4">🛠️ Custom Strategy Configuration</h3>
      
      <div class="space-y-6">
        <!-- Priority Sliders -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div>
            <label class="block text-sm font-semibold text-slate-300 mb-2">
              Profit Priority ({{ customPriorities.profit }}%)
            </label>
            <input 
              v-model.number="customPriorities.profit"
              type="range"
              min="0"
              max="100"
              step="5"
              class="w-full"
              @input="adjustPriorities('profit')"
            />
            <p class="text-xs text-slate-400 mt-1">Focus on maximizing energy arbitrage profits</p>
          </div>

          <div>
            <label class="block text-sm font-semibold text-slate-300 mb-2">
              Battery Health Priority ({{ customPriorities.health }}%)
            </label>
            <input 
              v-model.number="customPriorities.health"
              type="range"
              min="0"
              max="100"
              step="5"
              class="w-full"
              @input="adjustPriorities('health')"
            />
            <p class="text-xs text-slate-400 mt-1">Minimize battery degradation and extend lifespan</p>
          </div>

          <div>
            <label class="block text-sm font-semibold text-slate-300 mb-2">
              Reliability Priority ({{ customPriorities.reliability }}%)
            </label>
            <input 
              v-model.number="customPriorities.reliability"
              type="range"
              min="0"
              max="100"
              step="5"
              class="w-full"
              @input="adjustPriorities('reliability')"
            />
            <p class="text-xs text-slate-400 mt-1">Maintain backup power capacity for outages</p>
          </div>
        </div>

        <!-- Priority Visualization -->
        <div class="mt-4">
          <div class="flex items-center justify-between text-sm text-slate-300 mb-2">
            <span>Priority Distribution</span>
            <span>Total: {{ totalPriority }}%</span>
          </div>
          <div class="w-full bg-slate-800 rounded-full h-6 overflow-hidden flex">
            <div 
              class="bg-gradient-to-r from-green-500 to-green-400 transition-all duration-300"
              :style="{ width: customPriorities.profit + '%' }"
            ></div>
            <div 
              class="bg-gradient-to-r from-purple-500 to-purple-400 transition-all duration-300"
              :style="{ width: customPriorities.health + '%' }"
            ></div>
            <div 
              class="bg-gradient-to-r from-blue-500 to-blue-400 transition-all duration-300"
              :style="{ width: customPriorities.reliability + '%' }"
            ></div>
          </div>
          <div class="flex justify-between text-xs text-slate-400 mt-1">
            <span>💰 Profit: {{ customPriorities.profit }}%</span>
            <span>💊 Health: {{ customPriorities.health }}%</span>
            <span>🛡️ Reliability: {{ customPriorities.reliability }}%</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Strategy Details -->
    <div class="mb-6 p-4 bg-slate-900 bg-opacity-50 rounded-lg">
      <h3 class="text-lg font-semibold text-white mb-4">📋 Strategy Details</h3>
      
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <h4 class="font-semibold text-slate-300 mb-3">🎯 Optimization Behavior</h4>
          <div class="space-y-2 text-sm">
            <div v-for="behavior in currentStrategy.behaviors" :key="behavior" class="flex items-start gap-2">
              <span class="text-green-400 mt-1">✓</span>
              <span class="text-slate-300">{{ behavior }}</span>
            </div>
          </div>
        </div>

        <div>
          <h4 class="font-semibold text-slate-300 mb-3">⚠️ Trade-offs</h4>
          <div class="space-y-2 text-sm">
            <div v-for="tradeoff in currentStrategy.tradeoffs" :key="tradeoff" class="flex items-start gap-2">
              <span class="text-orange-400 mt-1">⚠</span>
              <span class="text-slate-300">{{ tradeoff }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Advanced Settings -->
    <div v-if="showAdvanced" class="mb-6 p-4 bg-slate-900 bg-opacity-50 rounded-lg">
      <h3 class="text-lg font-semibold text-white mb-4">⚙️ Advanced Optimization Settings</h3>
      
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <div>
          <label class="block text-sm font-semibold text-slate-300 mb-2">
            Min SOC Reserve (%)
          </label>
          <input 
            v-model.number="advancedSettings.minSocReserve"
            type="number"
            min="5"
            max="50"
            class="w-full bg-slate-800 border border-slate-600 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-energy-400"
          />
          <p class="text-xs text-slate-400 mt-1">Always keep this much charge for emergencies</p>
        </div>

        <div>
          <label class="block text-sm font-semibold text-slate-300 mb-2">
            Max C-Rate (C)
          </label>
          <input 
            v-model.number="advancedSettings.maxCRate"
            type="number"
            min="0.1"
            max="3.0"
            step="0.1"
            class="w-full bg-slate-800 border border-slate-600 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-energy-400"
          />
          <p class="text-xs text-slate-400 mt-1">Maximum charge/discharge rate relative to capacity</p>
        </div>

        <div>
          <label class="block text-sm font-semibold text-slate-300 mb-2">
            Price Threshold (₴/kWh)
          </label>
          <input 
            v-model.number="advancedSettings.priceThreshold"
            type="number"
            min="5"
            max="20"
            step="0.1"
            class="w-full bg-slate-800 border border-slate-600 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-energy-400"
          />
          <p class="text-xs text-slate-400 mt-1">Only trade when price spread exceeds this</p>
        </div>

        <div>
          <label class="block text-sm font-semibold text-slate-300 mb-2">
            Forecast Horizon (hours)
          </label>
          <input 
            v-model.number="advancedSettings.forecastHorizon"
            type="number"
            min="6"
            max="48"
            class="w-full bg-slate-800 border border-slate-600 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-energy-400"
          />
          <p class="text-xs text-slate-400 mt-1">How far ahead to optimize</p>
        </div>

        <div>
          <label class="block text-sm font-semibold text-slate-300 mb-2">
            Rebalance Frequency (hours)
          </label>
          <input 
            v-model.number="advancedSettings.rebalanceFreq"
            type="number"
            min="1"
            max="24"
            class="w-full bg-slate-800 border border-slate-600 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-energy-400"
          />
          <p class="text-xs text-slate-400 mt-1">How often to recalculate optimization</p>
        </div>

        <div>
          <label class="block text-sm font-semibold text-slate-300 mb-2">
            Risk Level
          </label>
          <select 
            v-model="advancedSettings.riskLevel"
            class="w-full bg-slate-800 border border-slate-600 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-energy-400"
          >
            <option value="conservative">Conservative</option>
            <option value="moderate">Moderate</option>
            <option value="aggressive">Aggressive</option>
          </select>
          <p class="text-xs text-slate-400 mt-1">Trading aggressiveness level</p>
        </div>
      </div>
    </div>

    <!-- Expected Outcomes -->
    <div class="mb-6 p-4 bg-gradient-to-r from-slate-800 to-slate-700 bg-opacity-60 border border-slate-600 rounded-lg">
      <h3 class="text-lg font-semibold text-white mb-4">📊 Expected Outcomes</h3>
      
      <div class="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div class="text-center">
          <div class="text-2xl font-bold text-green-400">{{ estimatedDailyProfit.toFixed(0) }} ₴</div>
          <div class="text-sm text-slate-400">Daily Profit</div>
        </div>
        <div class="text-center">
          <div class="text-2xl font-bold text-purple-400">{{ estimatedLifespan.toFixed(1) }} years</div>
          <div class="text-sm text-slate-400">Battery Lifespan</div>
        </div>
        <div class="text-center">
          <div class="text-2xl font-bold text-blue-400">{{ estimatedUptime.toFixed(1) }}%</div>
          <div class="text-sm text-slate-400">System Uptime</div>
        </div>
        <div class="text-center">
          <div class="text-2xl font-bold text-energy-400">{{ estimatedROI.toFixed(0) }}%</div>
          <div class="text-sm text-slate-400">Annual ROI</div>
        </div>
      </div>
    </div>

    <!-- Action Buttons -->
    <div class="flex gap-4">
      <button 
        @click="savePreferences"
        :disabled="isSaving"
        class="flex-1 px-6 py-3 bg-energy-400 hover:bg-cyan-300 text-slate-950 font-semibold rounded-lg transition disabled:opacity-50"
      >
        {{ isSaving ? 'Saving...' : '💾 Save Preferences' }}
      </button>
      
      <button 
        @click="resetToDefaults"
        class="px-6 py-3 bg-slate-700 hover:bg-slate-600 text-white font-semibold rounded-lg transition"
      >
        🔄 Reset
      </button>
      
      <button 
        @click="showAdvanced = !showAdvanced"
        class="px-6 py-3 bg-blue-600 hover:bg-blue-500 text-white font-semibold rounded-lg transition"
      >
        {{ showAdvanced ? '🔼' : '🔽' }} Advanced
      </button>
    </div>

    <!-- Status Messages -->
    <div v-if="message" class="mt-4 p-3 rounded-lg" :class="messageClass">
      <p class="text-sm">{{ message }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

interface Strategy {
  id: string
  name: string
  description: string
  icon: string
  priorities: {
    profit: number
    health: number
    reliability: number
  }
  behaviors: string[]
  tradeoffs: string[]
}

// Predefined strategies
const strategies = ref<Strategy[]>([
  {
    id: 'max-earn',
    name: 'Max Earn',
    description: 'Maximize arbitrage profits',
    icon: '💰',
    priorities: { profit: 70, health: 15, reliability: 15 },
    behaviors: [
      'Aggressive buy/sell based on price forecasts',
      'Deep discharge cycles for maximum arbitrage',
      'High C-rate charging/discharging when profitable',
      'Focus on peak/off-peak price differences'
    ],
    tradeoffs: [
      'Higher battery degradation',
      'Reduced backup power availability',
      'More frequent cycling'
    ]
  },
  {
    id: 'balanced',
    name: 'Balanced',
    description: 'Balance profit, health, and reliability',
    icon: '⚖️',
    priorities: { profit: 40, health: 30, reliability: 30 },
    behaviors: [
      'Moderate trading with health consideration',
      'Maintain minimum backup power reserve',
      'Limit C-rates to preserve battery life',
      'Trade when clear profit opportunities exist'
    ],
    tradeoffs: [
      'Lower maximum profits',
      'Moderate battery wear',
      'Good overall performance'
    ]
  },
  {
    id: 'max-health',
    name: 'Max Battery Health',
    description: 'Minimize degradation',
    icon: '💊',
    priorities: { profit: 20, health: 60, reliability: 20 },
    behaviors: [
      'Conservative C-rates (0.3C max)',
      'Avoid deep discharge cycles',
      'Maintain SOC between 20-80%',
      'Trade only during extreme price spreads'
    ],
    tradeoffs: [
      'Significantly lower profits',
      'Reduced energy utilization',
      'Maximum battery lifespan'
    ]
  },
  {
    id: 'max-charge',
    name: 'Max Charge',
    description: 'Always ready for backup power',
    icon: '🔋',
    priorities: { profit: 25, health: 25, reliability: 50 },
    behaviors: [
      'Maintain high SOC (80%+) at all times',
      'Only discharge for high-value opportunities',
      'Rapid recharge after any discharge',
      'Prioritize grid stability services'
    ],
    tradeoffs: [
      'Limited arbitrage opportunities',
      'Higher standby losses',
      'Excellent backup power readiness'
    ]
  },
  {
    id: 'custom',
    name: 'Custom',
    description: 'Define your own strategy',
    icon: '🛠️',
    priorities: { profit: 33, health: 33, reliability: 34 },
    behaviors: ['User-defined optimization parameters'],
    tradeoffs: ['Depends on your configuration']
  }
])

// State
const selectedStrategy = ref('balanced')
const customPriorities = ref({ profit: 33, health: 33, reliability: 34 })
const showAdvanced = ref(false)
const isSaving = ref(false)
const message = ref('')
const messageType = ref<'success' | 'error'>('success')

const advancedSettings = ref({
  minSocReserve: 15, // %
  maxCRate: 1.0, // C
  priceThreshold: 2.0, // ₴/kWh
  forecastHorizon: 24, // hours
  rebalanceFreq: 4, // hours
  riskLevel: 'moderate' as 'conservative' | 'moderate' | 'aggressive'
})

// Computed
const currentStrategy = computed(() => 
  strategies.value.find(s => s.id === selectedStrategy.value) || strategies.value[1]
)

const totalPriority = computed(() => 
  customPriorities.value.profit + customPriorities.value.health + customPriorities.value.reliability
)

const estimatedDailyProfit = computed(() => {
  const priorities = selectedStrategy.value === 'custom' 
    ? customPriorities.value 
    : currentStrategy.value.priorities
  
  // Simplified calculation based on profit priority
  const baseProfitPotential = 150 // ₴ per day for max arbitrage
  return baseProfitPotential * (priorities.profit / 100) * getRiskMultiplier()
})

const estimatedLifespan = computed(() => {
  const priorities = selectedStrategy.value === 'custom' 
    ? customPriorities.value 
    : currentStrategy.value.priorities
  
  // Base lifespan of 10 years, reduced by aggressive usage
  const baseLifespan = 10
  const healthFactor = priorities.health / 100
  const aggressionPenalty = (priorities.profit / 100) * 0.3 // Up to 30% reduction
  return baseLifespan * healthFactor * (1 - aggressionPenalty) + 5 // Min 5 years
})

const estimatedUptime = computed(() => {
  const priorities = selectedStrategy.value === 'custom' 
    ? customPriorities.value 
    : currentStrategy.value.priorities
  
  // Base uptime 95%, improved by reliability focus
  const baseUptime = 95
  const reliabilityBonus = (priorities.reliability / 100) * 4 // Up to 4% bonus
  return Math.min(99.5, baseUptime + reliabilityBonus)
})

const estimatedROI = computed(() => {
  const annualProfit = estimatedDailyProfit.value * 365
  const systemCost = 130000 // ₴ for 10kWh LFP system
  return (annualProfit / systemCost) * 100
})

const messageClass = computed(() => ({
  'bg-green-900 bg-opacity-30 border border-green-700 text-green-300': messageType.value === 'success',
  'bg-red-900 bg-opacity-30 border border-red-700 text-red-300': messageType.value === 'error'
}))

// Methods
const getRiskMultiplier = () => {
  const multipliers = { conservative: 0.7, moderate: 1.0, aggressive: 1.3 }
  return multipliers[advancedSettings.value.riskLevel]
}

const selectStrategy = (strategyId: string) => {
  selectedStrategy.value = strategyId
  
  if (strategyId !== 'custom') {
    const strategy = strategies.value.find(s => s.id === strategyId)
    if (strategy) {
      customPriorities.value = { ...strategy.priorities }
    }
  }
  
  showMessage(`Selected ${currentStrategy.value.name} strategy`, 'success')
}

const adjustPriorities = (changedPriority: 'profit' | 'health' | 'reliability') => {
  // Ensure priorities always add up to 100%
  const total = totalPriority.value
  if (total !== 100) {
    const diff = 100 - total
    const otherPriorities = Object.keys(customPriorities.value).filter(k => k !== changedPriority) as Array<keyof typeof customPriorities.value>
    
    // Distribute the difference among other priorities
    otherPriorities.forEach((priority, index) => {
      if (index === otherPriorities.length - 1) {
        // Last priority gets the remaining difference
        customPriorities.value[priority] = Math.max(0, customPriorities.value[priority] + diff - (Math.floor(diff / otherPriorities.length) * (otherPriorities.length - 1)))
      } else {
        customPriorities.value[priority] = Math.max(0, customPriorities.value[priority] + Math.floor(diff / otherPriorities.length))
      }
    })
  }
}

const savePreferences = async () => {
  isSaving.value = true
  
  try {
    const preferences = {
      strategy: selectedStrategy.value,
      priorities: selectedStrategy.value === 'custom' ? customPriorities.value : currentStrategy.value.priorities,
      advancedSettings: advancedSettings.value
    }
    
    // Here you would save to API
    // await $fetch('/api/preferences/save', { method: 'POST', body: preferences })
    
    // Simulate save delay
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    showMessage('Optimization preferences saved successfully!', 'success')
  } catch (error) {
    showMessage('Failed to save preferences', 'error')
  } finally {
    isSaving.value = false
  }
}

const resetToDefaults = () => {
  selectedStrategy.value = 'balanced'
  customPriorities.value = { profit: 33, health: 33, reliability: 34 }
  advancedSettings.value = {
    minSocReserve: 15,
    maxCRate: 1.0,
    priceThreshold: 2.0,
    forecastHorizon: 24,
    rebalanceFreq: 4,
    riskLevel: 'moderate'
  }
  showMessage('Reset to default preferences', 'success')
}

const showMessage = (text: string, type: 'success' | 'error') => {
  message.value = text
  messageType.value = type
  
  setTimeout(() => {
    message.value = ''
  }, 5000)
}
</script>