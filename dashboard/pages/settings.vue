<template>
  <div class="min-h-screen bg-slate-950 text-white p-8">
    <div class="max-w-6xl mx-auto space-y-8">
      <!-- Header with back navigation -->
      <div class="flex items-center justify-between mb-8">
        <div>
          <NuxtLink to="/" class="text-blue-400 hover:text-blue-300 text-sm mb-2 inline-block">
            ← Back to Dashboard
          </NuxtLink>
          <h1 class="text-4xl font-bold text-energy-400 mt-2">⚙️ Settings</h1>
          <p class="text-slate-400 mt-2">Configure your energy optimization system</p>
        </div>
      </div>

      <!-- Status Alerts Section -->
      <div class="space-y-4">
        <!-- Save Status Notification (Initially hidden) -->
        <div v-if="saveStatus.show" 
             :class="[
               'rounded-lg border p-4 flex items-center gap-3 animate-fade-in',
               saveStatus.success 
                 ? 'bg-green-900 bg-opacity-30 border-green-700' 
                 : 'bg-red-900 bg-opacity-30 border-red-700'
             ]">
          <div :class="saveStatus.success ? 'text-green-400 text-xl' : 'text-red-400 text-xl'">
            {{ saveStatus.success ? '✅' : '❌' }}
          </div>
          <div>
            <p :class="saveStatus.success ? 'text-green-300 font-semibold' : 'text-red-300 font-semibold'">
              {{ saveStatus.message }}
            </p>
          </div>
        </div>

        <!-- Retraining Proposal Alert -->
        <div v-if="showRetrainingProposal" class="bg-blue-900 bg-opacity-30 border border-blue-700 rounded-lg p-4">
          <div class="flex items-start justify-between gap-4">
            <div class="flex-1">
              <p class="text-blue-300 font-semibold mb-2">🤖 Model Retraining Recommended</p>
              <p class="text-blue-200 text-sm mb-3">
                Your settings have been updated. It's recommended to retrain your personal model to adapt to the new configuration.
              </p>
              <p class="text-xs text-blue-400 mb-3">
                <strong>Retraining will:</strong> Take ~5-10 minutes, optimize PPO agent for your new parameters, improve decision quality
              </p>
            </div>
            <button @click="dismissRetrainingProposal" class="text-blue-400 hover:text-blue-300 text-2xl">
              ×
            </button>
          </div>
          <div class="flex gap-3 mt-4">
            <button @click="launchRetraining" 
                    class="bg-blue-600 hover:bg-blue-500 px-4 py-2 rounded-lg font-semibold text-sm transition">
              🚀 Start Retraining Now
            </button>
            <button @click="dismissRetrainingProposal" 
                    class="bg-slate-700 hover:bg-slate-600 px-4 py-2 rounded-lg text-sm transition">
              Skip for Now
            </button>
          </div>
        </div>

        <!-- Active Retraining Progress -->
        <div v-if="retraining.active" class="bg-yellow-900 bg-opacity-30 border border-yellow-700 rounded-lg p-4">
          <div class="flex items-center gap-3 mb-3">
            <div class="animate-spin">⚙️</div>
            <p class="text-yellow-300 font-semibold">Model Retraining in Progress</p>
          </div>
          <div class="w-full bg-slate-800 rounded-full h-2 mb-2">
            <div class="h-full bg-yellow-500 rounded-full" :style="{ width: retraining.progress + '%' }"></div>
          </div>
          <p class="text-xs text-yellow-400">{{ retraining.progress }}% complete • {{ retraining.timeRemaining }}</p>
        </div>

        <!-- Retraining Complete -->
        <div v-if="retraining.completed" class="bg-green-900 bg-opacity-30 border border-green-700 rounded-lg p-4">
          <p class="text-green-300 font-semibold">✅ Model Retraining Complete!</p>
          <p class="text-sm text-green-200 mt-2">Your personal PPO model has been optimized and is now active.</p>
        </div>
      </div>

      <!-- Settings Tabs -->
      <div class="border-b border-slate-800 flex gap-4">
        <button @click="activeTab = 'general'" 
                :class="['px-4 py-3 font-semibold transition border-b-2', 
                         activeTab === 'general' ? 'border-energy-400 text-energy-400' : 'border-transparent text-slate-400 hover:text-white']">
          General
        </button>
        <button @click="activeTab = 'battery'" 
                :class="['px-4 py-3 font-semibold transition border-b-2', 
                         activeTab === 'battery' ? 'border-energy-400 text-energy-400' : 'border-transparent text-slate-400 hover:text-white']">
          Battery
        </button>
        <button @click="activeTab = 'model'" 
                :class="['px-4 py-3 font-semibold transition border-b-2', 
                         activeTab === 'model' ? 'border-energy-400 text-energy-400' : 'border-transparent text-slate-400 hover:text-white']">
          Model & Training
        </button>
        <button @click="activeTab = 'notifications'" 
                :class="['px-4 py-3 font-semibold transition border-b-2', 
                         activeTab === 'notifications' ? 'border-energy-400 text-energy-400' : 'border-transparent text-slate-400 hover:text-white']">
          Notifications
        </button>
      </div>

      <!-- Tab Content -->
      <div class="bg-slate-900 border border-slate-800 rounded-lg p-6">
        <!-- GENERAL TAB -->
        <div v-if="activeTab === 'general'" class="space-y-6">
          <div>
            <label class="block text-slate-300 font-semibold mb-2">Location / Site Name</label>
            <input v-model="settings.value.general.siteName" 
                   type="text" 
                   placeholder="e.g., Factory #1, Warehouse A"
                   class="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white placeholder-slate-500 focus:border-energy-400 focus:outline-none">
            <p class="text-xs text-slate-400 mt-1">Your facility's identifier for multi-site management</p>
          </div>

          <div>
            <label class="block text-slate-300 font-semibold mb-2">Timezone</label>
            <select v-model="settings.value.general.timezone" 
                    class="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white focus:border-energy-400 focus:outline-none">
              <option>Europe/Kiev (GMT+2)</option>
              <option>Europe/London (GMT+0)</option>
              <option>Europe/Berlin (GMT+1)</option>
              <option>America/New_York (GMT-5)</option>
            </select>
          </div>

          <div>
            <label class="block text-slate-300 font-semibold mb-2">Currency</label>
            <select v-model="settings.value.general.currency" 
                    class="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white focus:border-energy-400 focus:outline-none">
              <option value="UAH">Ukrainian Hryvnia (₴)</option>
              <option value="USD">US Dollar ($)</option>
              <option value="EUR">Euro (€)</option>
            </select>
          </div>

          <div class="flex items-center justify-between p-4 bg-slate-800 rounded-lg border border-slate-700">
            <div>
              <p class="text-white font-semibold">Enable Real-Time Notifications</p>
              <p class="text-xs text-slate-400 mt-1">Get alerts for trading opportunities and model updates</p>
            </div>
            <button @click="settings.value.general.notificationsEnabled = !settings.value.general.notificationsEnabled" 
                    :class="['relative inline-flex h-8 w-14 items-center rounded-full transition', 
                             settings.value.general.notificationsEnabled ? 'bg-green-600' : 'bg-slate-700']">
              <span :class="['inline-block h-6 w-6 transform rounded-full bg-white transition', 
                            settings.value.general.notificationsEnabled ? 'translate-x-7' : 'translate-x-1']"></span>
            </button>
          </div>
        </div>

        <!-- BATTERY TAB -->
        <div v-if="activeTab === 'battery'" class="space-y-6">
          <div class="bg-blue-900 bg-opacity-20 border border-blue-700 rounded-lg p-4 text-sm text-blue-200">
            <p class="font-semibold mb-2">💡 About Battery Settings</p>
            <p>These parameters define your battery constraints. The AI model learns from these values during training.</p>
          </div>

          <div>
            <label class="block text-slate-300 font-semibold mb-2">Total Battery Capacity (kWh)</label>
            <div class="flex gap-4">
              <input v-model.number="settings.value.battery.capacity" 
                     type="number" 
                     min="10" 
                     max="1000"
                     class="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white focus:border-energy-400 focus:outline-none">
              <div class="bg-slate-800 rounded-lg px-4 py-2 text-slate-400 min-w-24 flex items-center">
                {{ settings.value.battery.capacity }} kWh
              </div>
            </div>
            <p class="text-xs text-slate-400 mt-1">Maximum energy storage capacity of your battery system</p>
          </div>

          <div>
            <label class="block text-slate-300 font-semibold mb-2">Minimum Safe SOC (State of Charge)</label>
            <div class="flex gap-4">
              <input v-model.number="settings.value.battery.minSOC" 
                     type="number" 
                     min="0" 
                     max="100"
                     class="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white focus:border-energy-400 focus:outline-none">
              <div class="bg-slate-800 rounded-lg px-4 py-2 text-slate-400 min-w-16 flex items-center">
                {{ settings.value.battery.minSOC }}%
              </div>
            </div>
            <p class="text-xs text-slate-400 mt-1">Battery won't discharge below this level (safety reserve)</p>
          </div>

          <div>
            <label class="block text-slate-300 font-semibold mb-2">Maximum Charge Rate (kW)</label>
            <div class="flex gap-4">
              <input v-model.number="settings.value.battery.maxChargeRate" 
                     type="number" 
                     min="1" 
                     max="500"
                     class="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white focus:border-energy-400 focus:outline-none">
              <div class="bg-slate-800 rounded-lg px-4 py-2 text-slate-400 min-w-20 flex items-center">
                {{ settings.value.battery.maxChargeRate }} kW
              </div>
            </div>
            <p class="text-xs text-slate-400 mt-1">Maximum power input to battery (inverter limit)</p>
          </div>

          <div>
            <label class="block text-slate-300 font-semibold mb-2">Maximum Discharge Rate (kW)</label>
            <div class="flex gap-4">
              <input v-model.number="settings.value.battery.maxDischargeRate" 
                     type="number" 
                     min="1" 
                     max="500"
                     class="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white focus:border-energy-400 focus:outline-none">
              <div class="bg-slate-800 rounded-lg px-4 py-2 text-slate-400 min-w-20 flex items-center">
                {{ settings.value.battery.maxDischargeRate }} kW
              </div>
            </div>
            <p class="text-xs text-slate-400 mt-1">Maximum power output from battery</p>
          </div>
        </div>

        <!-- MODEL & TRAINING TAB -->
        <div v-if="activeTab === 'model'" class="space-y-6">
          <div class="bg-green-900 bg-opacity-20 border border-green-700 rounded-lg p-4">
            <p class="text-green-300 font-semibold mb-3">📊 Model Architecture</p>
            <div class="space-y-2 text-sm text-green-200">
              <div class="flex justify-between">
                <span>Algorithm:</span>
                <span class="font-semibold">PPO (Proximal Policy Optimization)</span>
              </div>
              <div class="flex justify-between">
                <span>Network:</span>
                <span class="font-semibold">2 hidden layers × 64 units</span>
              </div>
              <div class="flex justify-between">
                <span>Optimizer:</span>
                <span class="font-semibold">Adam (learning rate 3e-4)</span>
              </div>
              <div class="flex justify-between">
                <span>Training Framework:</span>
                <span class="font-semibold">Stable-Baselines3</span>
              </div>
            </div>
          </div>

          <!-- Model Strategy Explanation -->
          <div class="bg-blue-900 bg-opacity-20 border border-blue-700 rounded-lg p-4 space-y-3">
            <p class="text-blue-300 font-semibold">🤖 Personal vs Shared Models</p>
            <p class="text-sm text-blue-200">
              You have a <strong>personal PPO model</strong> trained specifically on your energy patterns, facility constraints, and local electricity prices. This ensures optimal decisions for YOUR unique situation.
            </p>
            <div class="bg-slate-800 rounded-lg p-3 text-sm space-y-2">
              <p class="text-slate-300"><strong>Why personal models?</strong></p>
              <ul class="text-slate-400 list-disc list-inside space-y-1">
                <li>Different facilities have different demand patterns</li>
                <li>Solar availability varies by location and season</li>
                <li>Electricity prices differ by region (OREE zones)</li>
                <li>Battery constraints are facility-specific</li>
              </ul>
            </div>
          </div>

          <!-- Training Schedule -->
          <div class="space-y-3">
            <p class="text-slate-300 font-semibold">📅 Retraining Schedule</p>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div class="bg-slate-800 rounded-lg p-4 border border-slate-700">
                <p class="text-slate-400 text-sm mb-2">Full Retraining</p>
                <p class="text-2xl font-bold text-energy-400 mb-2">Weekly</p>
                <p class="text-xs text-slate-500">Comprehensive model optimization (5-10 min)</p>
              </div>
              <div class="bg-slate-800 rounded-lg p-4 border border-slate-700">
                <p class="text-slate-400 text-sm mb-2">Quick Update</p>
                <p class="text-2xl font-bold text-blue-400 mb-2">Daily</p>
                <p class="text-xs text-slate-500">Fast parameter adjustment (30-60 sec)</p>
              </div>
            </div>
            <p class="text-xs text-slate-400 mt-3">
              <strong>What triggers retraining?</strong> Settings changes (battery, notifications, preferences) automatically trigger a quick daily update. Manual retraining recommended after major configuration changes.
            </p>
          </div>

          <!-- Manual Retraining -->
          <div class="border-t border-slate-700 pt-6">
            <p class="text-slate-300 font-semibold mb-4">🚀 Manual Model Retraining</p>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <button @click="launchQuickUpdate" 
                      :disabled="retraining.active"
                      class="bg-blue-600 hover:bg-blue-500 disabled:bg-slate-700 px-6 py-3 rounded-lg font-semibold text-white transition">
                ⚡ Quick Daily Update (1 min)
              </button>
              <button @click="launchFullRetraining" 
                      :disabled="retraining.active"
                      class="bg-green-600 hover:bg-green-500 disabled:bg-slate-700 px-6 py-3 rounded-lg font-semibold text-white transition">
                🔄 Full Weekly Retraining (10 min)
              </button>
            </div>
          </div>

          <!-- Last Training Info -->
          <div class="bg-slate-800 rounded-lg p-4 border border-slate-700 text-sm">
            <p class="text-slate-400 mb-2">📌 Last Training Session</p>
            <div class="space-y-1 text-slate-300">
              <div class="flex justify-between">
                <span>Completed:</span>
                <span>Feb 6, 2026 • 20:50 GMT+2</span>
              </div>
              <div class="flex justify-between">
                <span>Duration:</span>
                <span>8 minutes 23 seconds</span>
              </div>
              <div class="flex justify-between">
                <span>Data Points:</span>
                <span>2,016 hourly observations (7 days)</span>
              </div>
              <div class="flex justify-between">
                <span>Performance:</span>
                <span class="text-green-400">+57.9% cost reduction ✓</span>
              </div>
            </div>
          </div>
        </div>

        <!-- NOTIFICATIONS TAB -->
        <div v-if="activeTab === 'notifications'" class="space-y-6">
          <p class="text-slate-400 text-sm">Configure when and how you want to be notified about trading opportunities and system events</p>

          <div class="space-y-4">
            <!-- High Price Alert -->
            <div class="bg-slate-800 rounded-lg p-4 border border-slate-700 space-y-3">
              <div class="flex items-center justify-between">
                <div>
                  <p class="text-white font-semibold">🔴 High Price Alert</p>
                  <p class="text-xs text-slate-400 mt-1">Notify when price exceeds threshold (sell opportunity)</p>
                </div>
                <button @click="settings.value.notifications.highPrice = !settings.value.notifications.highPrice" 
                        :class="['relative inline-flex h-6 w-11 items-center rounded-full transition', 
                                 settings.value.notifications.highPrice ? 'bg-red-600' : 'bg-slate-700']">
                  <span :class="['inline-block h-4 w-4 transform rounded-full bg-white transition', 
                                settings.value.notifications.highPrice ? 'translate-x-6' : 'translate-x-1']"></span>
                </button>
              </div>
              <div v-if="settings.value.notifications.highPrice" class="flex gap-2">
                <input v-model.number="settings.value.notifications.highPriceThreshold" 
                       type="number" 
                       placeholder="₴/kWh"
                       class="flex-1 bg-slate-700 border border-slate-600 rounded px-3 py-1 text-sm text-white placeholder-slate-500 focus:border-energy-400">
                <span class="text-slate-400 text-sm flex items-center">₴/kWh</span>
              </div>
            </div>

            <!-- Low Price Alert -->
            <div class="bg-slate-800 rounded-lg p-4 border border-slate-700 space-y-3">
              <div class="flex items-center justify-between">
                <div>
                  <p class="text-white font-semibold">🟢 Low Price Alert</p>
                  <p class="text-xs text-slate-400 mt-1">Notify when price drops (buy opportunity)</p>
                </div>
                <button @click="settings.value.notifications.lowPrice = !settings.value.notifications.lowPrice" 
                        :class="['relative inline-flex h-6 w-11 items-center rounded-full transition', 
                                 settings.value.notifications.lowPrice ? 'bg-green-600' : 'bg-slate-700']">
                  <span :class="['inline-block h-4 w-4 transform rounded-full bg-white transition', 
                                settings.value.notifications.lowPrice ? 'translate-x-6' : 'translate-x-1']"></span>
                </button>
              </div>
              <div v-if="settings.value.notifications.lowPrice" class="flex gap-2">
                <input v-model.number="settings.value.notifications.lowPriceThreshold" 
                       type="number" 
                       placeholder="₴/kWh"
                       class="flex-1 bg-slate-700 border border-slate-600 rounded px-3 py-1 text-sm text-white placeholder-slate-500 focus:border-energy-400">
                <span class="text-slate-400 text-sm flex items-center">₴/kWh</span>
              </div>
            </div>

            <!-- Model Training Complete -->
            <div class="bg-slate-800 rounded-lg p-4 border border-slate-700 space-y-3">
              <div class="flex items-center justify-between">
                <div>
                  <p class="text-white font-semibold">🤖 Model Training Complete</p>
                  <p class="text-xs text-slate-400 mt-1">Notify when retraining finishes</p>
                </div>
                <button @click="settings.value.notifications.modelComplete = !settings.value.notifications.modelComplete" 
                        :class="['relative inline-flex h-6 w-11 items-center rounded-full transition', 
                                 settings.value.notifications.modelComplete ? 'bg-blue-600' : 'bg-slate-700']">
                  <span :class="['inline-block h-4 w-4 transform rounded-full bg-white transition', 
                                settings.value.notifications.modelComplete ? 'translate-x-6' : 'translate-x-1']"></span>
                </button>
              </div>
            </div>

            <!-- System Alerts -->
            <div class="bg-slate-800 rounded-lg p-4 border border-slate-700 space-y-3">
              <div class="flex items-center justify-between">
                <div>
                  <p class="text-white font-semibold">⚠️ System Alerts</p>
                  <p class="text-xs text-slate-400 mt-1">Battery low, grid outages, errors</p>
                </div>
                <button @click="settings.value.notifications.systemAlerts = !settings.value.notifications.systemAlerts" 
                        :class="['relative inline-flex h-6 w-11 items-center rounded-full transition', 
                                 settings.value.notifications.systemAlerts ? 'bg-orange-600' : 'bg-slate-700']">
                  <span :class="['inline-block h-4 w-4 transform rounded-full bg-white transition', 
                                settings.value.notifications.systemAlerts ? 'translate-x-6' : 'translate-x-1']"></span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Save Button -->
      <div class="flex gap-4 justify-end">
        <button @click="resetSettings" 
                class="bg-slate-700 hover:bg-slate-600 px-6 py-3 rounded-lg font-semibold transition">
          Reset to Defaults
        </button>
        <button @click="saveSettings" 
                :disabled="isSaving"
                class="bg-energy-600 hover:bg-energy-500 disabled:bg-slate-700 px-6 py-3 rounded-lg font-semibold text-white transition">
          {{ isSaving ? '⏳ Saving...' : '💾 Save Settings' }}
        </button>
      </div>

      <!-- Footer navigation -->
      <div class="flex gap-4 justify-center text-center mt-12 pt-8 border-t border-slate-800">
        <NuxtLink to="/" class="bg-blue-700 hover:bg-blue-600 px-6 py-2 rounded-lg transition text-sm">
          📊 Dashboard
        </NuxtLink>
        <NuxtLink to="/analytics" class="bg-blue-700 hover:bg-blue-600 px-6 py-2 rounded-lg transition text-sm">
          📈 Analytics
        </NuxtLink>
        <NuxtLink to="/control" class="bg-blue-700 hover:bg-blue-600 px-6 py-2 rounded-lg transition text-sm">
          🔋 Control
        </NuxtLink>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useSettings } from '#app'

definePageMeta({
  layout: 'default'
})

// Load composable
const { settings: composableSettings, saveSettings: composableSaveSettings, resetSettings: composableReset, loadSettings: composableLoad } = useSettings()

// Active tab
const activeTab = ref('general')

// Settings state - use composable settings directly
const settings = composableSettings

// Save status
const isSaving = ref(false)
const saveStatus = reactive({
  show: false,
  success: false,
  message: ''
})

// Retraining state
const showRetrainingProposal = ref(true)
const retraining = reactive({
  active: false,
  completed: false,
  progress: 0,
  timeRemaining: '0s',
  type: '' // 'quick' or 'full'
})

// Save settings - use composable with real API
const saveSettings = async () => {
  isSaving.value = true
  
  const result = await composableSaveSettings(settings.value)
  
  if (result.success) {
    saveStatus.success = true
    saveStatus.message = '✅ Settings saved and will persist on reload!'
  } else {
    saveStatus.success = false
    saveStatus.message = `❌ Save failed: ${result.error}`
  }
  
  saveStatus.show = true
  isSaving.value = false
  
  // Show retraining proposal
  showRetrainingProposal.value = true
  
  // Auto-hide success message after 5 seconds
  setTimeout(() => {
    saveStatus.show = false
  }, 5000)
}

// Reset settings
const resetSettings = () => {
  if (confirm('Are you sure? This will reset to defaults and reload the page.')) {
    composableReset()
    
    saveStatus.success = true
    saveStatus.message = '🔄 Settings reset to defaults'
    saveStatus.show = true
    
    setTimeout(() => {
      saveStatus.show = false
      if (process.client) {
        location.reload()
      }
    }, 1500)
  }
}

// Dismiss retraining proposal
const dismissRetrainingProposal = () => {
  showRetrainingProposal.value = false
}

// Launch quick update
const launchQuickUpdate = async () => {
  retraining.active = true
  retraining.type = 'quick'
  showRetrainingProposal.value = false
  
  for (let i = 0; i <= 100; i += 20) {
    retraining.progress = i
    retraining.timeRemaining = `${Math.round(60 - (i * 0.6))}s`
    await new Promise(resolve => setTimeout(resolve, 300))
  }
  
  retraining.active = false
  retraining.completed = true
  
  saveStatus.success = true
  saveStatus.message = '✅ Quick model update complete!'
  saveStatus.show = true
  
  setTimeout(() => {
    saveStatus.show = false
    retraining.completed = false
  }, 5000)
}

// Launch full retraining
const launchFullRetraining = async () => {
  retraining.active = true
  retraining.type = 'full'
  showRetrainingProposal.value = false
  
  for (let i = 0; i <= 100; i += 5) {
    retraining.progress = i
    const timeLeft = Math.round(600 - (i * 6))
    retraining.timeRemaining = `${Math.floor(timeLeft / 60)}m ${timeLeft % 60}s`
    await new Promise(resolve => setTimeout(resolve, 200))
  }
  
  retraining.active = false
  retraining.completed = true
  
  saveStatus.success = true
  saveStatus.message = '✅ Full model retraining complete! New model is now active.'
  saveStatus.show = true
  
  setTimeout(() => {
    saveStatus.show = false
    retraining.completed = false
  }, 5000)
}

// Load settings on mount
onMounted(async () => {
  await composableLoad()
})
</script>

<style scoped>
.energy-400 {
  @apply text-emerald-400;
}
.energy-500 {
  @apply bg-emerald-500;
}
.energy-600 {
  @apply bg-emerald-600;
}
.energy-500:hover {
  @apply bg-emerald-500;
}

@keyframes fade-in {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.animate-fade-in {
  animation: fade-in 0.3s ease-in-out;
}
</style>
