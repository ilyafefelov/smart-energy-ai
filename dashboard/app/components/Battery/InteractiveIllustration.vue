<template>
  <div class="relative overflow-hidden rounded-xl border border-slate-700 bg-slate-900/60 p-5">
    <div class="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_right,_rgba(34,211,238,0.15),_transparent_45%)]"></div>

    <div class="relative flex flex-wrap items-start justify-between gap-3">
      <div>
        <h3 class="text-lg font-bold text-white">{{ title }}</h3>
        <p class="text-xs text-slate-400">{{ subtitle }}</p>
      </div>
      <div class="flex items-center gap-2">
        <span class="rounded-full border border-slate-600 px-3 py-1 text-xs" :class="batteryPhysicsStore.powerStatus.color">
          {{ batteryPhysicsStore.powerStatus.icon }} {{ batteryPhysicsStore.powerStatus.text }}
        </span>
        <button
          class="rounded-lg px-3 py-1 text-xs font-semibold transition"
          :class="batteryPhysicsStore.state.manualMode ? 'bg-red-600 text-white hover:bg-red-500' : 'bg-emerald-600 text-white hover:bg-emerald-500'"
          @click="toggleMode"
        >
          {{ batteryPhysicsStore.state.manualMode ? 'Manual' : 'Auto' }}
        </button>
      </div>
    </div>

    <div class="relative mt-5 grid grid-cols-1 gap-5 lg:grid-cols-2">
      <div class="rounded-xl border border-slate-700 bg-slate-950/70 p-4">
        <div class="mb-3 flex items-center justify-center">
          <span
            class="rounded-full border px-3 py-1 text-xs font-semibold tracking-wide"
            :class="operationBadgeClass"
          >
            {{ operationStatus.icon }} {{ operationStatus.label }}
          </span>
        </div>

        <div class="mx-auto flex w-full max-w-xs items-end justify-center gap-4">
          <div class="relative h-56 w-28 rounded-2xl border-4 border-slate-600 bg-slate-950 p-1">
            <div class="absolute -top-3 left-1/2 h-2 w-10 -translate-x-1/2 rounded-t-lg bg-slate-500"></div>
            <div class="relative h-full w-full overflow-hidden rounded-xl bg-slate-900">
              <div class="absolute inset-x-0 bottom-0 transition-all duration-700" :style="batteryFillStyle"></div>
              <div
                v-if="batteryPhysicsStore.state.isCharging"
                class="absolute inset-x-0 bottom-0 h-10 animate-pulse bg-gradient-to-t from-cyan-300/80 to-transparent"
              ></div>
              <div
                v-if="batteryPhysicsStore.state.isDischarging"
                class="absolute inset-x-0 top-0 h-10 animate-pulse bg-gradient-to-b from-amber-300/80 to-transparent"
              ></div>
            </div>
            <div class="absolute inset-0 flex items-center justify-center text-2xl font-black text-white drop-shadow-lg">
              {{ Math.round(batteryPhysicsStore.state.socPercentage) }}%
            </div>

            <div
              v-if="batteryPhysicsStore.state.isCharging"
              class="absolute -right-8 top-1/2 -translate-y-1/2 animate-bounce text-xl text-emerald-300"
              title="Charging"
            >
              ↑
            </div>
            <div
              v-else-if="batteryPhysicsStore.state.isDischarging"
              class="absolute -right-8 top-1/2 -translate-y-1/2 animate-bounce text-xl text-amber-300"
              title="Discharging"
            >
              ↓
            </div>
            <div
              v-else
              class="absolute -right-8 top-1/2 -translate-y-1/2 text-xl text-slate-400"
              title="Idle"
            >
              •
            </div>
          </div>

          <div class="flex-1 space-y-3">
            <div class="rounded-lg bg-slate-800/80 px-3 py-2">
              <p class="text-[11px] uppercase tracking-wide text-slate-400">Power Flow</p>
              <p class="text-lg font-bold" :class="powerFlowColor">
                {{ signedPower }} kW
              </p>
            </div>
            <div class="rounded-lg bg-slate-800/80 px-3 py-2">
              <p class="text-[11px] uppercase tracking-wide text-slate-400">Temperature</p>
              <p class="text-lg font-bold" :class="temperatureColor">{{ batteryPhysicsStore.state.temperature.toFixed(1) }}°C</p>
            </div>
            <div class="rounded-lg bg-slate-800/80 px-3 py-2">
              <p class="text-[11px] uppercase tracking-wide text-slate-400">Health</p>
              <p class="text-lg font-bold" :class="batteryPhysicsStore.healthStatus.color">{{ batteryPhysicsStore.state.health }}%</p>
            </div>
          </div>
        </div>
      </div>

      <div class="rounded-xl border border-slate-700 bg-slate-950/70 p-4">
        <div class="mb-2 flex items-center justify-between text-xs text-slate-400">
          <span>Discharge</span>
          <span>Target {{ commandText }}</span>
          <span>Charge</span>
        </div>
        <input
          v-model.number="targetPower"
          type="range"
          :min="-batteryPhysicsStore.state.maxDischargePower"
          :max="batteryPhysicsStore.state.maxChargePower"
          step="0.1"
          class="h-2 w-full cursor-pointer appearance-none rounded-lg bg-slate-700"
          :disabled="!batteryPhysicsStore.state.manualMode || isBusy"
        />

        <div class="mt-3 grid grid-cols-2 gap-2 text-sm">
          <button
            class="rounded-lg bg-cyan-600 px-3 py-2 font-semibold text-white transition hover:bg-cyan-500 disabled:cursor-not-allowed disabled:opacity-40"
            :disabled="!batteryPhysicsStore.state.manualMode || isBusy"
            @click="applyCommand"
          >
            Apply Command
          </button>
          <button
            class="rounded-lg bg-slate-700 px-3 py-2 font-semibold text-slate-100 transition hover:bg-slate-600 disabled:cursor-not-allowed disabled:opacity-40"
            :disabled="isBusy"
            @click="setIdle"
          >
            Hold
          </button>
          <button
            class="rounded-lg bg-emerald-700 px-3 py-2 font-semibold text-white transition hover:bg-emerald-600 disabled:cursor-not-allowed disabled:opacity-40"
            :disabled="!batteryPhysicsStore.canCharge || isBusy"
            @click="quickCharge"
          >
            Quick Charge
          </button>
          <button
            class="rounded-lg bg-amber-700 px-3 py-2 font-semibold text-white transition hover:bg-amber-600 disabled:cursor-not-allowed disabled:opacity-40"
            :disabled="!batteryPhysicsStore.canDischarge || isBusy"
            @click="quickDischarge"
          >
            Quick Discharge
          </button>
        </div>

        <div class="mt-4 rounded-lg border border-slate-700 bg-slate-900/70 p-3">
          <p class="text-[11px] uppercase tracking-wide text-slate-400">Control Semantics</p>
          <div class="mt-2 space-y-1 text-xs text-slate-300">
            <p>`Apply Command` sends the slider target as manual battery power.</p>
            <p>`Quick Charge` = +80% of max charge power ({{ quickChargeFormula }}).</p>
            <p>`Quick Discharge` = -80% of max discharge power ({{ quickDischargeFormula }}).</p>
            <p>`Hold` sets battery command to 0 kW.</p>
          </div>
        </div>

        <div class="mt-3 rounded-lg border border-slate-700 bg-slate-900/70 p-3">
          <div class="flex items-center justify-between gap-2">
            <p class="text-[11px] uppercase tracking-wide text-slate-400">Auto Intelligence</p>
            <span class="rounded-full border px-2 py-0.5 text-[10px]" :class="autoSourceBadgeClass">{{ autoSourceLabel }}</span>
          </div>
          <div class="mt-2 space-y-1 text-xs text-slate-300">
            <p>{{ autoIntelligenceSummary }}</p>
            <p>Requested: <span class="font-semibold text-slate-100">{{ requestedCommandLabel }}</span> | Active: <span class="font-semibold text-slate-100">{{ activeCommandLabel }}</span></p>
            <p v-if="batteryPhysicsStore.state.command_reason">Reason: <span class="text-slate-100">{{ batteryPhysicsStore.state.command_reason }}</span></p>
            <p v-if="batteryPhysicsStore.state.control_fallback_reason_code && batteryPhysicsStore.state.control_fallback_reason_code !== 'none'">
              Fallback code: <span class="text-amber-300">{{ batteryPhysicsStore.state.control_fallback_reason_code }}</span>
            </p>
          </div>
        </div>

        <div class="mt-3 rounded-lg border border-slate-700 bg-slate-900/70 p-3">
          <div class="flex items-center justify-between gap-2">
            <p class="text-[11px] uppercase tracking-wide text-slate-400">Strategy and Scenario</p>
            <span class="rounded-full border border-teal-500/60 bg-teal-500/10 px-2 py-0.5 text-[10px] text-teal-200">
              {{ strategyLabel }}
            </span>
          </div>
          <div class="mt-2 space-y-1 text-xs text-slate-300">
            <p>Load Profile: <span class="font-semibold text-slate-100">{{ loadProfileLabel }}</span></p>
            <p v-if="strategyWeightSummary">Weights: <span class="text-slate-100">{{ strategyWeightSummary }}</span></p>
            <p v-else>Live strategy weighting is unavailable for the current sample.</p>
          </div>
        </div>

        <div class="mt-3 rounded-lg border border-slate-700 bg-slate-900/70 p-3">
          <div class="flex items-center justify-between gap-2">
            <p class="text-[11px] uppercase tracking-wide text-slate-400">Decision Trace (24h)</p>
            <button
              class="rounded-md border border-slate-600 px-2 py-0.5 text-[10px] font-semibold text-slate-200 transition hover:border-cyan-500 hover:text-cyan-200 disabled:cursor-not-allowed disabled:opacity-40"
              :disabled="traceLoading"
              @click="refreshDecisionTrace"
            >
              Refresh
            </button>
          </div>
          <p v-if="traceError" class="mt-2 text-xs text-amber-300">{{ traceError }}</p>
          <p v-else-if="traceLoading && decisionTrace.length === 0" class="mt-2 text-xs text-slate-400">Loading trace entries...</p>
          <div v-else-if="decisionTrace.length > 0" class="mt-2 max-h-52 space-y-2 overflow-auto pr-1">
            <div
              v-for="entry in decisionTrace"
              :key="`${entry.command_id || 'cmd'}:${entry.timestamp}`"
              class="rounded-md border border-slate-700 bg-slate-950/60 p-2"
            >
              <div class="flex items-center justify-between gap-2">
                <span class="text-[11px] text-slate-400">{{ formatTraceTimestamp(entry.timestamp) }}</span>
                <span class="rounded-full border px-1.5 py-0.5 text-[10px]" :class="traceSourceBadgeClass(entry.decision_source)">
                  {{ traceSourceLabel(entry.decision_source) }}
                </span>
              </div>
              <p class="mt-1 text-xs text-slate-200">{{ traceCommandSummary(entry) }}</p>
              <p class="mt-1 text-[11px] text-slate-400">{{ traceDetailSummary(entry) }}</p>
            </div>
          </div>
          <p v-else class="mt-2 text-xs text-slate-400">No control decisions recorded in the last 24 hours.</p>
        </div>

        <div class="mt-4 rounded-lg border border-slate-700 bg-slate-900/70 p-3">
          <p class="text-[11px] uppercase tracking-wide text-slate-400">Current SoC Sync</p>
          <p class="mt-1 text-xs text-slate-400">Align simulator charge level with manual field telemetry.</p>
          <div class="mt-2 flex items-center gap-2">
            <input
              v-model.number="manualSocPercent"
              type="number"
              min="0"
              max="100"
              step="0.1"
              class="w-full rounded-md border border-slate-600 bg-slate-950 px-2 py-1 text-sm text-slate-100 outline-none focus:border-cyan-500"
              :disabled="isBusy"
            />
            <button
              class="rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-40"
              :disabled="isBusy"
              @click="syncCurrentSoc"
            >
              Sync SoC
            </button>
          </div>
        </div>

        <p class="mt-3 text-xs" :class="feedback.type === 'error' ? 'text-red-400' : 'text-cyan-300'" v-if="feedback.message">
          {{ feedback.message }}
        </p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useControlTransitionNotifications } from '../../composables/useControlTransitionNotifications'
import { useTenantContext } from '../../composables/useTenantContext'
import { useBatteryPhysicsStore } from '~/stores/batteryPhysicsStore'

interface FeedbackState {
  message: string
  type: 'success' | 'error'
}

interface DecisionTraceEntry {
  command_id?: string | null
  timestamp?: string | null
  requested_command?: string | null
  resolved_command?: string | null
  command?: string | null
  decision_source?: string | null
  power_kw?: number | null
  soc_before?: number | null
  soc_after?: number | null
  reason?: string | null
}

const props = withDefaults(
  defineProps<{
    title?: string
    subtitle?: string
  }>(),
  {
    title: 'Interactive Battery Illustration',
    subtitle: 'Unified control widget for Settings and Dashboard',
  }
)

const batteryPhysicsStore = useBatteryPhysicsStore()
const tenantContext = useTenantContext()
const transitionNotifications = useControlTransitionNotifications()
const targetPower = ref(0)
const manualSocPercent = ref(0)
const feedback = ref<FeedbackState>({ message: '', type: 'success' })
const decisionTrace = ref<DecisionTraceEntry[]>([])
const traceLoading = ref(false)
const traceError = ref('')
const traceWindowHours = ref(24)
const traceInterval = ref<ReturnType<typeof setInterval> | null>(null)

const isBusy = computed(() => batteryPhysicsStore.isLoading)

const effectiveDisplayPower = computed(() => {
  const measuredPower = Number(batteryPhysicsStore.state.power || 0)
  const appliedPower = Number(
    batteryPhysicsStore.state.appliedPowerCommand
      ?? batteryPhysicsStore.state.commandedPower
      ?? batteryPhysicsStore.state.powerCommand
      ?? 0,
  )

  // Prefer measured telemetry when present, but fall back to command flow
  // so simulation/manual control still communicates active charge/discharge.
  if (Math.abs(measuredPower) > 0.05) {
    return measuredPower
  }
  return appliedPower
})

const signedPower = computed(() => {
  const power = effectiveDisplayPower.value
  return `${power > 0 ? '+' : ''}${power.toFixed(1)}`
})

const commandText = computed(() => {
  const value = Number(targetPower.value || 0)
  return `${value > 0 ? '+' : ''}${value.toFixed(1)} kW`
})

const quickChargeFormula = computed(() => {
  const quickKw = Number((batteryPhysicsStore.state.maxChargePower * 0.8).toFixed(2))
  return `0.8 x ${batteryPhysicsStore.state.maxChargePower.toFixed(2)} kW = +${quickKw.toFixed(2)} kW`
})

const quickDischargeFormula = computed(() => {
  const quickKw = Number((batteryPhysicsStore.state.maxDischargePower * 0.8).toFixed(2))
  return `0.8 x ${batteryPhysicsStore.state.maxDischargePower.toFixed(2)} kW = -${quickKw.toFixed(2)} kW`
})

const decisionSourceNormalized = computed(() => {
  return String(batteryPhysicsStore.state.decision_source || '').trim().toLowerCase()
})

const requestedCommandLabel = computed(() => {
  return String(batteryPhysicsStore.state.requested_command || 'n/a').toUpperCase()
})

const activeCommandLabel = computed(() => {
  return String(batteryPhysicsStore.state.active_command || 'n/a').toUpperCase()
})

const autoSourceLabel = computed(() => {
  if (batteryPhysicsStore.state.manualMode) return 'Manual Mode'
  if (decisionSourceNormalized.value === 'dagster') return 'Dagster Auto'
  if (decisionSourceNormalized.value === 'ml') return 'ML Auto'
  if (decisionSourceNormalized.value === 'heuristic') return 'Heuristic Fallback'
  return 'Auto (Unknown Source)'
})

const autoSourceBadgeClass = computed(() => {
  if (batteryPhysicsStore.state.manualMode) return 'border-slate-600 bg-slate-700/40 text-slate-300'
  if (decisionSourceNormalized.value === 'dagster') return 'border-cyan-500/70 bg-cyan-500/15 text-cyan-200'
  if (decisionSourceNormalized.value === 'ml') return 'border-emerald-500/70 bg-emerald-500/15 text-emerald-200'
  if (decisionSourceNormalized.value === 'heuristic') return 'border-amber-500/70 bg-amber-500/15 text-amber-200'
  return 'border-slate-500/70 bg-slate-500/15 text-slate-200'
})

const autoIntelligenceSummary = computed(() => {
  if (batteryPhysicsStore.state.manualMode) {
    return 'Manual mode bypasses auto optimization and executes your direct command inputs.'
  }

  if (decisionSourceNormalized.value === 'dagster') {
    return 'Auto mode is using Dagster orchestration with live prices, battery state, and tenant config context.'
  }

  if (decisionSourceNormalized.value === 'ml') {
    return 'Auto mode is using ML recommendations from live market, weather, and battery signals.'
  }

  if (decisionSourceNormalized.value === 'heuristic') {
    return 'Auto mode is in fallback heuristic mode (price-threshold rules) because primary recommendation sources were unavailable.'
  }

  return 'Auto mode is enabled, but the decision source is not currently classified.'
})

const strategyLabel = computed(() => {
  const raw = String(batteryPhysicsStore.state.optimization_strategy || 'balanced')
  return raw.replace(/[_-]/g, ' ').toUpperCase()
})

const loadProfileLabel = computed(() => {
  const raw = String(batteryPhysicsStore.state.load_profile_type || 'standard')
  return raw.replace(/[_-]/g, ' ').toUpperCase()
})

const strategyWeightSummary = computed(() => {
  const weights = batteryPhysicsStore.state.strategy_weights
  if (!weights || typeof weights !== 'object') {
    return ''
  }

  const cost = Number(weights.cost ?? 0)
  const health = Number(weights.batteryHealth ?? 0)
  const renewable = Number(weights.renewableUse ?? 0)
  const reliability = Number(weights.reliability ?? 0)
  if (![cost, health, renewable, reliability].some((value) => Number.isFinite(value) && value > 0)) {
    return ''
  }

  return [
    `cost ${Math.round(cost * 100)}%`,
    `health ${Math.round(health * 100)}%`,
    `renewable ${Math.round(renewable * 100)}%`,
    `reliability ${Math.round(reliability * 100)}%`,
  ].join(', ')
})

const powerFlowColor = computed(() => {
  const power = effectiveDisplayPower.value
  if (power > 0) return 'text-emerald-400'
  if (power < 0) return 'text-amber-400'
  return 'text-slate-300'
})

const operationStatus = computed(() => {
  const modeLabel = batteryPhysicsStore.state.manualMode ? 'Manual' : 'Auto'
  if (batteryPhysicsStore.state.isCharging) {
    return {
      icon: '🟢',
      label: `${modeLabel} Charging`,
      tone: 'charging' as const,
    }
  }

  if (batteryPhysicsStore.state.isDischarging) {
    return {
      icon: '🟠',
      label: `${modeLabel} Discharging`,
      tone: 'discharging' as const,
    }
  }

  return {
    icon: '⚪',
    label: `${modeLabel} Idle`,
    tone: 'idle' as const,
  }
})

const operationBadgeClass = computed(() => {
  if (operationStatus.value.tone === 'charging') {
    return 'border-emerald-500/60 bg-emerald-500/15 text-emerald-200'
  }
  if (operationStatus.value.tone === 'discharging') {
    return 'border-amber-500/60 bg-amber-500/15 text-amber-200'
  }
  return 'border-slate-600 bg-slate-700/30 text-slate-300'
})

const temperatureColor = computed(() => {
  const temp = Number(batteryPhysicsStore.state.temperature || 0)
  if (temp >= 40) return 'text-red-400'
  if (temp >= 32) return 'text-amber-400'
  if (temp <= 5) return 'text-sky-400'
  return 'text-emerald-400'
})

const batteryFillStyle = computed(() => {
  const soc = Math.max(0, Math.min(100, Number(batteryPhysicsStore.state.socPercentage || 0)))
  let gradient = 'linear-gradient(180deg, rgba(34,197,94,0.95) 0%, rgba(22,163,74,0.9) 100%)'

  if (soc <= 25) {
    gradient = 'linear-gradient(180deg, rgba(248,113,113,0.95) 0%, rgba(220,38,38,0.85) 100%)'
  } else if (soc <= 50) {
    gradient = 'linear-gradient(180deg, rgba(251,191,36,0.95) 0%, rgba(217,119,6,0.9) 100%)'
  } else if (soc >= 90) {
    gradient = 'linear-gradient(180deg, rgba(56,189,248,0.95) 0%, rgba(14,116,144,0.9) 100%)'
  }

  return {
    height: `${soc}%`,
    background: gradient,
    boxShadow: '0 0 24px rgba(56,189,248,0.25) inset',
  }
})

watch(
  () => batteryPhysicsStore.state.powerCommand,
  (value) => {
    targetPower.value = Number(value || 0)
  },
  { immediate: true }
)

watch(
  () => batteryPhysicsStore.state.socPercentage,
  (value) => {
    manualSocPercent.value = Number(value || 0)
  },
  { immediate: true }
)

const setFeedback = (
  message: string,
  type: 'success' | 'error' = 'success',
  dedupeKey?: string,
) => {
  feedback.value = { message, type }

  transitionNotifications.emitActionToast({
    tenantId: tenantContext.currentTenantId.value,
    title: type === 'error' ? 'Battery Control Error' : 'Battery Control Update',
    message,
    color: type === 'error' ? 'red' : 'green',
    dedupeKey: dedupeKey || `${type}:${message}`,
  })

  setTimeout(() => {
    feedback.value = { message: '', type: 'success' }
  }, 2800)
}

const buildTenantRequest = async () => {
  await tenantContext.loadTenants()
  const tenantId = tenantContext.currentTenantId.value
  return {
    tenantId,
    request: {
      query: {
        tenantId,
      },
      headers: {
        'x-tenant-id': tenantId,
      },
    },
  }
}

const refreshDecisionTrace = async () => {
  traceLoading.value = true
  traceError.value = ''

  try {
    const { tenantId, request } = await buildTenantRequest()
    const payload = await $fetch<any>('/api/control/history', {
      ...request,
      query: {
        ...request.query,
        tenantId,
        limit: 14,
        since_hours: traceWindowHours.value,
      },
    })

    decisionTrace.value = Array.isArray(payload?.history)
      ? payload.history.slice(0, 14)
      : []
  } catch (error) {
    traceError.value = (error as Error)?.message || 'Unable to load decision trace'
  } finally {
    traceLoading.value = false
  }
}

const traceSourceLabel = (source: unknown): string => {
  const normalized = String(source || 'manual').toLowerCase()
  if (normalized === 'dagster') return 'Dagster'
  if (normalized === 'ml') return 'ML'
  if (normalized === 'heuristic') return 'Heuristic'
  if (normalized === 'manual') return 'Manual'
  return 'Other'
}

const traceSourceBadgeClass = (source: unknown): string => {
  const normalized = String(source || 'manual').toLowerCase()
  if (normalized === 'dagster') return 'border-cyan-500/70 bg-cyan-500/15 text-cyan-200'
  if (normalized === 'ml') return 'border-emerald-500/70 bg-emerald-500/15 text-emerald-200'
  if (normalized === 'heuristic') return 'border-amber-500/70 bg-amber-500/15 text-amber-200'
  if (normalized === 'manual') return 'border-slate-500/70 bg-slate-500/15 text-slate-200'
  return 'border-slate-500/70 bg-slate-500/15 text-slate-200'
}

const formatTraceTimestamp = (timestamp: unknown): string => {
  const parsed = new Date(String(timestamp || ''))
  if (!Number.isFinite(parsed.getTime())) {
    return 'Unknown time'
  }
  return parsed.toLocaleString('en-US', {
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

const traceCommandSummary = (entry: DecisionTraceEntry): string => {
  const requested = String(entry.requested_command || entry.command || 'hold').toUpperCase()
  const resolved = String(entry.resolved_command || entry.command || 'hold').toUpperCase()
  return requested === resolved ? resolved : `${requested} -> ${resolved}`
}

const traceDetailSummary = (entry: DecisionTraceEntry): string => {
  const power = Number(entry.power_kw || 0)
  const before = Number(entry.soc_before)
  const after = Number(entry.soc_after)
  const delta = Number.isFinite(before) && Number.isFinite(after)
    ? (after - before) * 100
    : null

  const powerText = `Power ${power > 0 ? '+' : ''}${power.toFixed(2)} kW`
  const socText = delta == null
    ? 'SoC n/a'
    : `SoC ${delta >= 0 ? '+' : ''}${delta.toFixed(1)}%`
  const reason = String(entry.reason || '').trim()
  const reasonText = reason ? `Reason: ${reason}` : 'Reason: n/a'

  return `${powerText} | ${socText} | ${reasonText}`
}

const toggleMode = async () => {
  try {
    const nextManual = !batteryPhysicsStore.state.manualMode
    await batteryPhysicsStore.setAutoMode(!nextManual)
    await refreshDecisionTrace()
    setFeedback(nextManual ? 'Manual mode enabled' : 'Auto mode enabled', 'success', `mode:${nextManual ? 'manual' : 'auto'}`)
  } catch {
    setFeedback('Failed to switch control mode', 'error', 'mode:error')
  }
}

const applyCommand = async () => {
  try {
    await batteryPhysicsStore.setPowerCommand(targetPower.value)
    await refreshDecisionTrace()
    setFeedback('Power command applied', 'success', 'power:apply')
  } catch {
    setFeedback('Failed to apply power command', 'error', 'power:apply:error')
  }
}

const quickCharge = async () => {
  try {
    await batteryPhysicsStore.charge(batteryPhysicsStore.state.maxChargePower * 0.8)
    await refreshDecisionTrace()
    setFeedback('Quick charge started', 'success', 'quick:charge')
  } catch {
    setFeedback('Quick charge failed', 'error', 'quick:charge:error')
  }
}

const quickDischarge = async () => {
  try {
    await batteryPhysicsStore.discharge(batteryPhysicsStore.state.maxDischargePower * 0.8)
    await refreshDecisionTrace()
    setFeedback('Quick discharge started', 'success', 'quick:discharge')
  } catch {
    setFeedback('Quick discharge failed', 'error', 'quick:discharge:error')
  }
}

const setIdle = async () => {
  try {
    await batteryPhysicsStore.idle()
    targetPower.value = 0
    await refreshDecisionTrace()
    setFeedback('Battery set to hold', 'success', 'hold')
  } catch {
    setFeedback('Failed to hold battery command', 'error', 'hold:error')
  }
}

const syncCurrentSoc = async () => {
  try {
    const normalized = Math.max(0, Math.min(100, Number(manualSocPercent.value || 0)))
    await batteryPhysicsStore.setStateOfCharge(normalized)
    manualSocPercent.value = normalized
    setFeedback(`SoC synchronized to ${normalized.toFixed(1)}%`, 'success', 'soc:sync')
  } catch {
    setFeedback('Failed to synchronize current SoC', 'error', 'soc:sync:error')
  }
}

const title = computed(() => props.title)
const subtitle = computed(() => props.subtitle)

watch(
  () => tenantContext.currentTenantId.value,
  () => {
    refreshDecisionTrace()
  }
)

onMounted(() => {
  refreshDecisionTrace()
  traceInterval.value = setInterval(() => {
    refreshDecisionTrace()
  }, 15000)
})

onBeforeUnmount(() => {
  if (traceInterval.value) {
    clearInterval(traceInterval.value)
    traceInterval.value = null
  }
})
</script>
