<template>
  <div class="space-y-8">
    <div>
      <h1 class="text-4xl font-bold text-energy-400 mb-2">Price Analytics</h1>
      <p class="text-slate-400">OREE market analysis & arbitrage opportunities</p>
    </div>

    <!-- Price Levels -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div class="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-lg p-6">
        <h2 class="text-2xl font-bold text-white mb-6">Price Levels Analysis</h2>
        <div class="space-y-4">
          <div class="flex items-center justify-between p-4 bg-slate-800 rounded-lg">
            <div>
              <p class="text-slate-400 text-sm mb-1">Current Weighted Price</p>
              <p class="text-3xl font-bold text-energy-400">{{ (metrics.prices.current.weighted / 1000).toFixed(2) }} ₴/kWh</p>
            </div>
            <div class="text-4xl">⚡</div>
          </div>

          <div class="grid grid-cols-3 gap-3 pt-2">
            <div class="bg-gradient-to-br from-blue-900 to-slate-800 rounded-lg p-3 border border-blue-700">
              <p class="text-blue-400 text-xs font-semibold">BASE</p>
              <p class="text-xl font-bold text-blue-300">{{ (metrics.prices.current.base / 1000).toFixed(2) }}₴</p>
            </div>
            <div class="bg-gradient-to-br from-red-900 to-slate-800 rounded-lg p-3 border border-red-700">
              <p class="text-red-400 text-xs font-semibold">PEAK (+14.1%)</p>
              <p class="text-xl font-bold text-red-300">{{ (metrics.prices.current.peak / 1000).toFixed(2) }}₴</p>
            </div>
            <div class="bg-gradient-to-br from-green-900 to-slate-800 rounded-lg p-3 border border-green-700">
              <p class="text-green-400 text-xs font-semibold">OFF-PEAK (-14.1%)</p>
              <p class="text-xl font-bold text-green-300">{{ (metrics.prices.current.offpeak / 1000).toFixed(2) }}₴</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Statistics -->
      <div class="bg-slate-900 border border-slate-800 rounded-lg p-6">
        <h2 class="text-xl font-bold text-white mb-4">Market Statistics</h2>
        <div class="space-y-3">
          <div>
            <p class="text-slate-400 text-sm">Min (7d)</p>
            <p class="text-2xl font-bold text-green-500">{{ (metrics.prices.daily.min / 1000).toFixed(2) }}₴</p>
          </div>
          <div>
            <p class="text-slate-400 text-sm">Max (7d)</p>
            <p class="text-2xl font-bold text-red-500">{{ (metrics.prices.daily.max / 1000).toFixed(2) }}₴</p>
          </div>
          <div>
            <p class="text-slate-400 text-sm">Avg (7d)</p>
            <p class="text-2xl font-bold text-blue-500">{{ (metrics.prices.daily.avg / 1000).toFixed(2) }}₴</p>
          </div>
          <div class="pt-3 border-t border-slate-700">
            <p class="text-slate-400 text-sm">Volatility</p>
            <p class="text-lg font-bold text-yellow-500">{{ ((metrics.prices.daily.volatility / metrics.prices.daily.avg) * 100).toFixed(1) }}%</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Arbitrage Opportunities -->
    <div class="bg-slate-900 border border-slate-800 rounded-lg p-6">
      <h2 class="text-2xl font-bold text-white mb-6">⚡ Arbitrage Opportunities</h2>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div class="bg-gradient-to-br from-green-900 to-slate-800 border border-green-700 rounded-lg p-4">
          <p class="text-green-400 font-semibold mb-2">BUY ZONE</p>
          <p class="text-3xl font-bold text-green-300">{{ (metrics.prices.daily.min / 1000).toFixed(1) }}₴</p>
          <p class="text-sm text-slate-400 mt-2">Minimum price observed</p>
        </div>

        <div class="bg-gradient-to-br from-yellow-900 to-slate-800 border border-yellow-700 rounded-lg p-4">
          <p class="text-yellow-400 font-semibold mb-2">SPREAD</p>
          <p class="text-3xl font-bold text-yellow-300">{{ (metrics.prices.arbitrage.spread / 1000).toFixed(1) }}₴</p>
          <p class="text-sm text-slate-400 mt-2">Max arbitrage opportunity</p>
        </div>

        <div class="bg-gradient-to-br from-red-900 to-slate-800 border border-red-700 rounded-lg p-4">
          <p class="text-red-400 font-semibold mb-2">SELL ZONE</p>
          <p class="text-3xl font-bold text-red-300">{{ (metrics.prices.daily.max / 1000).toFixed(1) }}₴</p>
          <p class="text-sm text-slate-400 mt-2">Maximum price observed</p>
        </div>
      </div>

      <div class="mt-6 p-4 bg-gradient-to-r from-energy-900 to-slate-800 rounded-lg border border-energy-700">
        <p class="text-energy-300 font-semibold mb-2">💰 Daily Arbitrage Potential</p>
        <p class="text-2xl font-bold text-energy-400">{{ (metrics.prices.arbitrage.daily_max / 1000).toFixed(0) }}k₴ <span class="text-sm text-slate-400">(max theoretical)</span></p>
        <p class="text-sm text-slate-400 mt-2">For 50kW system with 1,200 kWh daily capacity</p>
      </div>
    </div>

    <!-- 7-Day Trend -->
    <div class="bg-slate-900 border border-slate-800 rounded-lg p-6">
      <h2 class="text-2xl font-bold text-white mb-6">7-Day Price Trend</h2>
      <div class="space-y-3">
        <div v-for="day in trendData" :key="day.date" class="flex items-center gap-4">
          <span class="w-20 text-slate-400 text-sm">{{ day.date }}</span>
          <div class="flex-1 flex items-end gap-2 h-12">
            <div class="flex-1 bg-green-600 rounded-t-lg opacity-70" :style="{ height: day.minPercent + '%' }" title="Min"></div>
            <div class="flex-1 bg-blue-600 rounded-t-lg" :style="{ height: day.avgPercent + '%' }" title="Avg"></div>
            <div class="flex-1 bg-red-600 rounded-t-lg opacity-70" :style="{ height: day.maxPercent + '%' }" title="Max"></div>
          </div>
          <span class="w-20 text-right text-slate-400 text-xs">
            {{ day.min }}-{{ day.max }}₴
          </span>
        </div>
      </div>
      <div class="mt-6 flex gap-6 justify-center text-sm">
        <div class="flex items-center gap-2">
          <div class="w-4 h-4 bg-green-600 rounded"></div>
          <span class="text-slate-400">Min</span>
        </div>
        <div class="flex items-center gap-2">
          <div class="w-4 h-4 bg-blue-600 rounded"></div>
          <span class="text-slate-400">Avg</span>
        </div>
        <div class="flex items-center gap-2">
          <div class="w-4 h-4 bg-red-600 rounded"></div>
          <span class="text-slate-400">Max</span>
        </div>
      </div>
    </div>

    <!-- Load Shifting Opportunities -->
    <div class="bg-slate-900 border border-slate-800 rounded-lg p-6">
      <h2 class="text-2xl font-bold text-white mb-4">Load Shifting Strategy</h2>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div class="bg-slate-800 rounded-lg p-4">
          <p class="text-slate-400 text-sm mb-2">Peak Hours (High Cost)</p>
          <p class="text-2xl font-bold text-red-400">08:00 - 22:00</p>
          <p class="text-xs text-slate-500 mt-2">Price 14% above base</p>
        </div>
        <div class="bg-slate-800 rounded-lg p-4">
          <p class="text-slate-400 text-sm mb-2">Off-Peak Hours (Low Cost)</p>
          <p class="text-2xl font-bold text-green-400">22:00 - 08:00</p>
          <p class="text-xs text-slate-500 mt-2">Price 14% below base</p>
        </div>
      </div>
      <div class="mt-4 p-4 bg-gradient-to-r from-slate-800 to-slate-700 rounded-lg">
        <p class="text-slate-300 text-sm">
          <strong>Strategy:</strong> Shift 50kW load to off-peak hours for 8 hours
          <br><strong>Daily Potential:</strong> <span class="text-green-400 font-bold">617.91₴</span>
        </p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useEnergyMetrics } from '~/composables/useEnergyMetrics'
import { computed } from 'vue'

definePageMeta({
  layout: 'default'
})

const metrics = useEnergyMetrics()

const trendData = computed(() => [
  {
    date: 'Feb 1',
    min: '6.5₴',
    minPercent: 43,
    avg: '11.4₴',
    avgPercent: 76,
    max: '15.0₴',
    maxPercent: 100
  },
  {
    date: 'Feb 2',
    min: '5.4₴',
    minPercent: 36,
    avg: '9.4₴',
    avgPercent: 62,
    max: '14.9₴',
    maxPercent: 99
  },
  {
    date: 'Feb 3',
    min: '5.0₴',
    minPercent: 33,
    avg: '9.6₴',
    avgPercent: 64,
    max: '15.0₴',
    maxPercent: 100
  },
  {
    date: 'Feb 4',
    min: '5.4₴',
    minPercent: 36,
    avg: '10.7₴',
    avgPercent: 71,
    max: '15.0₴',
    maxPercent: 100
  },
  {
    date: 'Feb 5',
    min: '5.4₴',
    minPercent: 36,
    avg: '10.6₴',
    avgPercent: 70,
    max: '14.9₴',
    maxPercent: 99
  },
  {
    date: 'Feb 6',
    min: '5.4₴',
    minPercent: 36,
    avg: '11.4₴',
    avgPercent: 76,
    max: '15.0₴',
    maxPercent: 100
  },
  {
    date: 'Feb 7',
    min: '5.6₴',
    minPercent: 37,
    avg: '10.8₴',
    avgPercent: 72,
    max: '14.9₴',
    maxPercent: 99
  }
])
</script>
