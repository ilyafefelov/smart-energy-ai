<template>
  <div class="bg-slate-900 border border-slate-700 rounded-lg p-6">
    <div class="flex items-center justify-between mb-4">
      <h3 class="text-lg font-semibold text-white flex items-center gap-2">
        <span class="text-2xl">📈</span>
        24-Hour Forecast
      </h3>
      <p class="text-xs text-slate-400">
        Next {{ mlStore.dailyForecast.length }} hours
      </p>
    </div>

    <!-- Loading State -->
    <div v-if="mlStore.loading && mlStore.dailyForecast.length === 0" class="flex items-center justify-center py-8">
      <div class="animate-spin text-2xl">⟳</div>
      <span class="ml-2 text-slate-400">Loading forecast...</span>
    </div>

    <!-- Chart Container -->
    <div v-else-if="mlStore.dailyForecast.length > 0" class="space-y-4">
      <!-- Chart -->
      <div class="h-64 bg-slate-800 rounded-lg p-4 relative">
        <canvas
          ref="chartCanvas"
          class="w-full h-full"
        ></canvas>
      </div>

      <!-- Forecast Timeline -->
      <div class="space-y-2 max-h-64 overflow-y-auto">
        <h4 class="text-sm font-semibold text-slate-300 border-b border-slate-700 pb-2">
          Hourly Breakdown
        </h4>
        <div 
          v-for="(forecast, index) in mlStore.dailyForecast.slice(0, 12)" 
          :key="index"
          class="flex items-center gap-3 p-2 bg-slate-800 rounded-lg"
        >
          <div class="text-xs text-slate-400 w-12">
            {{ formatHour(forecast.hour) }}
          </div>
          <div 
            :class="[
              'flex items-center justify-center w-8 h-8 rounded text-xs font-semibold',
              getActionColor(forecast.action)
            ]"
          >
            {{ getActionIcon(forecast.action) }}
          </div>
          <div class="flex-1">
            <p class="text-sm font-semibold" :class="getActionTextColor(forecast.action)">
              {{ forecast.action }}
            </p>
            <p class="text-xs text-slate-400 truncate">{{ forecast.reasoning }}</p>
          </div>
          <div class="text-right">
            <p class="text-sm font-semibold text-green-400">
              ₴{{ Math.round(forecast.price_uah_mwh / 1000) }}
            </p>
            <p class="text-xs text-slate-400">per kWh</p>
          </div>
        </div>
        
        <!-- Show More Button -->
        <button 
          v-if="mlStore.dailyForecast.length > 12 && !showAllForecast"
          @click="showAllForecast = true"
          class="w-full py-2 text-sm text-energy-400 hover:text-energy-300 border border-slate-700 rounded-lg hover:bg-slate-800 transition-colors"
        >
          Show {{ mlStore.dailyForecast.length - 12 }} more hours
        </button>
        
        <!-- Additional forecast items when expanded -->
        <div 
          v-if="showAllForecast"
          class="space-y-2"
        >
          <div 
            v-for="(forecast, index) in mlStore.dailyForecast.slice(12)" 
            :key="index + 12"
            class="flex items-center gap-3 p-2 bg-slate-800 rounded-lg"
          >
            <div class="text-xs text-slate-400 w-12">
              {{ formatHour(forecast.hour) }}
            </div>
            <div 
              :class="[
                'flex items-center justify-center w-8 h-8 rounded text-xs font-semibold',
                getActionColor(forecast.action)
              ]"
            >
              {{ getActionIcon(forecast.action) }}
            </div>
            <div class="flex-1">
              <p class="text-sm font-semibold" :class="getActionTextColor(forecast.action)">
                {{ forecast.action }}
              </p>
              <p class="text-xs text-slate-400 truncate">{{ forecast.reasoning }}</p>
            </div>
            <div class="text-right">
              <p class="text-sm font-semibold text-green-400">
                ₴{{ Math.round(forecast.price_uah_mwh / 1000) }}
              </p>
              <p class="text-xs text-slate-400">per kWh</p>
            </div>
          </div>
          
          <button 
            @click="showAllForecast = false"
            class="w-full py-2 text-sm text-energy-400 hover:text-energy-300 border border-slate-700 rounded-lg hover:bg-slate-800 transition-colors"
          >
            Show less
          </button>
        </div>
      </div>

      <!-- Summary Stats -->
      <div class="grid grid-cols-3 gap-4 pt-4 border-t border-slate-700">
        <div class="text-center">
          <p class="text-xs text-slate-400">BUY Hours</p>
          <p class="text-lg font-semibold text-green-400">
            {{ getForecastStats().buy }}
          </p>
        </div>
        <div class="text-center">
          <p class="text-xs text-slate-400">SELL Hours</p>
          <p class="text-lg font-semibold text-blue-400">
            {{ getForecastStats().sell }}
          </p>
        </div>
        <div class="text-center">
          <p class="text-xs text-slate-400">HOLD Hours</p>
          <p class="text-lg font-semibold text-gray-400">
            {{ getForecastStats().hold }}
          </p>
        </div>
      </div>
    </div>

    <!-- No Data State -->
    <div v-else class="text-center py-8">
      <p class="text-slate-400">No forecast data available</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick, watch } from 'vue'
import { useMLStore } from '~/stores/mlStore'

const mlStore = useMLStore()
const chartCanvas = ref<HTMLCanvasElement>()
const showAllForecast = ref(false)

// Helper functions
const formatHour = (hour: number): string => {
  return `${hour.toString().padStart(2, '0')}:00`
}

const getActionColor = (action: string): string => {
  switch (action) {
    case 'BUY': return 'bg-green-500 bg-opacity-20 text-green-400'
    case 'SELL': return 'bg-blue-500 bg-opacity-20 text-blue-400'
    case 'HOLD': return 'bg-gray-500 bg-opacity-20 text-gray-400'
    default: return 'bg-gray-500 bg-opacity-20 text-gray-400'
  }
}

const getActionTextColor = (action: string): string => {
  switch (action) {
    case 'BUY': return 'text-green-400'
    case 'SELL': return 'text-blue-400'
    case 'HOLD': return 'text-gray-400'
    default: return 'text-gray-400'
  }
}

const getActionIcon = (action: string): string => {
  switch (action) {
    case 'BUY': return '⬆'
    case 'SELL': return '⬇'
    case 'HOLD': return '⏸'
    default: return '⏸'
  }
}

const getForecastStats = () => {
  const stats = { buy: 0, sell: 0, hold: 0 }
  
  mlStore.dailyForecast.forEach(forecast => {
    switch (forecast.action) {
      case 'BUY': stats.buy++; break
      case 'SELL': stats.sell++; break
      case 'HOLD': stats.hold++; break
    }
  })
  
  return stats
}

// Simple chart drawing (without external dependencies)
const drawChart = () => {
  if (!chartCanvas.value || mlStore.dailyForecast.length === 0) return
  
  const canvas = chartCanvas.value
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  
  // Set canvas size
  canvas.width = canvas.offsetWidth * devicePixelRatio
  canvas.height = canvas.offsetHeight * devicePixelRatio
  ctx.scale(devicePixelRatio, devicePixelRatio)
  
  const width = canvas.offsetWidth
  const height = canvas.offsetHeight
  
  // Clear canvas
  ctx.fillStyle = '#1e293b' // slate-800
  ctx.fillRect(0, 0, width, height)
  
  // Prepare data
  const data = mlStore.dailyForecast.slice(0, 24) // Show 24 hours max
  const maxPrice = Math.max(...data.map(d => d.price_uah_mwh))
  const minPrice = Math.min(...data.map(d => d.price_uah_mwh))
  const priceRange = maxPrice - minPrice || 1
  
  const stepX = width / Math.max(data.length - 1, 1)
  const padding = 20
  
  // Draw price line
  ctx.beginPath()
  ctx.strokeStyle = '#60a5fa' // blue-400
  ctx.lineWidth = 2
  
  data.forEach((point, index) => {
    const x = index * stepX
    const y = height - padding - ((point.price_uah_mwh - minPrice) / priceRange) * (height - 2 * padding)
    
    if (index === 0) {
      ctx.moveTo(x, y)
    } else {
      ctx.lineTo(x, y)
    }
  })
  ctx.stroke()
  
  // Draw action indicators
  data.forEach((point, index) => {
    const x = index * stepX
    const y = height - padding - ((point.price_uah_mwh - minPrice) / priceRange) * (height - 2 * padding)
    
    // Action color
    let color = '#6b7280' // gray-500
    if (point.action === 'BUY') color = '#22c55e' // green-500
    if (point.action === 'SELL') color = '#3b82f6' // blue-500
    
    // Draw circle
    ctx.beginPath()
    ctx.fillStyle = color
    ctx.arc(x, y, 4, 0, 2 * Math.PI)
    ctx.fill()
    
    // Draw action label at bottom
    if (index % 3 === 0) { // Show every 3rd hour to avoid crowding
      ctx.fillStyle = '#94a3b8' // slate-400
      ctx.font = '10px Inter'
      ctx.textAlign = 'center'
      ctx.fillText(`${point.hour}h`, x, height - 5)
    }
  })
  
  // Draw price labels
  ctx.fillStyle = '#94a3b8' // slate-400
  ctx.font = '10px Inter'
  ctx.textAlign = 'left'
  ctx.fillText(`₴${Math.round(maxPrice/1000)}`, 5, padding)
  ctx.fillText(`₴${Math.round(minPrice/1000)}`, 5, height - padding)
}

// Watch for data changes and redraw
watch(() => mlStore.dailyForecast, () => {
  nextTick(() => {
    drawChart()
  })
}, { deep: true })

// Handle window resize
const handleResize = () => {
  nextTick(() => {
    drawChart()
  })
}

onMounted(() => {
  drawChart()
  window.addEventListener('resize', handleResize)
})
</script>