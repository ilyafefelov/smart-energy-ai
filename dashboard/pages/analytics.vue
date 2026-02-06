<template>
  <div class="space-y-8">
    <div>
      <h1 class="text-4xl font-bold text-energy-400 mb-2">Price Analytics</h1>
      <p class="text-slate-400">Real-time OREE market analysis</p>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Price Levels -->
      <div class="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-lg p-6">
        <h2 class="text-2xl font-bold text-white mb-4">Price Levels</h2>
        <div class="space-y-3">
          <div class="flex justify-between items-center">
            <span class="text-slate-300">Current Weighted Price</span>
            <span class="text-2xl font-bold text-energy-400">11.37 ₴/kWh</span>
          </div>
          <div class="flex justify-between items-center pt-3 border-t border-slate-700">
            <span class="text-slate-400">Base</span>
            <span class="text-xl font-bold text-blue-400">10.97 ₴/kWh</span>
          </div>
          <div class="flex justify-between items-center">
            <span class="text-slate-400">Peak</span>
            <span class="text-xl font-bold text-red-400">12.52 ₴/kWh (+14.1%)</span>
          </div>
          <div class="flex justify-between items-center">
            <span class="text-slate-400">Off-Peak</span>
            <span class="text-xl font-bold text-green-400">9.43 ₴/kWh (-14.1%)</span>
          </div>
        </div>
      </div>

      <!-- Market Statistics -->
      <div class="bg-slate-900 border border-slate-800 rounded-lg p-6">
        <h2 class="text-xl font-bold text-white mb-4">Market Stats</h2>
        <div class="space-y-3">
          <div>
            <p class="text-slate-400 text-sm">Min (7d)</p>
            <p class="text-2xl font-bold text-green-500">5.00 ₴</p>
          </div>
          <div>
            <p class="text-slate-400 text-sm">Max (7d)</p>
            <p class="text-2xl font-bold text-red-500">15.00 ₴</p>
          </div>
          <div>
            <p class="text-slate-400 text-sm">Volatility</p>
            <p class="text-2xl font-bold text-yellow-500">13.3%</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Arbitrage Opportunities -->
    <div class="bg-slate-900 border border-slate-800 rounded-lg p-6">
      <h2 class="text-2xl font-bold text-white mb-4">⚡ Arbitrage Opportunities</h2>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div class="bg-green-900 bg-opacity-20 border border-green-700 rounded-lg p-4">
          <p class="text-green-400 font-semibold mb-2">Buy Zone</p>
          <p class="text-3xl font-bold text-green-300">5 ₴</p>
          <p class="text-sm text-slate-400 mt-2">Minimum price observed</p>
        </div>
        <div class="bg-yellow-900 bg-opacity-20 border border-yellow-700 rounded-lg p-4">
          <p class="text-yellow-400 font-semibold mb-2">Spread</p>
          <p class="text-3xl font-bold text-yellow-300">10 ₴</p>
          <p class="text-sm text-slate-400 mt-2">Max arbitrage opportunity</p>
        </div>
        <div class="bg-red-900 bg-opacity-20 border border-red-700 rounded-lg p-4">
          <p class="text-red-400 font-semibold mb-2">Sell Zone</p>
          <p class="text-3xl font-bold text-red-300">15 ₴</p>
          <p class="text-sm text-slate-400 mt-2">Maximum price observed</p>
        </div>
      </div>

      <div class="mt-6 p-4 bg-slate-800 rounded-lg">
        <p class="text-slate-300">
          <strong>Daily Potential:</strong> For a 50kW system with 1,200 kWh daily capacity:
          <span class="text-energy-400 font-semibold">12,000 ₴ maximum arbitrage</span>
          <span class="text-slate-500 text-sm">(if perfect execution)</span>
        </p>
      </div>
    </div>

    <!-- Price Trends -->
    <div class="bg-slate-900 border border-slate-800 rounded-lg p-6">
      <h2 class="text-2xl font-bold text-white mb-4">7-Day Trend</h2>
      <div class="space-y-2">
        <div v-for="day in days" :key="day.date" class="flex items-center justify-between py-2 border-b border-slate-800">
          <span class="text-slate-400">{{ day.date }}</span>
          <div class="flex items-center space-x-4">
            <div class="w-48 h-6 bg-slate-800 rounded overflow-hidden">
              <div class="h-full bg-gradient-to-r from-green-500 to-red-500" :style="{ width: day.range + '%' }"></div>
            </div>
            <span class="text-slate-300 w-24 text-right">{{ day.min }} - {{ day.max }} ₴</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  layout: 'default'
})

const days = ref([
  { date: 'Feb 1', min: 6500, max: 15000, range: 85 },
  { date: 'Feb 2', min: 5400, max: 14973, range: 87 },
  { date: 'Feb 3', min: 5000, max: 15000, range: 90 },
  { date: 'Feb 4', min: 5440, max: 15000, range: 89 },
  { date: 'Feb 5', min: 5400, max: 14997, range: 89 },
  { date: 'Feb 6', min: 5400, max: 15000, range: 90 },
  { date: 'Feb 7', min: 5600, max: 14996, range: 88 },
])
</script>
