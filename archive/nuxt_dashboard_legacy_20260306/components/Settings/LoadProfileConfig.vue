<template>
  <UCard class="mb-6">
    <template #header>
      <h3 class="text-lg font-semibold flex items-center gap-2">
        ⚡ Load Profile Configuration
        <UBadge v-if="loadConfig.load_profile_type" color="blue" variant="soft">
          {{ getProfileDisplayName(loadConfig.load_profile_type) }}
        </UBadge>
      </h3>
    </template>
    
    <UForm :schema="loadSchema" :state="loadConfig" @submit="saveLoadConfig" class="space-y-6">
      <!-- Load Profile Type Selection -->
      <UFormGroup label="Load Profile Type" name="load_profile_type" help="Choose the pattern that best matches your energy usage">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <UCard 
            v-for="(template, type) in profileTemplates" 
            :key="type"
            :ui="{ 
              background: loadConfig.load_profile_type === type ? 'bg-blue-50 dark:bg-blue-950' : 'bg-white dark:bg-gray-800',
              ring: loadConfig.load_profile_type === type ? 'ring-blue-500' : 'ring-gray-200 dark:ring-gray-700'
            }"
            class="cursor-pointer transition-all hover:ring-blue-300"
            @click="onProfileTypeChange(type)"
          >
            <div class="space-y-3">
              <div class="flex items-center justify-between">
                <h4 class="font-semibold">{{ template.name }}</h4>
                <UIcon 
                  name="i-heroicons-check-circle" 
                  class="text-blue-500" 
                  v-if="loadConfig.load_profile_type === type"
                />
              </div>
              <p class="text-sm text-gray-600 dark:text-gray-400">{{ template.description }}</p>
              
              <!-- Mini visualization -->
              <div class="h-12 bg-gray-100 dark:bg-gray-700 rounded relative overflow-hidden">
                <div 
                  v-for="(coef, hour) in template.hourly_pattern" 
                  :key="hour"
                  class="absolute bottom-0 bg-blue-400 opacity-70"
                  :style="{
                    left: `${(hour / 24) * 100}%`,
                    width: `${100/24}%`,
                    height: `${coef * 100}%`
                  }"
                />
              </div>
              
              <div class="text-xs space-y-1">
                <div class="flex justify-between">
                  <span>Peak Hours:</span>
                  <span class="font-medium">{{ template.peak_hours }}</span>
                </div>
                <div class="flex justify-between">
                  <span>Arbitrage Potential:</span>
                  <div class="flex items-center gap-1">
                    <UIcon 
                      v-for="i in 10" 
                      :key="i"
                      name="i-heroicons-star-solid"
                      :class="i <= template.arbitrage_potential ? 'text-yellow-400' : 'text-gray-300'"
                      class="w-3 h-3"
                    />
                  </div>
                </div>
              </div>
            </div>
          </UCard>
        </div>
      </UFormGroup>

      <!-- Peak Load Configuration -->
      <UFormGroup label="Peak Load" name="load_peak_kw" help="Maximum power consumption during operation">
        <div class="space-y-3">
          <URange 
            v-model="loadConfig.load_peak_kw"
            :min="1" :max="50" :step="0.5"
            :ui="{ track: 'bg-blue-200 dark:bg-blue-800', thumb: 'bg-blue-500' }"
            size="lg"
          />
          <div class="flex justify-between text-sm text-gray-600">
            <span>1 kW</span>
            <span class="font-semibold text-lg text-blue-600">
              {{ loadConfig.load_peak_kw }} kW
            </span>
            <span>50 kW</span>
          </div>
          <div class="bg-gray-50 dark:bg-gray-800 rounded-lg p-3 text-sm">
            <div class="grid grid-cols-2 gap-4">
              <div>
                <span class="text-gray-500">Base Load:</span>
                <span class="font-semibold ml-2">{{ (loadConfig.load_peak_kw * 0.2).toFixed(1) }} kW</span>
              </div>
              <div>
                <span class="text-gray-500">Daily Energy:</span>
                <span class="font-semibold ml-2">{{ getDailyEnergyEstimate() }} kWh</span>
              </div>
            </div>
          </div>
        </div>
      </UFormGroup>

      <!-- Custom Hourly Profile (if custom type selected) -->
      <div v-if="loadConfig.load_profile_type === 'custom'" class="space-y-4">
        <UFormGroup label="Custom 24-Hour Profile" help="Define load coefficients for each hour (0-1 relative to peak)">
          <div class="space-y-4">
            <!-- Hour-by-hour sliders -->
            <div class="grid grid-cols-6 gap-2">
              <div v-for="hour in 24" :key="hour" class="text-center">
                <label class="text-xs text-gray-500 block mb-1">{{ String(hour - 1).padStart(2, '0') }}:00</label>
                <URange
                  v-model="loadConfig.load_custom_hourly[hour - 1]"
                  :min="0" :max="1" :step="0.05"
                  orientation="vertical"
                  class="h-16"
                  size="sm"
                />
                <span class="text-xs text-gray-400 mt-1 block">
                  {{ (loadConfig.load_custom_hourly[hour - 1] * 100).toFixed(0) }}%
                </span>
              </div>
            </div>
            
            <!-- Profile Visualization -->
            <div class="mt-4">
              <h4 class="font-medium mb-2">Profile Preview</h4>
              <canvas ref="profileCanvas" class="w-full h-32 bg-gray-100 dark:bg-gray-800 rounded"></canvas>
            </div>
            
            <!-- Quick preset buttons -->
            <div class="flex flex-wrap gap-2">
              <UButton @click="setFlatProfile" size="sm" variant="outline">Flat Profile</UButton>
              <UButton @click="setBusinessHours" size="sm" variant="outline">Business Hours</UButton>
              <UButton @click="setNightShift" size="sm" variant="outline">Night Shift</UButton>
              <UButton @click="setContinuous" size="sm" variant="outline">24/7 Continuous</UButton>
            </div>
          </div>
        </UFormGroup>
      </div>

      <!-- Advanced Settings -->
      <UFormGroup>
        <UButton
          @click="showAdvanced = !showAdvanced"
          variant="ghost"
          :icon="showAdvanced ? 'i-heroicons-chevron-up' : 'i-heroicons-chevron-down'"
          size="sm"
        >
          {{ showAdvanced ? 'Hide' : 'Show' }} Advanced Load Settings
        </UButton>
      </UFormGroup>

      <div v-if="showAdvanced" class="space-y-6 border-t pt-6">
        <!-- Base Load -->
        <UFormGroup label="Base Load" name="load_base_kw" help="Minimum continuous load even during off-hours">
          <UInput 
            v-model="loadConfig.load_base_kw"
            type="number" 
            step="0.1" 
            min="0.5" 
            max="20"
            size="md"
          />
          <template #trailing>
            <span class="text-gray-400 text-sm">kW</span>
          </template>
        </UFormGroup>

        <!-- Seasonal and Weekend Factors -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <UFormGroup label="Weekend Load Factor" name="load_weekend_factor" help="Load reduction factor for weekends">
            <URange 
              v-model="loadConfig.load_weekend_factor"
              :min="0.3" :max="1.0" :step="0.05"
              size="md"
            />
            <div class="flex justify-between text-sm text-gray-600 mt-1">
              <span>30%</span>
              <span class="font-semibold">{{ (loadConfig.load_weekend_factor * 100).toFixed(0) }}%</span>
              <span>100%</span>
            </div>
          </UFormGroup>
          
          <UFormGroup label="Seasonal Variation" name="load_seasonal_variation" help="Load variation throughout the year">
            <URange 
              v-model="loadConfig.load_seasonal_variation"
              :min="0.0" :max="0.5" :step="0.05"
              size="md"
            />
            <div class="flex justify-between text-sm text-gray-600 mt-1">
              <span>0%</span>
              <span class="font-semibold">±{{ (loadConfig.load_seasonal_variation * 100).toFixed(0) }}%</span>
              <span>50%</span>
            </div>
          </UFormGroup>
        </div>
      </div>

      <!-- Load Analysis -->
      <UAlert 
        icon="i-heroicons-chart-bar"
        color="blue"
        title="Load Profile Analysis"
      >
        <template #description>
          <div class="space-y-2">
            <div class="flex justify-between">
              <span>Peak Load:</span>
              <span class="font-semibold">{{ loadConfig.load_peak_kw }} kW</span>
            </div>
            <div class="flex justify-between">
              <span>Base Load:</span>
              <span class="font-semibold">{{ loadConfig.load_base_kw }} kW</span>
            </div>
            <div class="flex justify-between">
              <span>Load Factor:</span>
              <span class="font-semibold">{{ getLoadFactor().toFixed(1) }}%</span>
            </div>
            <div class="flex justify-between">
              <span>Daily Energy (est.):</span>
              <span class="font-semibold">{{ getDailyEnergyEstimate() }} kWh</span>
            </div>
            <div class="text-xs text-gray-600 mt-2">
              {{ getLoadAnalysis() }}
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
          :icon="saving ? 'i-heroicons-arrow-path' : 'i-heroicons-bolt'"
        >
          {{ saving ? 'Saving & Recalculating...' : 'Save Load Profile' }}
        </UButton>
      </div>
    </UForm>
  </UCard>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, onMounted, nextTick } from 'vue'
import { useSettingsStore } from '~/stores/settingsStore'
import { useToast } from '#imports'

const settingsStore = useSettingsStore()
const toast = useToast()

// Component state
const saving = ref(false)
const showAdvanced = ref(false)
const profileCanvas = ref<HTMLCanvasElement>()

// Load configuration
const loadConfig = reactive({
  load_profile_type: 'standard' as 'standard' | 'multi_shift' | '24_7' | 'custom',
  load_peak_kw: 10.0,
  load_base_kw: 2.0,
  load_custom_hourly: new Array(24).fill(0.5),
  load_seasonal_variation: 0.2,
  load_weekend_factor: 0.6
})

// Profile templates with enhanced data
const profileTemplates = {
  'standard': {
    name: 'Standard Business Hours',
    description: 'Office/retail: 9 AM - 6 PM weekdays',
    peak_hours: '09:00-18:00',
    arbitrage_potential: 8,
    hourly_pattern: [
      0.2, 0.2, 0.2, 0.2, 0.2, 0.3,  // 00-05: Night
      0.4, 0.6, 0.8,                  // 06-08: Morning
      1.0, 1.0, 0.9, 0.8, 0.9, 1.0, 1.0, 0.9, 0.8, // 09-17: Business
      0.6, 0.5, 0.4, 0.3, 0.3, 0.2   // 18-23: Evening
    ]
  },
  'multi_shift': {
    name: 'Multi-Shift Manufacturing',
    description: 'Two shifts: 6 AM-2 PM + 10 PM-6 AM',
    peak_hours: '06:00-14:00, 22:00-06:00',
    arbitrage_potential: 6,
    hourly_pattern: [
      0.8, 0.8, 0.7, 0.6, 0.5, 0.4,  // 00-05: Night shift
      1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, // 06-13: Day shift
      0.3, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.3, // 14-21: Break
      0.9, 0.9                        // 22-23: Night shift start
    ]
  },
  '24_7': {
    name: '24/7 Continuous',
    description: 'Continuous operations with minimal variation',
    peak_hours: 'Continuous',
    arbitrage_potential: 4,
    hourly_pattern: [
      0.9, 0.9, 0.9, 0.9, 0.9, 0.95, // 00-05: Slight reduction
      1.0, 1.0, 1.0, 1.0, 1.0, 1.0,  // 06-11: Full load
      1.0, 1.0, 1.0, 1.0, 1.0, 1.0,  // 12-17: Full load
      1.0, 1.0, 0.95, 0.95, 0.9, 0.9 // 18-23: Slight reduction
    ]
  },
  'custom': {
    name: 'Custom Profile',
    description: 'Define your own 24-hour pattern',
    peak_hours: 'User-defined',
    arbitrage_potential: 5,
    hourly_pattern: new Array(24).fill(0.5)
  }
}

// Computed properties
const loadFactor = computed(() => {
  const pattern = loadConfig.load_profile_type === 'custom' 
    ? loadConfig.load_custom_hourly 
    : profileTemplates[loadConfig.load_profile_type].hourly_pattern
  
  const averageCoef = pattern.reduce((sum, coef) => sum + coef, 0) / 24
  return (averageCoef * 100)
})

// Methods
const getProfileDisplayName = (type: string) => {
  return profileTemplates[type]?.name.split(' ')[0] || type
}

const getDailyEnergyEstimate = () => {
  const pattern = loadConfig.load_profile_type === 'custom' 
    ? loadConfig.load_custom_hourly 
    : profileTemplates[loadConfig.load_profile_type].hourly_pattern
  
  const totalEnergy = pattern.reduce((sum, coef) => sum + (coef * loadConfig.load_peak_kw), 0)
  return totalEnergy.toFixed(1)
}

const getLoadFactor = () => {
  return loadFactor.value
}

const getLoadAnalysis = () => {
  const factor = loadFactor.value
  if (factor < 40) {
    return 'Low load factor - excellent for arbitrage opportunities during off-peak hours.'
  } else if (factor < 70) {
    return 'Moderate load factor - good balance between operations and arbitrage potential.'
  } else {
    return 'High load factor - limited arbitrage opportunities but consistent energy demand.'
  }
}

const onProfileTypeChange = (newType: string) => {
  loadConfig.load_profile_type = newType as any
  
  const template = profileTemplates[newType]
  if (newType !== 'custom') {
    // Set defaults from template
    loadConfig.load_custom_hourly = [...template.hourly_pattern]
  }
  
  // Update visualization
  nextTick(() => {
    drawLoadProfile()
  })
}

const setFlatProfile = () => {
  loadConfig.load_custom_hourly = new Array(24).fill(0.5)
  drawLoadProfile()
}

const setBusinessHours = () => {
  loadConfig.load_custom_hourly = [...profileTemplates.standard.hourly_pattern]
  drawLoadProfile()
}

const setNightShift = () => {
  const nightPattern = new Array(24).fill(0.2)
  // Night shift: 22:00 - 06:00
  for (let i = 22; i < 24; i++) nightPattern[i] = 1.0
  for (let i = 0; i < 6; i++) nightPattern[i] = 1.0
  loadConfig.load_custom_hourly = nightPattern
  drawLoadProfile()
}

const setContinuous = () => {
  loadConfig.load_custom_hourly = [...profileTemplates['24_7'].hourly_pattern]
  drawLoadProfile()
}

const drawLoadProfile = () => {
  if (!profileCanvas.value) return
  
  const canvas = profileCanvas.value
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  
  // Set canvas size
  canvas.width = canvas.offsetWidth
  canvas.height = canvas.offsetHeight
  
  const width = canvas.width
  const height = canvas.height
  
  // Clear canvas
  ctx.fillStyle = 'rgb(31, 41, 55)' // dark background
  ctx.fillRect(0, 0, width, height)
  
  // Draw profile
  const pattern = loadConfig.load_profile_type === 'custom' 
    ? loadConfig.load_custom_hourly 
    : profileTemplates[loadConfig.load_profile_type].hourly_pattern
  
  const barWidth = width / 24
  
  ctx.fillStyle = 'rgb(59, 130, 246)' // blue-500
  
  pattern.forEach((coef, hour) => {
    const barHeight = coef * (height - 10)
    const x = hour * barWidth
    const y = height - barHeight
    
    ctx.fillRect(x, y, barWidth - 1, barHeight)
  })
  
  // Draw hour labels
  ctx.fillStyle = 'rgb(156, 163, 175)' // gray-400
  ctx.font = '10px monospace'
  ctx.textAlign = 'center'
  
  for (let hour = 0; hour < 24; hour += 4) {
    const x = (hour + 0.5) * barWidth
    ctx.fillText(String(hour).padStart(2, '0'), x, height - 2)
  }
}

const saveLoadConfig = async () => {
  saving.value = true
  
  try {
    const response = await $fetch('/api/settings/load-profile', {
      method: 'POST',
      body: loadConfig
    })
    
    if (response.success) {
      toast.add({
        title: 'Load Profile Saved',
        description: 'ML pipeline is recalculating analytics with your new load profile.',
        icon: 'i-heroicons-check-circle',
        color: 'green'
      })
      
      // Update store
      await settingsStore.updateLoadConfig(loadConfig)
      
      // Trigger analytics refresh
      await refreshAllAnalytics()
    } else {
      throw new Error('Failed to save load profile')
    }
  } catch (error) {
    console.error('Save failed:', error)
    toast.add({
      title: 'Save Failed',
      description: 'Could not save load profile configuration. Please try again.',
      icon: 'i-heroicons-x-circle',
      color: 'red'
    })
  } finally {
    saving.value = false
  }
}

const refreshAllAnalytics = async () => {
  // Trigger analytics recalculation
  await nextTick()
}

// Schema for validation
const loadSchema = {
  load_profile_type: { required: true },
  load_peak_kw: { required: true, min: 1, max: 500 },
  load_base_kw: { required: true, min: 0.5, max: 20 }
}

// Watch for custom hourly changes to redraw
watch(() => loadConfig.load_custom_hourly, () => {
  nextTick(() => {
    drawLoadProfile()
  })
}, { deep: true })

// Initialize
onMounted(async () => {
  const currentConfig = settingsStore.settings.userConfig
  if (currentConfig) {
    Object.assign(loadConfig, currentConfig)
  }
  
  // Draw initial profile
  await nextTick()
  drawLoadProfile()
})
</script>

<style scoped>
.profile-visualization {
  background: linear-gradient(to bottom, #f3f4f6, #e5e7eb);
}

.dark .profile-visualization {
  background: linear-gradient(to bottom, #374151, #1f2937);
}
</style>