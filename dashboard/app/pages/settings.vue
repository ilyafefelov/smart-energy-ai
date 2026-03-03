<template>
  <div class="min-h-screen bg-slate-950 text-white p-8">
    <div class="max-w-6xl mx-auto space-y-8">
      <!-- Header -->
      <div class="flex items-center justify-between mb-8">
        <div>
          <NuxtLink to="/" class="text-blue-400 hover:text-blue-300 text-sm mb-2 inline-block">
            ← Back to Dashboard
          </NuxtLink>
          <h1 class="text-4xl font-bold text-energy-400 mt-2">⚙️ Settings</h1>
          <p class="text-slate-400 mt-2">Configure your energy optimization system</p>
        </div>

        <select
          v-model="selectedTenantId"
          class="px-3 py-2 rounded-md border border-slate-700 bg-slate-900 text-sm"
        >
          <option v-for="tenant in tenantOptions" :key="tenant.id" :value="tenant.id">
            {{ tenant.name || tenant.id }}
          </option>
        </select>
      </div>

      <!-- Status Messages -->
      <div class="space-y-4">
        <!-- Save Success -->
        <div v-if="saveSuccess" class="bg-green-900 bg-opacity-30 border border-green-700 rounded-lg p-4 flex items-center gap-3">
          <span class="text-green-400 text-xl">✅</span>
          <div>
            <p class="text-green-300 font-semibold">Settings saved successfully</p>
            <p class="text-xs text-green-400">All changes have been saved</p>
          </div>
        </div>

        <!-- Save Error -->
        <div v-if="settingsStore.error" class="bg-red-900 bg-opacity-30 border border-red-700 rounded-lg p-4">
          <p class="text-red-300 font-semibold">❌ Error: {{ settingsStore.error }}</p>
          <button @click="settingsStore.clearError" class="text-xs text-red-400 hover:text-red-300 mt-2">Dismiss</button>
        </div>

        <!-- Loading State -->
        <div v-if="settingsStore.isLoading" class="bg-blue-900 bg-opacity-30 border border-blue-700 rounded-lg p-4">
          <p class="text-blue-300 font-semibold">Loading settings...</p>
        </div>
      </div>

      <!-- Quick Overview Cards -->
      <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
        <div class="rounded-xl border border-cyan-700/50 bg-gradient-to-br from-cyan-900/35 to-slate-900 p-4">
          <p class="text-xs uppercase tracking-wider text-cyan-300">Battery Profile</p>
          <p class="mt-2 text-2xl font-bold text-white">{{ settingsStore.settings.battery.capacity }} kWh</p>
          <p class="text-xs text-cyan-200 mt-1">Charge {{ settingsStore.settings.battery.maxChargeRate }} kW • Discharge {{ settingsStore.settings.battery.maxDischargeRate }} kW</p>
        </div>

        <div class="rounded-xl border border-emerald-700/50 bg-gradient-to-br from-emerald-900/35 to-slate-900 p-4">
          <p class="text-xs uppercase tracking-wider text-emerald-300">Safety Window</p>
          <p class="mt-2 text-2xl font-bold text-white">{{ settingsStore.settings.battery.minSOC }}%</p>
          <p class="text-xs text-emerald-200 mt-1">Minimum SOC reserve • {{ usableCapacityEstimate }} kWh usable estimate</p>
        </div>

        <div class="rounded-xl border border-violet-700/50 bg-gradient-to-br from-violet-900/35 to-slate-900 p-4">
          <p class="text-xs uppercase tracking-wider text-violet-300">Model Preset</p>
          <p class="mt-2 text-2xl font-bold text-white">{{ settingsStore.settings.model.epochs }} epochs</p>
          <p class="text-xs text-violet-200 mt-1">Batch {{ settingsStore.settings.model.batchSize }} • LR {{ settingsStore.settings.model.learningRate }}</p>
        </div>

        <div class="rounded-xl border border-amber-700/50 bg-gradient-to-br from-amber-900/35 to-slate-900 p-4">
          <p class="text-xs uppercase tracking-wider text-amber-300">Arbitrage Snapshot</p>
          <p class="mt-2 text-2xl font-bold text-white">₴{{ estimatedDailySpreadRevenue }}</p>
          <p class="text-xs text-amber-200 mt-1">Daily spread estimate • Notifications: {{ enabledNotificationCount }}/4 enabled</p>
        </div>
      </div>

      <!-- Settings Tabs -->
      <div class="border-b border-slate-800 flex gap-4">
        <button 
          v-for="tab in tabs"
          :key="tab.id"
          @click="activeTab = tab.id"
          :class="[
            'px-4 py-3 font-semibold transition border-b-2',
            activeTab === tab.id
              ? 'border-energy-400 text-energy-400'
              : 'border-transparent text-slate-400 hover:text-white'
          ]"
        >
          {{ tab.icon }} {{ tab.label }}
        </button>
      </div>

      <!-- Tab Content -->
      <div class="space-y-8">
        <!-- General Settings -->
        <div v-if="activeTab === 'general'" class="space-y-6">
          <div class="bg-slate-800 bg-opacity-40 border border-slate-700 rounded-lg p-6">
            <h2 class="text-xl font-bold text-white mb-6">General Settings</h2>

            <div class="space-y-4">
              <div>
                <label class="block text-sm font-semibold text-slate-300 mb-2">Site Name</label>
                <input 
                  v-model="settingsStore.settings.general.siteName"
                  type="text"
                  class="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-white placeholder-slate-500 focus:outline-none focus:border-energy-400"
                  placeholder="e.g., Factory #1"
                />
              </div>

              <div>
                <label class="block text-sm font-semibold text-slate-300 mb-2">Timezone</label>
                <select 
                  v-model="settingsStore.settings.general.timezone"
                  class="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-energy-400"
                >
                  <option>Europe/Kiev (GMT+2)</option>
                  <option>UTC</option>
                  <option>Europe/London (GMT)</option>
                </select>
              </div>

              <div>
                <label class="block text-sm font-semibold text-slate-300 mb-2">Currency</label>
                <select 
                  v-model="settingsStore.settings.general.currency"
                  class="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-energy-400"
                >
                  <option>UAH</option>
                  <option>USD</option>
                  <option>EUR</option>
                </select>
              </div>

              <div class="flex items-center gap-3 pt-4">
                <input 
                  v-model="settingsStore.settings.general.notificationsEnabled"
                  type="checkbox"
                  id="notif"
                  class="w-5 h-5 rounded border-slate-700 cursor-pointer"
                />
                <label for="notif" class="text-sm text-slate-300 cursor-pointer">Enable notifications</label>
              </div>
            </div>

            <button 
              @click="saveGeneralSettings"
              :disabled="settingsStore.isSaving"
              class="mt-6 px-6 py-2 bg-energy-400 hover:bg-cyan-300 text-slate-950 font-semibold rounded-lg transition disabled:opacity-50"
            >
              {{ settingsStore.isSaving ? 'Saving...' : 'Save Changes' }}
            </button>
          </div>
        </div>

        <!-- Battery Settings -->
        <div v-if="activeTab === 'battery'" class="space-y-6">
          <BatteryConfigPanel />
        </div>

        <!-- Generation Settings -->
        <div v-if="activeTab === 'generation'" class="space-y-6">
          <GenerationSolarWindConfig />
        </div>

        <!-- Battery Control -->
        <div v-if="activeTab === 'control'" class="space-y-6">
          <BatteryPhysicsSimulator />
        </div>

        <!-- Scenario Management -->
        <div v-if="activeTab === 'scenarios'" class="space-y-6">
          <ScenarioManager />
        </div>

        <!-- Optimization Preferences -->
        <div v-if="activeTab === 'preferences'" class="space-y-6">
          <PreferencesOptimizationProfile />
        </div>

        <!-- Notification Settings -->
        <div v-if="activeTab === 'notifications'" class="space-y-6">
          <div class="bg-slate-800 bg-opacity-40 border border-slate-700 rounded-lg p-6">
            <h2 class="text-xl font-bold text-white mb-6">Notification Preferences</h2>

            <div class="space-y-4">
              <div class="flex items-center justify-between">
                <div>
                  <p class="text-sm font-semibold text-slate-300">High Price Alerts</p>
                  <p class="text-xs text-slate-400">Notify when price exceeds threshold</p>
                </div>
                <input 
                  v-model="settingsStore.settings.notifications.highPrice"
                  type="checkbox"
                  class="w-5 h-5 rounded cursor-pointer"
                />
              </div>

              <div v-if="settingsStore.settings.notifications.highPrice" class="pl-4 border-l-2 border-slate-700">
                <label class="block text-xs font-semibold text-slate-300 mb-2">Threshold (₴/kWh)</label>
                <input 
                  v-model.number="settingsStore.settings.notifications.highPriceThreshold"
                  type="number"
                  min="0"
                  step="0.1"
                  class="w-full max-w-xs bg-slate-900 border border-slate-700 rounded-lg px-3 py-1 text-white text-sm focus:outline-none focus:border-energy-400"
                />
              </div>

              <div class="flex items-center justify-between">
                <div>
                  <p class="text-sm font-semibold text-slate-300">Low Price Alerts</p>
                  <p class="text-xs text-slate-400">Notify when price drops below threshold</p>
                </div>
                <input 
                  v-model="settingsStore.settings.notifications.lowPrice"
                  type="checkbox"
                  class="w-5 h-5 rounded cursor-pointer"
                />
              </div>

              <div v-if="settingsStore.settings.notifications.lowPrice" class="pl-4 border-l-2 border-slate-700">
                <label class="block text-xs font-semibold text-slate-300 mb-2">Threshold (₴/kWh)</label>
                <input 
                  v-model.number="settingsStore.settings.notifications.lowPriceThreshold"
                  type="number"
                  min="0"
                  step="0.1"
                  class="w-full max-w-xs bg-slate-900 border border-slate-700 rounded-lg px-3 py-1 text-white text-sm focus:outline-none focus:border-energy-400"
                />
              </div>

              <div class="pt-4 space-y-3">
                <div class="flex items-center gap-3">
                  <input 
                    v-model="settingsStore.settings.notifications.modelComplete"
                    type="checkbox"
                    id="notif-model"
                    class="w-5 h-5 rounded cursor-pointer"
                  />
                  <label for="notif-model" class="text-sm text-slate-300 cursor-pointer">Notify when model training completes</label>
                </div>

                <div class="flex items-center gap-3">
                  <input 
                    v-model="settingsStore.settings.notifications.systemAlerts"
                    type="checkbox"
                    id="notif-system"
                    class="w-5 h-5 rounded cursor-pointer"
                  />
                  <label for="notif-system" class="text-sm text-slate-300 cursor-pointer">Enable system alerts</label>
                </div>
              </div>
            </div>

            <button 
              @click="saveNotificationSettings"
              :disabled="settingsStore.isSaving"
              class="mt-6 px-6 py-2 bg-energy-400 hover:bg-cyan-300 text-slate-950 font-semibold rounded-lg transition disabled:opacity-50"
            >
              {{ settingsStore.isSaving ? 'Saving...' : 'Save Changes' }}
            </button>
          </div>
        </div>

        <!-- Model Settings -->
        <div v-if="activeTab === 'model'" class="space-y-6">
          <div class="bg-slate-800 bg-opacity-40 border border-slate-700 rounded-lg p-6">
            <h2 class="text-xl font-bold text-white mb-6">Model & Training Configuration</h2>

            <div class="space-y-4">
              <div>
                <label class="block text-sm font-semibold text-slate-300 mb-2">Learning Rate</label>
                <input 
                  v-model.number="settingsStore.settings.model.learningRate"
                  type="number"
                  min="0"
                  step="0.0001"
                  class="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-energy-400"
                />
                <p class="text-xs text-slate-400 mt-1">Controls model training speed (smaller = slower but more stable)</p>
              </div>

              <div>
                <label class="block text-sm font-semibold text-slate-300 mb-2">Batch Size</label>
                <input 
                  v-model.number="settingsStore.settings.model.batchSize"
                  type="number"
                  min="1"
                  class="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-energy-400"
                />
                <p class="text-xs text-slate-400 mt-1">Number of samples per training iteration</p>
              </div>

              <div>
                <label class="block text-sm font-semibold text-slate-300 mb-2">Training Epochs</label>
                <input 
                  v-model.number="settingsStore.settings.model.epochs"
                  type="number"
                  min="1"
                  max="100"
                  class="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-energy-400"
                />
                <p class="text-xs text-slate-400 mt-1">Number of complete passes through training data</p>
              </div>
            </div>

            <div class="mt-6 pt-6 border-t border-slate-700 space-y-4">
              <button 
                @click="saveModelSettings"
                :disabled="settingsStore.isSaving"
                class="w-full px-6 py-2 bg-energy-400 hover:bg-cyan-300 text-slate-950 font-semibold rounded-lg transition disabled:opacity-50"
              >
                {{ settingsStore.isSaving ? 'Saving...' : 'Save Changes' }}
              </button>

              <button 
                @click="startModelRetraining"
                class="w-full px-6 py-2 bg-blue-600 hover:bg-blue-500 text-white font-semibold rounded-lg transition"
              >
                🚀 Retrain Model with New Settings
              </button>
            </div>
          </div>
        </div>

        <!-- Danger Zone -->
        <div class="bg-red-900 bg-opacity-20 border border-red-700 rounded-lg p-6">
          <h2 class="text-lg font-bold text-red-300 mb-4">⚠️ Danger Zone</h2>
          <p class="text-sm text-red-200 mb-4">Reset all settings to factory defaults. This cannot be undone.</p>
          <button 
            @click="resetSettings"
            class="px-6 py-2 bg-red-600 hover:bg-red-500 text-white font-semibold rounded-lg transition"
          >
            🔄 Reset to Defaults
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, watch } from 'vue'
import { useSettingsStore } from '~/stores/settingsStore'
import { useRetrainingStore } from '~/stores/retrainingStore'
import { useTenantContext } from '~/composables/useTenantContext'
import BatteryConfigPanel from '~/components/Battery/ConfigPanel.vue'
import GenerationSolarWindConfig from '~/components/Generation/SolarWindConfig.vue'
import BatteryPhysicsSimulator from '~/components/Battery/PhysicsSimulator.vue'
import ScenarioManager from '~/components/Scenario/Manager.vue'
import PreferencesOptimizationProfile from '~/components/Preferences/OptimizationProfile.vue'

const settingsStore = useSettingsStore()
const retrainingStore = useRetrainingStore()
const tenantContext = useTenantContext()
const route = useRoute()

const tenantOptions = computed(() => tenantContext.tenants.value)
const selectedTenantId = computed({
  get: () => tenantContext.currentTenantId.value,
  set: (tenantId: string) => tenantContext.setTenant(tenantId),
})

const usableCapacityEstimate = computed(() => {
  const capacity = Number(settingsStore.settings.battery.capacity || 0)
  const minReserve = Number(settingsStore.settings.battery.minSOC || 0) / 100
  return Math.max(0, capacity * (1 - minReserve)).toFixed(1)
})

const estimatedDailySpreadRevenue = computed(() => {
  const capacity = Number(settingsStore.settings.battery.capacity || 0)
  const maxDischarge = Number(settingsStore.settings.battery.maxDischargeRate || 0)
  const high = Number(settingsStore.settings.notifications.highPriceThreshold || 0)
  const low = Number(settingsStore.settings.notifications.lowPriceThreshold || 0)
  const spread = Math.max(0, high - low)
  const cycleEnergy = Math.min(capacity, maxDischarge * 4)
  return Math.round(cycleEnergy * spread * 0.85).toLocaleString()
})

const enabledNotificationCount = computed(() => {
  const alerts = settingsStore.settings.notifications
  return [alerts.highPrice, alerts.lowPrice, alerts.modelComplete, alerts.systemAlerts].filter(Boolean).length
})

const tabs = [
  { id: 'general', label: 'General', icon: '🌍' },
  { id: 'battery', label: 'Battery', icon: '🔋' },
  { id: 'generation', label: 'Generation', icon: '⚡' },
  { id: 'control', label: 'Control', icon: '🎮' },
  { id: 'scenarios', label: 'Scenarios', icon: '📋' },
  { id: 'preferences', label: 'Optimization', icon: '🎯' },
  { id: 'notifications', label: 'Notifications', icon: '🔔' },
  { id: 'model', label: 'Model', icon: '🤖' }
]

const tabIds = new Set(tabs.map((tab) => tab.id))
const initialTab = String(route.query.tab || 'general')
const activeTab = ref(tabIds.has(initialTab) ? initialTab : 'general')
const saveSuccess = ref(false)

const showSaveSuccess = () => {
  saveSuccess.value = true
  setTimeout(() => {
    saveSuccess.value = false
  }, 3000)
}

const saveGeneralSettings = async () => {
  const result = await settingsStore.updateGeneralSettings(settingsStore.settings.general)
  if (result.success) {
    showSaveSuccess()
  }
}

const saveBatterySettings = async () => {
  const result = await settingsStore.updateBatterySettings(settingsStore.settings.battery)
  if (result.success) {
    showSaveSuccess()
  }
}

const saveNotificationSettings = async () => {
  const result = await settingsStore.updateNotificationSettings(settingsStore.settings.notifications)
  if (result.success) {
    showSaveSuccess()
  }
}

const saveModelSettings = async () => {
  const result = await settingsStore.updateModelSettings(settingsStore.settings.model)
  if (result.success) {
    showSaveSuccess()
  }
}

const startModelRetraining = async () => {
  // Pass model settings to retraining
  const result = await retrainingStore.startRetraining({
    learningRate: settingsStore.settings.model.learningRate,
    batchSize: settingsStore.settings.model.batchSize,
    epochs: settingsStore.settings.model.epochs
  })

  if (result.success) {
    // Could navigate to dashboard or show success
    showSaveSuccess()
  }
}

const resetSettings = async () => {
  if (confirm('Are you sure? This will reset all settings to defaults.')) {
    await settingsStore.resetToDefaults()
    showSaveSuccess()
  }
}

onMounted(async () => {
  await tenantContext.loadTenants()
  await settingsStore.loadSettings()
})

watch(
  () => tenantContext.currentTenantId.value,
  async () => {
    await settingsStore.loadSettings()
  },
)

watch(
  () => route.query.tab,
  (value) => {
    const tab = String(value || '')
    if (tabIds.has(tab)) {
      activeTab.value = tab
    }
  },
)
</script>
