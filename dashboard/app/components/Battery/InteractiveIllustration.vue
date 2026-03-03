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

        <p class="mt-3 text-xs" :class="feedback.type === 'error' ? 'text-red-400' : 'text-cyan-300'" v-if="feedback.message">
          {{ feedback.message }}
        </p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useControlTransitionNotifications } from '../../composables/useControlTransitionNotifications'
import { useTenantContext } from '../../composables/useTenantContext'
import { useBatteryPhysicsStore } from '~/stores/batteryPhysicsStore'

interface FeedbackState {
  message: string
  type: 'success' | 'error'
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
const feedback = ref<FeedbackState>({ message: '', type: 'success' })

const isBusy = computed(() => batteryPhysicsStore.isLoading)

const effectiveDisplayPower = computed(() => {
  const measuredPower = Number(batteryPhysicsStore.state.power || 0)
  const commandPower = Number(batteryPhysicsStore.state.powerCommand || 0)

  // Prefer measured telemetry when present, but fall back to command flow
  // so simulation/manual control still communicates active charge/discharge.
  if (Math.abs(measuredPower) > 0.05) {
    return measuredPower
  }
  return commandPower
})

const signedPower = computed(() => {
  const power = effectiveDisplayPower.value
  return `${power > 0 ? '+' : ''}${power.toFixed(1)}`
})

const commandText = computed(() => {
  const value = Number(targetPower.value || 0)
  return `${value > 0 ? '+' : ''}${value.toFixed(1)} kW`
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

const toggleMode = async () => {
  try {
    const nextManual = !batteryPhysicsStore.state.manualMode
    await batteryPhysicsStore.setAutoMode(!nextManual)
    setFeedback(nextManual ? 'Manual mode enabled' : 'Auto mode enabled', 'success', `mode:${nextManual ? 'manual' : 'auto'}`)
  } catch {
    setFeedback('Failed to switch control mode', 'error', 'mode:error')
  }
}

const applyCommand = async () => {
  try {
    await batteryPhysicsStore.setPowerCommand(targetPower.value)
    setFeedback('Power command applied', 'success', 'power:apply')
  } catch {
    setFeedback('Failed to apply power command', 'error', 'power:apply:error')
  }
}

const quickCharge = async () => {
  try {
    await batteryPhysicsStore.charge(batteryPhysicsStore.state.maxChargePower * 0.8)
    setFeedback('Quick charge started', 'success', 'quick:charge')
  } catch {
    setFeedback('Quick charge failed', 'error', 'quick:charge:error')
  }
}

const quickDischarge = async () => {
  try {
    await batteryPhysicsStore.discharge(batteryPhysicsStore.state.maxDischargePower * 0.8)
    setFeedback('Quick discharge started', 'success', 'quick:discharge')
  } catch {
    setFeedback('Quick discharge failed', 'error', 'quick:discharge:error')
  }
}

const setIdle = async () => {
  try {
    await batteryPhysicsStore.idle()
    targetPower.value = 0
    setFeedback('Battery set to hold', 'success', 'hold')
  } catch {
    setFeedback('Failed to hold battery command', 'error', 'hold:error')
  }
}

const title = computed(() => props.title)
const subtitle = computed(() => props.subtitle)
</script>
