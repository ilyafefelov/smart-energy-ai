<template>
  <div 
    :class="[
      'rounded-lg border p-6 transition-all duration-300 hover:shadow-lg',
      colorClasses[color] || colorClasses.slate
    ]"
    @mouseenter="isHovered = true"
    @mouseleave="isHovered = false"
  >
    <!-- Header with tooltip -->
    <div class="flex items-start justify-between mb-4">
      <div class="flex-1">
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
         <span v-if="trendValue !== undefined" :class="trendColor" class="text-sm font-semibold">
           {{ formattedTrendValue }}
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
import { computed, ref } from 'vue'

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

const isHovered = ref(false)

const colorClasses = {
  green: 'bg-green-900 bg-opacity-20 border-green-700 hover:bg-opacity-30 hover:scale-102 hover:shadow-lg',
  red: 'bg-red-900 bg-opacity-20 border-red-700 hover:bg-opacity-30 hover:scale-102 hover:shadow-lg',
  blue: 'bg-blue-900 bg-opacity-20 border-blue-700 hover:bg-opacity-30 hover:scale-102 hover:shadow-lg',
  yellow: 'bg-yellow-900 bg-opacity-20 border-yellow-700 hover:bg-opacity-30 hover:scale-102 hover:shadow-lg',
  purple: 'bg-purple-900 bg-opacity-20 border-purple-700 hover:bg-opacity-30 hover:scale-102 hover:shadow-lg',
  slate: 'bg-slate-800 bg-opacity-40 border-slate-700 hover:bg-opacity-50 hover:scale-102 hover:shadow-lg',
  orange: 'bg-orange-900 bg-opacity-20 border-orange-700 hover:bg-opacity-30 hover:scale-102 hover:shadow-lg'
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

const formattedTrendValue = computed(() => {
  if (props.trendValue === undefined) return ''
  const v = props.trendValue
  // If value is > 100 (like 100.2), it's likely a ratio - convert to percentage change
  // Otherwise just format as-is
  let displayValue: number
  if (v > 100) {
    displayValue = v - 100 // Convert ratio to percentage change
  } else {
    displayValue = v
  }
  return `${displayValue > 0 ? '+' : ''}${displayValue.toFixed(1)}%`
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
.hover\:scale-102:hover {
  transform: scale(1.02);
}

.hover\:shadow-lg:hover {
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.3);
}
</style>
