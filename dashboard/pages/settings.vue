<template>
  <div class="space-y-8">
    <div>
      <h1 class="text-4xl font-bold text-energy-400 mb-2">Settings</h1>
      <p class="text-slate-400">System configuration & preferences</p>
    </div>

    <!-- System Configuration -->
    <div class="bg-slate-900 border border-slate-800 rounded-lg p-6">
      <h2 class="text-2xl font-bold text-white mb-4">System Configuration</h2>
      
      <div class="space-y-4">
        <div>
          <label class="block text-slate-300 font-semibold mb-2">Battery Capacity</label>
          <input type="text" value="150 kWh" disabled class="w-full bg-slate-800 border border-slate-700 rounded px-3 py-2 text-white">
          <p class="text-xs text-slate-500 mt-1">LiFePO4 Battery System</p>
        </div>

        <div>
          <label class="block text-slate-300 font-semibold mb-2">Max Import Power</label>
          <input type="number" value="100" class="w-full bg-slate-800 border border-slate-700 rounded px-3 py-2 text-white">
          <p class="text-xs text-slate-500 mt-1">Maximum grid import in kW</p>
        </div>

        <div>
          <label class="block text-slate-300 font-semibold mb-2">Optimization Mode</label>
          <select class="w-full bg-slate-800 border border-slate-700 rounded px-3 py-2 text-white">
            <option>Conservative (minimize grid dependence)</option>
            <option selected>Balanced (maximize savings)</option>
            <option>Aggressive (highest arbitrage)</option>
            <option>Manual Control</option>
          </select>
        </div>

        <div>
          <label class="block text-slate-300 font-semibold mb-2">Price Alert Threshold</label>
          <input type="number" value="5" class="w-full bg-slate-800 border border-slate-700 rounded px-3 py-2 text-white">
          <p class="text-xs text-slate-500 mt-1">Alert when price drops below ₴/kWh</p>
        </div>
      </div>
    </div>

    <!-- API Configuration -->
    <div class="bg-slate-900 border border-slate-800 rounded-lg p-6">
      <h2 class="text-2xl font-bold text-white mb-4">API Configuration</h2>
      
      <div class="space-y-4">
        <div>
          <label class="block text-slate-300 font-semibold mb-2">OREE API Endpoint</label>
          <input type="text" value="https://www.oree.com.ua/index.php/pricectr" disabled class="w-full bg-slate-800 border border-slate-700 rounded px-3 py-2 text-white text-sm">
        </div>

        <div>
          <label class="block text-slate-300 font-semibold mb-2">Data Update Interval</label>
          <select class="w-full bg-slate-800 border border-slate-700 rounded px-3 py-2 text-white">
            <option>Every 15 minutes</option>
            <option selected>Every 30 minutes</option>
            <option>Every hour</option>
            <option>Manual updates</option>
          </select>
        </div>

        <div>
          <label class="flex items-center mt-4">
            <input type="checkbox" checked class="rounded">
            <span class="ml-3 text-slate-300">Enable real-time notifications</span>
          </label>
        </div>
      </div>
    </div>

    <!-- ML Model Settings -->
    <div class="bg-slate-900 border border-slate-800 rounded-lg p-6">
      <h2 class="text-2xl font-bold text-white mb-4">ML Model Configuration</h2>
      
      <div class="bg-slate-800 rounded p-4 mb-4">
        <div class="grid grid-cols-2 gap-4">
          <div>
            <p class="text-slate-400 text-sm">Model Type</p>
            <p class="font-semibold text-white">PPO (Proximal Policy Optimization)</p>
          </div>
          <div>
            <p class="text-slate-400 text-sm">Status</p>
            <p class="font-semibold text-green-400">✓ Active</p>
          </div>
          <div>
            <p class="text-slate-400 text-sm">Policy</p>
            <p class="font-semibold text-white">MlpPolicy (Multi-Layer Perceptron)</p>
          </div>
          <div>
            <p class="text-slate-400 text-sm">Performance</p>
            <p class="font-semibold text-energy-400">57.9% savings</p>
          </div>
        </div>
      </div>

      <div class="space-y-4">
        <div>
          <label class="block text-slate-300 font-semibold mb-2">Learning Rate</label>
          <input type="text" value="3e-4" disabled class="w-full bg-slate-800 border border-slate-700 rounded px-3 py-2 text-white">
        </div>

        <div>
          <label class="block text-slate-300 font-semibold mb-2">Batch Size</label>
          <input type="number" value="64" disabled class="w-full bg-slate-800 border border-slate-700 rounded px-3 py-2 text-white">
        </div>

        <div>
          <label class="flex items-center mt-4">
            <input type="checkbox" checked disabled class="rounded">
            <span class="ml-3 text-slate-300">Auto-retrain on new data</span>
          </label>
        </div>
      </div>
    </div>

    <!-- Notifications -->
    <div class="bg-slate-900 border border-slate-800 rounded-lg p-6">
      <h2 class="text-2xl font-bold text-white mb-4">Notifications</h2>
      
      <div class="space-y-3">
        <label class="flex items-center">
          <input type="checkbox" checked class="rounded">
          <span class="ml-3 text-slate-300">Price alerts</span>
          <span class="ml-auto text-sm text-green-400">Enabled</span>
        </label>

        <label class="flex items-center">
          <input type="checkbox" checked class="rounded">
          <span class="ml-3 text-slate-300">Battery warnings</span>
          <span class="ml-auto text-sm text-green-400">Enabled</span>
        </label>

        <label class="flex items-center">
          <input type="checkbox" class="rounded">
          <span class="ml-3 text-slate-300">Daily summary email</span>
          <span class="ml-auto text-sm text-slate-500">Disabled</span>
        </label>

        <label class="flex items-center">
          <input type="checkbox" checked class="rounded">
          <span class="ml-3 text-slate-300">Telegram notifications</span>
          <span class="ml-auto text-sm text-green-400">Enabled</span>
        </label>
      </div>
    </div>

    <!-- Save Settings -->
    <div class="flex gap-4">
      <button class="flex-1 bg-energy-500 hover:bg-energy-600 text-white font-semibold py-3 rounded-lg transition">
        Save Settings
      </button>
      <button class="flex-1 bg-slate-800 hover:bg-slate-700 text-white font-semibold py-3 rounded-lg transition border border-slate-700">
        Reset to Defaults
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  layout: 'default'
})
</script>
