<template>
  <div class="space-y-8">
    <div>
      <h1 class="text-4xl font-bold text-energy-400 mb-2">Battery Control</h1>
      <p class="text-slate-400">Real-time optimization & manual control</p>
    </div>

    <!-- Battery Status -->
    <div class="bg-slate-900 border border-slate-800 rounded-lg p-6">
      <h2 class="text-2xl font-bold text-white mb-6">Battery Status</h2>
      
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <!-- SOC Display -->
        <div>
          <div class="flex justify-between items-center mb-2">
            <span class="text-slate-300">State of Charge</span>
            <span class="text-3xl font-bold text-energy-400">75%</span>
          </div>
          <div class="w-full bg-slate-700 rounded-full h-4 overflow-hidden">
            <div class="h-full bg-gradient-to-r from-green-500 via-yellow-500 to-red-500" style="width: 75%"></div>
          </div>
          <div class="flex justify-between text-sm text-slate-400 mt-2">
            <span>112.5 kWh / 150 kWh</span>
            <span>Min: 15 kWh | Max: 142.5 kWh</span>
          </div>
        </div>

        <!-- Power Flow -->
        <div>
          <div class="grid grid-cols-2 gap-4">
            <div class="bg-slate-800 rounded p-4">
              <p class="text-slate-400 text-sm mb-2">Charging Power</p>
              <p class="text-2xl font-bold text-green-400">25 kW</p>
              <p class="text-xs text-slate-500">Efficiency: 95%</p>
            </div>
            <div class="bg-slate-800 rounded p-4">
              <p class="text-slate-400 text-sm mb-2">Available Power</p>
              <p class="text-2xl font-bold text-yellow-400">50 kW</p>
              <p class="text-xs text-slate-500">Max rate</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Control Panel -->
    <div class="bg-slate-900 border border-slate-800 rounded-lg p-6">
      <h2 class="text-2xl font-bold text-white mb-6">Control Panel</h2>
      
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <!-- Charge Control -->
        <div class="border border-slate-700 rounded-lg p-4">
          <h3 class="text-lg font-semibold text-white mb-4">Charging Strategy</h3>
          <div class="space-y-3">
            <div>
              <label class="block text-slate-300 text-sm mb-2">Target SOC</label>
              <input type="range" min="10" max="95" value="75" class="w-full">
              <div class="flex justify-between text-xs text-slate-400 mt-1">
                <span>Min 10%</span>
                <span>75%</span>
                <span>Max 95%</span>
              </div>
            </div>
            <div>
              <label class="block text-slate-300 text-sm mb-2">Charge Rate</label>
              <select class="w-full bg-slate-800 border border-slate-700 rounded px-3 py-2 text-white">
                <option>Conservative (25 kW)</option>
                <option selected>Balanced (40 kW)</option>
                <option>Aggressive (50 kW)</option>
              </select>
            </div>
            <button class="w-full bg-green-600 hover:bg-green-700 text-white font-semibold py-2 rounded mt-3">
              ↑ Start Charging
            </button>
          </div>
        </div>

        <!-- Discharge Control -->
        <div class="border border-slate-700 rounded-lg p-4">
          <h3 class="text-lg font-semibold text-white mb-4">Discharging Strategy</h3>
          <div class="space-y-3">
            <div>
              <label class="block text-slate-300 text-sm mb-2">Min Reserve</label>
              <input type="range" min="10" max="50" value="20" class="w-full">
              <div class="flex justify-between text-xs text-slate-400 mt-1">
                <span>10%</span>
                <span>20%</span>
                <span>50%</span>
              </div>
            </div>
            <div>
              <label class="block text-slate-300 text-sm mb-2">Discharge Rate</label>
              <select class="w-full bg-slate-800 border border-slate-700 rounded px-3 py-2 text-white">
                <option>Conservative (25 kW)</option>
                <option selected>Balanced (40 kW)</option>
                <option>Aggressive (50 kW)</option>
              </select>
            </div>
            <button class="w-full bg-red-600 hover:bg-red-700 text-white font-semibold py-2 rounded mt-3">
              ↓ Start Discharging
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Today's Activity -->
    <div class="bg-slate-900 border border-slate-800 rounded-lg p-6">
      <h2 class="text-2xl font-bold text-white mb-6">Today's Activity (Feb 6)</h2>
      
      <div class="grid grid-cols-3 gap-4 mb-6">
        <div class="bg-slate-800 rounded p-3">
          <p class="text-slate-400 text-sm">Charge Cycles</p>
          <p class="text-2xl font-bold text-energy-400">3</p>
        </div>
        <div class="bg-slate-800 rounded p-3">
          <p class="text-slate-400 text-sm">Energy In</p>
          <p class="text-2xl font-bold text-green-400">120 kWh</p>
        </div>
        <div class="bg-slate-800 rounded p-3">
          <p class="text-slate-400 text-sm">Energy Out</p>
          <p class="text-2xl font-bold text-yellow-400">110 kWh</p>
        </div>
      </div>

      <div class="bg-slate-800 rounded p-4">
        <p class="text-slate-300"><strong>Loss Rate:</strong> 10 kWh (8.3% typical for LiFePO4)</p>
        <p class="text-slate-300 mt-2"><strong>Health:</strong> 98% | <strong>Cycles:</strong> 3,245 remaining</p>
      </div>
    </div>

    <!-- Safety Settings -->
    <div class="bg-slate-900 border border-slate-800 rounded-lg p-6">
      <h2 class="text-2xl font-bold text-white mb-4">Safety & Limits</h2>
      
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div class="bg-slate-800 rounded p-3">
          <p class="text-slate-400 text-xs mb-1">Max Charge</p>
          <p class="text-lg font-bold text-white">50 kW</p>
          <p class="text-xs text-green-400">✓ Safe</p>
        </div>
        <div class="bg-slate-800 rounded p-3">
          <p class="text-slate-400 text-xs mb-1">Max Discharge</p>
          <p class="text-lg font-bold text-white">50 kW</p>
          <p class="text-xs text-green-400">✓ Safe</p>
        </div>
        <div class="bg-slate-800 rounded p-3">
          <p class="text-slate-400 text-xs mb-1">Min Temp</p>
          <p class="text-lg font-bold text-white">-10°C</p>
          <p class="text-xs text-blue-400">Current: 22°C</p>
        </div>
        <div class="bg-slate-800 rounded p-3">
          <p class="text-slate-400 text-xs mb-1">Max Temp</p>
          <p class="text-lg font-bold text-white">55°C</p>
          <p class="text-xs text-blue-400">Current: 22°C</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  layout: 'default'
})
</script>
