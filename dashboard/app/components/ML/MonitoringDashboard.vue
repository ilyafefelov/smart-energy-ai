<!-- MLOps Monitoring Dashboard Component -->
<template>
  <div class="space-y-6">
    <!-- Header with Overall Status -->
    <UCard>
      <template #header>
        <div class="flex items-center justify-between">
          <div class="flex items-center space-x-3">
            <UIcon name="i-heroicons-chart-bar-square" class="w-8 h-8 text-emerald-500" />
            <h1 class="text-2xl font-bold text-gray-900 dark:text-white">
              📊 MLOps Dashboard
            </h1>
          </div>
          <div class="flex items-center space-x-3">
            <UBadge 
              :color="getHealthColor(dashboardData.system_health?.overall_status)" 
              :label="dashboardData.system_health?.overall_status?.toUpperCase() || 'LOADING'"
              size="lg"
            />
            <UButton 
              @click="refreshDashboard" 
              :loading="loading"
              icon="i-heroicons-arrow-path"
              size="sm"
              variant="ghost"
            >
              Refresh
            </UButton>
          </div>
        </div>
      </template>
      
      <!-- System Health Overview -->
      <div class="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div class="text-center p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
          <div class="text-3xl font-bold text-blue-600 mb-2">
            {{ dashboardData.performance_metrics?.mape?.toFixed(1) || '--' }}%
          </div>
          <p class="text-sm text-gray-600 dark:text-gray-400">Model Accuracy (MAPE)</p>
          <p class="text-xs text-gray-500 mt-1">
            Target: &lt; 10%
          </p>
        </div>
        
        <div class="text-center p-4 bg-green-50 dark:bg-green-900/20 rounded-lg">
          <div class="text-3xl font-bold text-green-600 mb-2">
            {{ dashboardData.performance_metrics?.latency_p95_ms?.toFixed(0) || '--' }}ms
          </div>
          <p class="text-sm text-gray-600 dark:text-gray-400">Prediction Latency</p>
          <p class="text-xs text-gray-500 mt-1">
            P95 Response Time
          </p>
        </div>
        
        <div class="text-center p-4 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
          <div class="text-3xl font-bold text-purple-600 mb-2">
            {{ dashboardData.performance_metrics?.prediction_count || 0 }}
          </div>
          <p class="text-sm text-gray-600 dark:text-gray-400">Predictions Today</p>
          <p class="text-xs text-gray-500 mt-1">
            Real-time Serving
          </p>
        </div>
        
        <div class="text-center p-4 bg-amber-50 dark:bg-amber-900/20 rounded-lg">
          <div class="text-3xl font-bold text-amber-600 mb-2">
            {{ dashboardData.alerts?.total_active || 0 }}
          </div>
          <p class="text-sm text-gray-600 dark:text-gray-400">Active Alerts</p>
          <p class="text-xs text-gray-500 mt-1">
            {{ dashboardData.alerts?.critical_count || 0 }} Critical
          </p>
        </div>
      </div>
    </UCard>

    <UCard>
      <template #header>
        <div class="flex items-center justify-between">
          <div class="flex items-center space-x-3">
            <UIcon name="i-heroicons-shield-check" class="w-6 h-6 text-cyan-500" />
            <h2 class="text-xl font-semibold">🛡️ Dagster Schedule Contract</h2>
          </div>
          <UBadge
            :color="getDagsterContractColor(dashboardData.dagster_schedule_contract?.summary?.overall_status)"
            :label="formatContractStatus(dashboardData.dagster_schedule_contract?.summary?.overall_status)"
            size="sm"
          />
        </div>
      </template>

      <div class="grid grid-cols-1 lg:grid-cols-4 gap-4 mb-6">
        <div class="rounded-lg border border-cyan-200 dark:border-cyan-900 bg-cyan-50 dark:bg-cyan-950/20 p-4">
          <p class="text-xs uppercase tracking-[0.24em] text-cyan-700 dark:text-cyan-300">Snapshot</p>
          <p class="mt-2 text-2xl font-semibold text-cyan-900 dark:text-cyan-100">
            {{ dashboardData.dagster_schedule_contract?.snapshot_is_fresh ? 'Fresh' : 'Fallback' }}
          </p>
          <p class="mt-1 text-xs text-cyan-800/70 dark:text-cyan-200/70">
            {{ dagsterSnapshotLabel }}
          </p>
        </div>

        <div class="rounded-lg border border-emerald-200 dark:border-emerald-900 bg-emerald-50 dark:bg-emerald-950/20 p-4">
          <p class="text-xs uppercase tracking-[0.24em] text-emerald-700 dark:text-emerald-300">Passing</p>
          <p class="mt-2 text-2xl font-semibold text-emerald-900 dark:text-emerald-100">
            {{ dashboardData.dagster_schedule_contract?.summary?.passed_checks || 0 }}
          </p>
          <p class="mt-1 text-xs text-emerald-800/70 dark:text-emerald-200/70">Checks green across both schedule assets</p>
        </div>

        <div class="rounded-lg border border-red-200 dark:border-red-900 bg-red-50 dark:bg-red-950/20 p-4">
          <p class="text-xs uppercase tracking-[0.24em] text-red-700 dark:text-red-300">Failing</p>
          <p class="mt-2 text-2xl font-semibold text-red-900 dark:text-red-100">
            {{ dashboardData.dagster_schedule_contract?.summary?.failed_checks || 0 }}
          </p>
          <p class="mt-1 text-xs text-red-800/70 dark:text-red-200/70">Contract violations that invalidate live schedule trust</p>
        </div>

        <div class="rounded-lg border border-amber-200 dark:border-amber-900 bg-amber-50 dark:bg-amber-950/20 p-4">
          <p class="text-xs uppercase tracking-[0.24em] text-amber-700 dark:text-amber-300">Unevaluated</p>
          <p class="mt-2 text-2xl font-semibold text-amber-900 dark:text-amber-100">
            {{ dagsterUnevaluatedCount }}
          </p>
          <p class="mt-1 text-xs text-amber-800/70 dark:text-amber-200/70">Checks that have not produced a terminal result yet</p>
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div
          v-for="asset in dashboardData.dagster_schedule_contract?.assets || []"
          :key="asset.asset_name"
          class="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-950/40 p-4"
        >
          <div class="flex items-center justify-between mb-4">
            <div>
              <p class="text-xs uppercase tracking-[0.2em] text-gray-500">Asset</p>
              <h3 class="text-lg font-semibold">{{ asset.asset_name }}</h3>
            </div>
            <UBadge
              :color="getDagsterContractColor(asset.summary?.overall_status)"
              :label="formatContractStatus(asset.summary?.overall_status)"
              size="sm"
            />
          </div>

          <div class="grid grid-cols-3 gap-3 mb-4 text-center">
            <div class="rounded-lg bg-gray-50 dark:bg-gray-900 p-3">
              <p class="text-xs text-gray-500">Pass</p>
              <p class="text-lg font-semibold text-emerald-600">{{ asset.summary?.passed_checks || 0 }}</p>
            </div>
            <div class="rounded-lg bg-gray-50 dark:bg-gray-900 p-3">
              <p class="text-xs text-gray-500">Fail/Warn</p>
              <p class="text-lg font-semibold text-red-600">{{ (asset.summary?.failed_checks || 0) + (asset.summary?.warning_checks || 0) }}</p>
            </div>
            <div class="rounded-lg bg-gray-50 dark:bg-gray-900 p-3">
              <p class="text-xs text-gray-500">Not Run</p>
              <p class="text-lg font-semibold text-amber-600">{{ (asset.summary?.not_run_checks || 0) + (asset.summary?.planned_checks || 0) }}</p>
            </div>
          </div>

          <div class="space-y-2">
            <div
              v-for="check in asset.checks || []"
              :key="`${asset.asset_name}-${check.check_name}`"
              class="flex items-start justify-between gap-4 rounded-lg border border-gray-200 dark:border-gray-800 px-3 py-2"
            >
              <div>
                <p class="font-medium text-sm">{{ check.check_name }}</p>
                <p class="text-xs text-gray-500">
                  {{ check.description || 'Latest Dagster asset-check evaluation for schedule contract enforcement.' }}
                </p>
              </div>
              <div class="text-right shrink-0">
                <UBadge :color="getDagsterCheckBadgeColor(check.status)" :label="check.status.toUpperCase()" size="xs" />
                <p class="mt-1 text-[11px] text-gray-500">{{ formatTime(check.timestamp) }}</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <UAlert
        v-if="(dashboardData.dagster_schedule_contract?.summary?.failing_check_names || []).length > 0"
        class="mt-6"
        icon="i-heroicons-exclamation-triangle"
        color="red"
        title="Schedule contract failures detected"
        :description="`Failing checks: ${(dashboardData.dagster_schedule_contract?.summary?.failing_check_names || []).join(', ')}`"
      />

      <UAlert
        v-else-if="dagsterUnevaluatedCount > 0"
        class="mt-6"
        icon="i-heroicons-clock"
        color="amber"
        title="Schedule checks have not been fully evaluated yet"
        :description="`Run the Dagster optimization_schedule_contract_checks job to populate ${(dashboardData.dagster_schedule_contract?.summary?.unevaluated_check_names || []).length} unevaluated checks.`"
      />
    </UCard>

    <!-- Model Deployment Status -->
    <UCard>
      <template #header>
        <div class="flex items-center space-x-3">
          <UIcon name="i-heroicons-server-stack" class="w-6 h-6 text-blue-500" />
          <h2 class="text-xl font-semibold">🚀 Model Deployment Status</h2>
        </div>
      </template>
      
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <!-- Production Model -->
        <div class="border border-green-200 dark:border-green-800 rounded-lg p-4 bg-green-50 dark:bg-green-900/10">
          <div class="flex items-center justify-between mb-3">
            <h3 class="font-semibold text-green-800 dark:text-green-200">Production Model</h3>
            <UBadge color="green" label="LIVE" />
          </div>
          
          <div v-if="dashboardData.model_status?.production" class="space-y-2">
            <p class="text-sm">
              <span class="font-medium">Version:</span> 
              {{ dashboardData.model_status.production.version }}
            </p>
            <p class="text-sm">
              <span class="font-medium">Deployed:</span> 
              {{ formatTime(dashboardData.model_status.production.created_at) }}
            </p>
            <p class="text-sm">
              <span class="font-medium">Performance:</span> 
              {{ dashboardData.model_status.production.performance_mape?.toFixed(1) }}% MAPE
            </p>
            <div class="flex items-center space-x-2">
              <div :class="`w-2 h-2 rounded-full ${getHealthDotColor(dashboardData.model_status.production.health_status)}`"></div>
              <span class="text-xs text-gray-600 dark:text-gray-400">
                {{ dashboardData.model_status.production.health_status || 'unknown' }}
              </span>
            </div>
          </div>
          
          <div v-else class="text-center py-4">
            <UIcon name="i-heroicons-exclamation-triangle" class="w-8 h-8 text-amber-500 mx-auto mb-2" />
            <p class="text-sm text-gray-600">No production model deployed</p>
          </div>
        </div>
        
        <!-- Staging Model -->
        <div class="border border-blue-200 dark:border-blue-800 rounded-lg p-4 bg-blue-50 dark:bg-blue-900/10">
          <div class="flex items-center justify-between mb-3">
            <h3 class="font-semibold text-blue-800 dark:text-blue-200">Staging Model</h3>
            <UBadge color="blue" label="STAGING" />
          </div>
          
          <div v-if="dashboardData.model_status?.staging" class="space-y-2">
            <p class="text-sm">
              <span class="font-medium">Version:</span> 
              {{ dashboardData.model_status.staging.version }}
            </p>
            <p class="text-sm">
              <span class="font-medium">Created:</span> 
              {{ formatTime(dashboardData.model_status.staging.created_at) }}
            </p>
            <p class="text-sm">
              <span class="font-medium">Performance:</span> 
              {{ dashboardData.model_status.staging.performance_mape?.toFixed(1) }}% MAPE
            </p>
            <div class="flex items-center space-x-2">
              <div :class="`w-2 h-2 rounded-full ${getHealthDotColor(dashboardData.model_status.staging.health_status)}`"></div>
              <span class="text-xs text-gray-600 dark:text-gray-400">
                {{ dashboardData.model_status.staging.health_status || 'unknown' }}
              </span>
            </div>
            
            <div class="mt-3">
              <UButton 
                @click="promoteToProduction" 
                color="blue" 
                size="xs"
                :loading="promoting"
              >
                Promote to Production
              </UButton>
            </div>
          </div>
          
          <div v-else class="text-center py-4">
            <UIcon name="i-heroicons-beaker" class="w-8 h-8 text-gray-400 mx-auto mb-2" />
            <p class="text-sm text-gray-600">No staging model available</p>
          </div>
        </div>
      </div>
    </UCard>

    <!-- Performance Monitoring -->
    <UCard>
      <template #header>
        <div class="flex items-center justify-between">
          <div class="flex items-center space-x-3">
            <UIcon name="i-heroicons-chart-line" class="w-6 h-6 text-emerald-500" />
            <h2 class="text-xl font-semibold">📈 Performance Monitoring</h2>
          </div>
        </div>
      </template>
      
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <!-- Key Metrics -->
        <div>
          <h3 class="font-semibold mb-4">Key Performance Indicators</h3>
          <div class="space-y-4">
            <div class="flex justify-between items-center p-3 bg-gray-50 dark:bg-gray-800 rounded">
              <div>
                <span class="font-medium">Model Accuracy (MAPE)</span>
                <p class="text-xs text-gray-500">Lower is better • Target: &lt;10%</p>
              </div>
              <div class="text-right">
                <span class="text-xl font-bold" :class="getMapeColor(dashboardData.performance_metrics?.mape)">
                  {{ dashboardData.performance_metrics?.mape?.toFixed(1) || '--' }}%
                </span>
              </div>
            </div>
            
            <div class="flex justify-between items-center p-3 bg-gray-50 dark:bg-gray-800 rounded">
              <div>
                <span class="font-medium">R² Score</span>
                <p class="text-xs text-gray-500">Model fit quality • Target: >0.85</p>
              </div>
              <div class="text-right">
                <span class="text-xl font-bold text-blue-600">
                  {{ dashboardData.performance_metrics?.r2_score?.toFixed(3) || '--' }}
                </span>
              </div>
            </div>
            
            <div class="flex justify-between items-center p-3 bg-gray-50 dark:bg-gray-800 rounded">
              <div>
                <span class="font-medium">Error Rate</span>
                <p class="text-xs text-gray-500">Failed predictions • Target: &lt;2%</p>
              </div>
              <div class="text-right">
                <span class="text-xl font-bold" :class="getErrorRateColor(dashboardData.performance_metrics?.error_rate)">
                  {{ dashboardData.performance_metrics?.error_rate?.toFixed(1) || '--' }}%
                </span>
              </div>
            </div>
          </div>
        </div>
        
        <!-- Feature Importance -->
        <div>
          <h3 class="font-semibold mb-4">Feature Importance</h3>
          <div class="space-y-3">
            <div 
              v-for="(importance, feature) in dashboardData.feature_importance"
              :key="feature"
              class="flex items-center space-x-3"
            >
              <span class="text-sm font-medium min-w-[120px] text-right">{{ formatFeatureName(feature) }}</span>
              <div class="flex-1 bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                <div 
                  class="bg-emerald-500 h-2 rounded-full transition-all duration-500"
                  :style="{ width: `${importance * 100}%` }"
                ></div>
              </div>
              <span class="text-xs text-gray-500 min-w-[40px]">{{ (importance * 100).toFixed(1) }}%</span>
            </div>
          </div>
        </div>
      </div>
    </UCard>

    <!-- Data Drift & Alerts -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- Data Drift Detection -->
      <UCard>
        <template #header>
          <div class="flex items-center space-x-3">
            <UIcon name="i-heroicons-exclamation-triangle" class="w-6 h-6 text-amber-500" />
            <h2 class="text-xl font-semibold">⚠️ Data Drift Detection</h2>
          </div>
        </template>
        
        <div class="space-y-4">
          <div class="flex items-center justify-between">
            <span class="font-medium">Overall Drift Score</span>
            <div class="text-right">
              <span class="text-2xl font-bold" :class="getDriftColor(dashboardData.drift_status?.drift_score)">
                {{ (dashboardData.drift_status?.drift_score * 100)?.toFixed(1) || '--' }}%
              </span>
              <p class="text-xs text-gray-500">
                {{ dashboardData.drift_status?.status || 'unknown' }}
              </p>
            </div>
          </div>
          
          <UAlert 
            v-if="dashboardData.drift_status?.drift_detected"
            icon="i-heroicons-exclamation-triangle"
            color="amber"
            title="Data Drift Detected"
            description="Input data distribution has changed. Consider model retraining."
          />
          
          <div v-if="dashboardData.drift_status?.feature_drifts">
            <h4 class="font-medium mb-2">Per-Feature Drift</h4>
            <div class="space-y-2">
              <div 
                v-for="(drift, feature) in dashboardData.drift_status.feature_drifts"
                :key="feature"
                class="flex justify-between items-center text-sm"
              >
                <span>{{ formatFeatureName(feature) }}</span>
                <span :class="getDriftColor(drift)">{{ (drift * 100).toFixed(1) }}%</span>
              </div>
            </div>
          </div>
        </div>
      </UCard>
      
      <!-- Active Alerts -->
      <UCard>
        <template #header>
          <div class="flex items-center space-x-3">
            <UIcon name="i-heroicons-bell" class="w-6 h-6 text-red-500" />
            <h2 class="text-xl font-semibold">🔔 Active Alerts</h2>
          </div>
        </template>
        
        <div v-if="dashboardData.alerts?.latest_alerts?.length > 0" class="space-y-3">
          <div 
            v-for="(alert, index) in dashboardData.alerts.latest_alerts"
            :key="index"
            class="border border-gray-200 dark:border-gray-700 rounded-lg p-3"
          >
            <div class="flex items-start justify-between mb-2">
              <UBadge 
                :color="alert.severity === 'critical' ? 'red' : 'amber'" 
                :label="alert.severity.toUpperCase()" 
                size="sm"
              />
              <span class="text-xs text-gray-500">
                {{ formatTime(alert.timestamp) }}
              </span>
            </div>
            <p class="text-sm text-gray-700 dark:text-gray-300">
              {{ alert.message }}
            </p>
          </div>
        </div>
        
        <div v-else class="text-center py-8">
          <UIcon name="i-heroicons-check-circle" class="w-16 h-16 mx-auto mb-4 text-green-500" />
          <p class="text-gray-500">No active alerts</p>
          <p class="text-xs text-gray-400 mt-1">System operating normally</p>
        </div>
      </UCard>
    </div>

    <!-- Retraining Status -->
    <UCard>
      <template #header>
        <div class="flex items-center justify-between">
          <div class="flex items-center space-x-3">
            <UIcon name="i-heroicons-arrow-path" class="w-6 h-6 text-purple-500" />
            <h2 class="text-xl font-semibold">🔄 Automated Retraining</h2>
          </div>
          <UButton 
            @click="triggerRetraining" 
            :loading="retraining"
            color="purple"
            icon="i-heroicons-play"
            size="sm"
          >
            Trigger Retraining
          </UButton>
        </div>
      </template>
      
      <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div class="text-center p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
          <div class="text-2xl font-bold mb-2" :class="getRetrainingColor(dashboardData.retraining_status?.should_retrain)">
            {{ dashboardData.retraining_status?.should_retrain ? 'NEEDED' : 'NOT NEEDED' }}
          </div>
          <p class="text-sm text-gray-600 dark:text-gray-400">Retraining Status</p>
        </div>
        
        <div class="text-center p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
          <div class="text-2xl font-bold text-blue-600 mb-2">
            {{ Math.floor(dashboardData.retraining_status?.last_training_age_hours || 0) }}h
          </div>
          <p class="text-sm text-gray-600 dark:text-gray-400">Since Last Training</p>
        </div>
        
        <div class="text-center p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
          <div class="text-2xl font-bold text-gray-600 mb-2">
            {{ formatTime(dashboardData.retraining_status?.next_check) }}
          </div>
          <p class="text-sm text-gray-600 dark:text-gray-400">Next Check</p>
        </div>
      </div>
      
      <div v-if="dashboardData.retraining_status?.reasons?.length > 0" class="mt-4">
        <h4 class="font-medium mb-2">Retraining Triggers:</h4>
        <ul class="list-disc list-inside space-y-1 text-sm text-gray-600">
          <li v-for="reason in dashboardData.retraining_status.reasons" :key="reason">
            {{ reason }}
          </li>
        </ul>
      </div>
    </UCard>

    <!-- Energy Market Context -->
    <UCard>
      <template #header>
        <div class="flex items-center space-x-3">
          <UIcon name="i-heroicons-bolt" class="w-6 h-6 text-yellow-500" />
          <h2 class="text-xl font-semibold">⚡ Ukraine Energy Market Context</h2>
        </div>
      </template>
      
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
        <div>
          <div class="text-xl font-bold text-yellow-600">
            {{ Math.floor(dashboardData.energy_market?.current_price_uah_mwh || 0) }}
          </div>
          <p class="text-xs text-gray-500">UAH/MWh</p>
        </div>
        <div>
          <div class="text-xl font-bold" :class="dashboardData.energy_market?.peak_hours ? 'text-red-600' : 'text-green-600'">
            {{ dashboardData.energy_market?.peak_hours ? 'PEAK' : 'OFF-PEAK' }}
          </div>
          <p class="text-xs text-gray-500">Pricing</p>
        </div>
        <div>
          <div class="text-xl font-bold text-emerald-600">
            {{ dashboardData.energy_market?.renewable_share_percent?.toFixed(1) || 0 }}%
          </div>
          <p class="text-xs text-gray-500">Renewables</p>
        </div>
        <div>
          <div class="text-xl font-bold" :class="dashboardData.energy_market?.grid_stability === 'stable' ? 'text-blue-600' : 'text-red-600'">
            {{ dashboardData.energy_market?.grid_stability?.toUpperCase() || 'UNKNOWN' }}
          </div>
          <p class="text-xs text-gray-500">Grid Status</p>
        </div>
      </div>
    </UCard>
  </div>
</template>

<script setup>
// Page metadata
definePageMeta({
  title: 'MLOps Dashboard',
  description: 'ML model monitoring, performance tracking, and system health'
})

// Imports
import { ref, onMounted, onUnmounted } from 'vue'

// Toast notifications
const toast = typeof useToast === 'function'
  ? useToast()
  : { add: () => undefined }

// Reactive state
const dashboardData = ref({})
const loading = ref(false)
const promoting = ref(false)
const retraining = ref(false)

// Auto-refresh setup
let refreshInterval = null

// Methods
const refreshDashboard = async () => {
  loading.value = true
  try {
    const data = await $fetch('/api/ml/monitoring')
    dashboardData.value = data
    
    console.log('MLOps dashboard refreshed:', data.timestamp)
  } catch (error) {
    console.error('Failed to refresh MLOps dashboard:', error)
    toast.add({
      title: 'Dashboard Refresh Failed',
      description: error.message || 'Could not fetch monitoring data',
      color: 'red'
    })
  } finally {
    loading.value = false
  }
}

const promoteToProduction = async () => {
  promoting.value = true
  try {
    // Simulate model promotion
    await new Promise(resolve => setTimeout(resolve, 2000))
    
    toast.add({
      title: 'Model Promoted',
      description: 'Staging model successfully promoted to production',
      color: 'green'
    })
    
    await refreshDashboard()
  } catch (error) {
    toast.add({
      title: 'Promotion Failed',
      description: error.message || 'Failed to promote model',
      color: 'red'
    })
  } finally {
    promoting.value = false
  }
}

const triggerRetraining = async () => {
  retraining.value = true
  try {
    // Simulate retraining trigger
    await new Promise(resolve => setTimeout(resolve, 3000))
    
    toast.add({
      title: 'Retraining Initiated',
      description: 'Model retraining started. Estimated completion: 15 minutes',
      color: 'blue'
    })
    
    await refreshDashboard()
  } catch (error) {
    toast.add({
      title: 'Retraining Failed',
      description: error.message || 'Failed to trigger retraining',
      color: 'red'
    })
  } finally {
    retraining.value = false
  }
}

// Utility functions
const formatTime = (timestamp) => {
  if (!timestamp) return '--'
  try {
    return new Date(timestamp).toLocaleString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      day: '2-digit',
      month: '2-digit'
    })
  } catch {
    return '--'
  }
}

const formatFeatureName = (feature) => {
  return feature.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
}

const getHealthColor = (status) => {
  const colors = {
    'healthy': 'green',
    'degraded': 'amber',
    'unhealthy': 'red'
  }
  return colors[status] || 'gray'
}

const getHealthDotColor = (status) => {
  const colors = {
    'healthy': 'bg-green-500',
    'degraded': 'bg-amber-500',
    'unhealthy': 'bg-red-500'
  }
  return colors[status] || 'bg-gray-500'
}

const getMapeColor = (mape) => {
  if (!mape) return 'text-gray-500'
  if (mape < 8) return 'text-green-600'
  if (mape < 12) return 'text-amber-600'
  return 'text-red-600'
}

const getErrorRateColor = (rate) => {
  if (!rate) return 'text-gray-500'
  if (rate < 2) return 'text-green-600'
  if (rate < 5) return 'text-amber-600'
  return 'text-red-600'
}

const getDriftColor = (score) => {
  if (!score) return 'text-gray-500'
  if (score < 0.1) return 'text-green-600'
  if (score < 0.2) return 'text-amber-600'
  return 'text-red-600'
}

const getRetrainingColor = (needed) => {
  return needed ? 'text-red-600' : 'text-green-600'
}

const formatContractStatus = (status) => {
  return String(status || 'unknown').replace(/_/g, ' ').toUpperCase()
}

const getDagsterContractColor = (status) => {
  const colors = {
    healthy: 'green',
    warning: 'amber',
    degraded: 'red',
    unknown: 'gray',
    not_applicable: 'gray',
  }
  return colors[String(status || 'unknown').toLowerCase()] || 'gray'
}

const getDagsterCheckBadgeColor = (status) => {
  const colors = {
    passed: 'green',
    warning: 'amber',
    failed: 'red',
    not_run: 'gray',
    planned: 'blue',
  }
  return colors[String(status || 'not_run').toLowerCase()] || 'gray'
}

const dagsterUnevaluatedCount = computed(() => {
  const summary = dashboardData.value.dagster_schedule_contract?.summary || {}
  return Number(summary.not_run_checks || 0) + Number(summary.planned_checks || 0)
})

const dagsterSnapshotLabel = computed(() => {
  const contract = dashboardData.value.dagster_schedule_contract || {}
  if (contract.snapshot_is_fresh === true) {
    const age = contract.snapshot_age_minutes
    return age == null ? 'Dagster schedule snapshot within SLA' : `${Number(age).toFixed(1)} minutes old`
  }
  if (contract.snapshot_is_fresh === false) {
    const age = contract.snapshot_age_minutes
    return age == null ? 'Fallback path active because snapshot freshness is unknown' : `Fallback active, snapshot ${Number(age).toFixed(1)} minutes old`
  }
  return 'Snapshot freshness not yet available'
})

// Lifecycle
onMounted(async () => {
  // Initial data load
  await refreshDashboard()
  
  // Set up auto-refresh every 30 seconds
  refreshInterval = setInterval(async () => {
    await refreshDashboard()
  }, 30000)
  
  console.log('MLOps dashboard mounted, auto-refresh enabled')
})

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
  console.log('MLOps dashboard unmounted, auto-refresh disabled')
})
</script>

<style scoped>
/* Component-specific styles */
.fade-enter-active, .fade-leave-active {
  transition: opacity 0.3s;
}
.fade-enter, .fade-leave-to {
  opacity: 0;
}
</style>