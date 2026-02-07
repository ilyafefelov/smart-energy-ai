<template>
  <div 
    :class="[
      'rounded-lg border p-6 transition-all hover:shadow-lg',
      colorClasses[color] || colorClasses.slate
    ]"
  >
    <!-- Header with tooltip -->
    <div class="flex items-start justify-between mb-4">
      <div>
        <p class="text-sm text-slate-400 font-medium">{{ label }}</p>
        <InfoTooltip 
          v-if="tooltipInfo"
          :title="tooltipInfo.title"
          :description="tooltipInfo.description"
          :formula="tooltipInfo.formula"
        >
          <button class="text-xs text-slate-500 hover:text-energy-400 transition mt-1">
            ℹ️ What is this?
          </button>
        </InfoTooltip>
      </div>

      <!-- Icon if provided -->
      <span v-if="icon" class="text-2xl">{{ icon }}</span>
    </div>

    <!-- Main value -->
    <div class="space-y-2">
      <div class="text-3xl font-bold text-white">{{ value }}</div>

      <!-- Trend indicator -->
      <div v-if="trend" class="flex items-center gap-2">
        <span :class="trendColor">
          {{ trendIcon }}
        </span>
        <span v-if="trendValue" :class="trendColor" class="text-sm font-semibold">
          {{ trendValue > 0 ? '+' : '' }}{{ trendValue }}%
        </span>
      </div>

      <!-- Description -->
      <p v-if="description" class="text-xs text-slate-400 mt-2">{{ description }}</p>
    </div>

    <!-- Slot for custom content -->
    <slot />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  label: string
  value: string | number
  icon?: string
  color?: 'green' | 'red' | 'blue' | 'yellow' | 'purple' | 'slate' | 'orange'
  trend?: 'up' | 'down' | 'stable'
  trendValue?: number
  description?: string
  tooltipInfo?: {
    title: string
    description: string
    formula?: string
  }
}

const props = withDefaults(defineProps<Props>(), {
  color: 'slate',
  tooltipInfo: undefined,
  description: undefined
})

const colorClasses = {
  green: 'bg-green-900 bg-opacity-20 border-green-700 hover:bg-opacity-30',
  red: 'bg-red-900 bg-opacity-20 border-red-700 hover:bg-opacity-30',
  blue: 'bg-blue-900 bg-opacity-20 border-blue-700 hover:bg-opacity-30',
  yellow: 'bg-yellow-900 bg-opacity-20 border-yellow-700 hover:bg-opacity-30',
  purple: 'bg-purple-900 bg-opacity-20 border-purple-700 hover:bg-opacity-30',
  slate: 'bg-slate-800 bg-opacity-40 border-slate-700 hover:bg-opacity-50',
  orange: 'bg-orange-900 bg-opacity-20 border-orange-700 hover:bg-opacity-30'
}

const trendIcon = computed(() => {
  switch (props.trend) {
    case 'up':
      return '📈'
    case 'down':
      return '📉'
    default:
      return '➡️'
  }
})

const trendColor = computed(() => {
  switch (props.trend) {
    case 'up':
      return 'text-green-400'
    case 'down':
      return 'text-red-400'
    default:
      return 'text-yellow-400'
  }
})
</script>

<style scoped>
.hover\:shadow-lg:hover {
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.3);
}
</style>
