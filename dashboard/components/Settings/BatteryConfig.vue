<template>
  <UCard class="mb-6">
    <template #header>
      <h3 class="text-lg font-semibold flex items-center gap-2">
        🔋 Battery Configuration
        <UBadge v-if="batteryConfig.battery_type" :color="getBatteryTypeColor(batteryConfig.battery_type)" variant="soft">
          {{ batteryConfig.battery_type }}
        </UBadge>
      </h3>
    </template>
    
    <UForm :schema="batterySchema" :state="batteryConfig" @submit="saveBatteryConfig" class="space-y-6">
      <!-- Battery Type Selection -->
      <UFormGroup label="Battery Type" name="battery_type" help="Different battery types have unique characteristics for arbitrage">
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <UCard 
            v-for="(specs, type) in batteryTypes" 
            :key="type"
            :ui="{ 
              background: batteryConfig.battery_type === type ? 'bg-primary-50 dark:bg-primary-950' : 'bg-white dark:bg-gray-800',
              ring: batteryConfig.battery_type === type ? 'ring-primary-500' : 'ring-gray-200 dark:ring-gray-700'
            }"
            class="cursor-pointer transition-all hover:ring-primary-300"
            @click="onBatteryTypeChange(type)"
          >
            <div class="space-y-2">
              <div class="flex items-center justify-between">
                <h4 class="font-semibold">{{ specs.name }}</h4>
                <UIcon 
                  name="i-heroicons-check-circle" 
                  class="text-primary-500" 
                  v-if="batteryConfig.battery_type === type"
                />
              </div>
              <p class="text-sm text-gray-600 dark:text-gray-400">{{ specs.description }}</p>
              <div class="text-xs space-y-1">
                <div class="flex justify-between">
                  <span>Expected Cycles:</span>
                  <span class="font-medium">{{ specs.cycles_max.toLocaleString() }}</span>
                </div>
                <div class="flex justify-between">
                  <span>Efficiency:</span>
                  <span class="font-medium">{{ (specs.efficiency * 100).toFixed(0) }}%</span>
                </div>
                <div class="flex justify-between">
                  <span>Arbitrage Score:</span>
                  <div class="flex items-center gap-1">
                    <UIcon 
                      v-for="i in 10" 
                      :key="i"
                      name="i-heroicons-star-solid"
                      :class="i <= specs.suitability_score ? 'text-yellow-400' : 'text-gray-300'"
                      class="w-3 h-3"
                    />
                  </div>
                </div>
              </div>
            </div>
          </UCard>
        </div>
      </UFormGroup>

      <!-- Battery Capacity -->
      <UFormGroup label="Battery Capacity" name="battery_capacity_kwh" help="Total energy storage capacity in kWh">
        <div class="space-y-3">
          <URange 
            v-model="batteryConfig.battery_capacity_kwh"
            :min="1" :max="100" :step="0.5"
            :ui="{ track: 'bg-primary-200 dark:bg-primary-800', thumb: 'bg-primary-500' }"
            size="lg"
          />
          <div class="flex justify-between text-sm text-gray-600">
            <span>1 kWh</span>
            <span class="font-semibold text-lg text-primary-600">
              {{ batteryConfig.battery_capacity_kwh }} kWh
            </span>
            <span>100 kWh</span>
          </div>
          <div class="bg-gray-50 dark:bg-gray-800 rounded-lg p-3 text-sm">
            <div class="grid grid-cols-2 gap-4">
              <div>
                <span class="text-gray-500">Investment Cost:</span>
                <span class="font-semibold ml-2">₴{{ getCostEstimate(batteryConfig.battery_capacity_kwh).toLocaleString() }}</span>
              </div>
              <div>
                <span class="text-gray-500">Usable Capacity:</span>
                <span class="font-semibold ml-2">{{ getUsableCapacity() }} kWh</span>
              </div>
            </div>
          </div>
        </div>
      </UFormGroup>

      <!-- Battery Efficiency -->
      <UFormGroup label="Round-Trip Efficiency" name="battery_efficiency" help="Energy efficiency for charge/discharge cycles">
        <div class="space-y-3">
          <URange 
            v-model="batteryConfig.battery_efficiency"
            :min="0.7" :max="1.0" :step="0.01"
            :ui="{ track: 'bg-green-200 dark:bg-green-800', thumb: 'bg-green-500' }"
            size="lg"
          />
          <div class="flex justify-between text-sm text-gray-600">
            <span>70%</span>
            <span class="font-semibold text-lg text-green-600">
              {{ (batteryConfig.battery_efficiency * 100).toFixed(1) }}%
            </span>
            <span>100%</span>
          </div>
        </div>
      </UFormGroup>

      <!-- Advanced Settings Toggle -->
      <UFormGroup>
        <UButton
          @click="showAdvanced = !showAdvanced"
          variant="ghost"
          :icon="showAdvanced ? 'i-heroicons-chevron-up' : 'i-heroicons-chevron-down'"
          size="sm"
        >
          {{ showAdvanced ? 'Hide' : 'Show' }} Advanced Settings
        </UButton>
      </UFormGroup>

      <!-- Advanced Settings (Collapsible) -->
      <div v-if="showAdvanced" class="space-y-6 border-t pt-6">
        <!-- C-Rates -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <UFormGroup label="Charge C-Rate" name="battery_c_rate_charge" help="Maximum charging speed relative to capacity">
            <UInput 
              v-model="batteryConfig.battery_c_rate_charge"
              type="number" 
              step="0.1" 
              min="0.1" 
              max="2.0"
              size="md"
            />
            <template #trailing>
              <span class="text-gray-400 text-sm">C</span>
            </template>
          </UFormGroup>
          
          <UFormGroup label="Discharge C-Rate" name="battery_c_rate_discharge" help="Maximum discharge speed relative to capacity">
            <UInput 
              v-model="batteryConfig.battery_c_rate_discharge"
              type="number" 
              step="0.1" 
              min="0.1" 
              max="3.0"
              size="md"
            />
            <template #trailing>
              <span class="text-gray-400 text-sm">C</span>
            </template>
          </UFormGroup>
        </div>

        <!-- SOC Limits -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <UFormGroup label="Minimum SOC" name="battery_soc_min" help="Minimum state of charge to preserve battery life">
            <UInput 
              v-model="batteryConfig.battery_soc_min"
              type="number" 
              step="0.05" 
              min="0.05" 
              max="0.3"
              size="md"
            />
            <template #trailing>
              <span class="text-gray-400 text-sm">{{ (batteryConfig.battery_soc_min * 100).toFixed(0) }}%</span>
            </template>
          </UFormGroup>
          
          <UFormGroup label="Maximum SOC" name="battery_soc_max" help="Maximum state of charge for optimal lifespan">
            <UInput 
              v-model="batteryConfig.battery_soc_max"
              type="number" 
              step="0.05" 
              min="0.8" 
              max="1.0"
              size="md"
            />
            <template #trailing>
              <span class="text-gray-400 text-sm">{{ (batteryConfig.battery_soc_max * 100).toFixed(0) }}%</span>
            </template>
          </UFormGroup>
        </div>
      </div>

      <!-- Degradation Analysis -->
      <UAlert 
        :icon="getDegradationIcon(batteryConfig.battery_type)"
        :color="getDegradationColor(batteryConfig.battery_type)"
        :title="`${batteryConfig.battery_type} Degradation Analysis`"
      >
        <template #description>
          <div class="space-y-2">
            <div class="flex justify-between">
              <span>Cost per cycle:</span>
              <span class="font-semibold">₴{{ getDegradationCost().toFixed(2) }}</span>
            </div>
            <div class="flex justify-between">
              <span>Daily cycles (estimated):</span>
              <span class="font-semibold">1.0</span>
            </div>
            <div class="flex justify-between">
              <span>Daily degradation cost:</span>
              <span class="font-semibold">₴{{ getDegradationCost().toFixed(2) }}</span>
            </div>
            <div class="text-xs text-gray-600 mt-2">
              {{ getDegradationDescription(batteryConfig.battery_type) }}
            </div>
          </div>
        </template>
      </UAlert>

      <!-- Save Button -->
      <div class="flex justify-end">
        <UButton 
          type="submit" 
          :loading="saving"
          size="lg"
          :icon="saving ? 'i-heroicons-arrow-path' : 'i-heroicons-battery-100'"
        >
          {{ saving ? 'Saving & Recalculating...' : 'Save Battery Configuration' }}
        </UButton>
      </div>
    </UForm>
  </UCard>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue'
import { useSettingsStore } from '~/stores/settingsStore'
import { useToast } from '#imports'

const settingsStore = useSettingsStore()
const toast = useToast()

// Component state
const saving = ref(false)
const showAdvanced = ref(false)

// Battery configuration
const batteryConfig = reactive({
  battery_type: 'LFP' as 'LFP' | 'Lead-Acid' | 'VRFB',
  battery_capacity_kwh: 10.0,
  battery_efficiency: 0.95,
  battery_c_rate_charge: 0.5,
  battery_c_rate_discharge: 1.0,
  battery_soc_min: 0.1,
  battery_soc_max: 1.0
})

// Battery type specifications
const batteryTypes = {
  'LFP': {
    name: 'LFP (Lithium Iron Phosphate)',
    description: '8000 cycles, best for daily cycling',
    efficiency: 0.95,
    cycles_max: 8000,
    cost_uah_per_kwh: 13000,
    suitability_score: 9
  },
  'Lead-Acid': {
    name: 'Lead-Acid Deep Cycle',
    description: '600 cycles, lower cost, high maintenance',
    efficiency: 0.85,
    cycles_max: 600,
    cost_uah_per_kwh: 5500,
    suitability_score: 4
  },
  'VRFB': {
    name: 'Vanadium Flow Battery',
    description: '20000+ cycles, minimal degradation',
    efficiency: 0.75,
    cycles_max: 20000,
    cost_uah_per_kwh: 22000,
    suitability_score: 7
  }
}

// Computed properties
const usableCapacity = computed(() => {
  const dodMax = batteryConfig.battery_type === 'Lead-Acid' ? 0.5 : 
                 batteryConfig.battery_type === 'VRFB' ? 1.0 : 0.9
  return (batteryConfig.battery_capacity_kwh * dodMax).toFixed(1)
})

// Methods
const getBatteryTypeColor = (type: string) => {
  const colors = { 'LFP': 'green', 'Lead-Acid': 'yellow', 'VRFB': 'blue' }
  return colors[type] || 'gray'
}

const getCostEstimate = (capacity: number) => {
  const costPerKwh = batteryTypes[batteryConfig.battery_type].cost_uah_per_kwh
  return Math.round(capacity * costPerKwh)
}

const getUsableCapacity = () => {
  return usableCapacity.value
}

const getDegradationCost = () => {
  const specs = batteryTypes[batteryConfig.battery_type]
  return batteryConfig.battery_capacity_kwh * specs.cost_uah_per_kwh / specs.cycles_max
}

const getDegradationIcon = (type: string) => {
  const icons = { 'LFP': 'i-heroicons-battery-100', 'Lead-Acid': 'i-heroicons-exclamation-triangle', 'VRFB': 'i-heroicons-beaker' }
  return icons[type] || 'i-heroicons-battery-50'
}

const getDegradationColor = (type: string) => {
  const colors = { 'LFP': 'green', 'Lead-Acid': 'amber', 'VRFB': 'blue' }
  return colors[type] || 'gray'
}

const getDegradationDescription = (type: string) => {
  const descriptions = {
    'LFP': 'LFP batteries have excellent cycle life and low degradation, ideal for daily arbitrage cycling.',
    'Lead-Acid': 'Lead-acid batteries degrade faster with deep cycles. Consider limited DoD to extend life.',
    'VRFB': 'Flow batteries have minimal capacity degradation over thousands of cycles, excellent for long-term use.'
  }
  return descriptions[type] || ''
}

const onBatteryTypeChange = async (newType: string) => {
  batteryConfig.battery_type = newType as any
  
  // Set type-specific defaults
  const specs = batteryTypes[newType]
  batteryConfig.battery_efficiency = specs.efficiency
  
  if (newType === 'Lead-Acid') {
    batteryConfig.battery_c_rate_charge = 0.2
    batteryConfig.battery_c_rate_discharge = 0.3
    batteryConfig.battery_soc_min = 0.2
    batteryConfig.battery_soc_max = 0.8
  } else if (newType === 'VRFB') {
    batteryConfig.battery_c_rate_charge = 0.25
    batteryConfig.battery_c_rate_discharge = 0.25
    batteryConfig.battery_soc_min = 0.05
    batteryConfig.battery_soc_max = 1.0
  } else { // LFP
    batteryConfig.battery_c_rate_charge = 0.5
    batteryConfig.battery_c_rate_discharge = 1.0
    batteryConfig.battery_soc_min = 0.1
    batteryConfig.battery_soc_max = 1.0
  }
  
  // Immediate recalculation of analytics
  await refreshAllAnalytics()
}

const saveBatteryConfig = async () => {
  saving.value = true
  
  try {
    const response = await $fetch('/api/settings/battery', {
      method: 'POST',
      body: batteryConfig
    })
    
    if (response.success) {
      toast.add({
        title: 'Battery Configuration Saved',
        description: 'ML pipeline is recalculating analytics with your new settings.',
        icon: 'i-heroicons-check-circle',
        color: 'green'
      })
      
      // Update store
      await settingsStore.updateBatteryConfig(batteryConfig)
      
      // Trigger immediate analytics refresh
      await refreshAllAnalytics()
    } else {
      throw new Error('Failed to save configuration')
    }
  } catch (error) {
    console.error('Save failed:', error)
    toast.add({
      title: 'Save Failed',
      description: 'Could not save battery configuration. Please try again.',
      icon: 'i-heroicons-x-circle',
      color: 'red'
    })
  } finally {
    saving.value = false
  }
}

const refreshAllAnalytics = async () => {
  // Emit event to refresh analytics
  await nextTick()
  // This will be picked up by parent components and analytics store
}

// Schema for validation
const batterySchema = {
  battery_type: { required: true },
  battery_capacity_kwh: { required: true, min: 1, max: 1000 },
  battery_efficiency: { required: true, min: 0.7, max: 1.0 }
}

// Initialize from store
onMounted(async () => {
  const currentConfig = settingsStore.settings.userConfig
  if (currentConfig) {
    Object.assign(batteryConfig, currentConfig)
  }
})
</script>

<style scoped>
/* Custom styling for the component */
.battery-type-card {
  transition: all 0.2s ease-in-out;
}

.battery-type-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}
</style>