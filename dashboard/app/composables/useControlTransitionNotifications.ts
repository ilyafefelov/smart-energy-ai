import { computed, ref } from 'vue'
import { useSettingsStore } from '~/stores/settingsStore'

type ToastPayload = {
  id?: string
  title?: string
  description?: string
  color?: string
  icon?: string
}

export type ControlStatusSnapshot = {
  mode?: string | null
  active_command?: string | { command?: string | null } | null
  requested_command?: string | null
  decision_source?: string | null
}

function resolveToast(): { add: (payload: ToastPayload) => void } {
  const candidate = (globalThis as any)?.useToast
  if (typeof candidate === 'function') {
    try {
      return candidate()
    } catch {
      // Fall through to no-op when toast provider is unavailable.
    }
  }

  return {
    add: (_payload: ToastPayload) => undefined,
  }
}

type ActionToastInput = {
  tenantId?: string
  title?: string
  message: string
  color?: string
  icon?: string
  dedupeKey?: string
}

const TRANSITION_TOAST_DEBOUNCE_MS = 10000

export function useControlTransitionNotifications() {
  const toast = resolveToast()
  const settingsStore = useSettingsStore()

  const lastTransitionToastKey = ref<string | null>(null)
  const lastTransitionToastAt = ref(0)

  const transitionNotificationsEnabled = computed(() => {
    return Boolean(
      settingsStore.generalSettings?.notificationsEnabled !== false
      && settingsStore.notificationSettings?.systemAlerts !== false,
    )
  })

  const normalizeActiveCommand = (value: ControlStatusSnapshot['active_command']): string | null => {
    if (!value) return null
    if (typeof value === 'string') return value
    if (typeof value?.command === 'string') return value.command
    return null
  }

  const buildTransitionToastKey = (nextStatus: ControlStatusSnapshot, tenantId?: string): string => {
    const mode = nextStatus?.mode || 'unknown'
    const requested = nextStatus?.requested_command || 'none'
    const active = normalizeActiveCommand(nextStatus?.active_command) || 'none'
    const source = nextStatus?.decision_source || 'unknown'
    return `${tenantId || 'unknown'}:${mode}:${requested}:${active}:${source}`
  }

  const emitTransitionToastIfNeeded = (
    previousStatus: ControlStatusSnapshot,
    nextStatus: ControlStatusSnapshot,
    tenantId?: string,
  ): void => {
    if (!transitionNotificationsEnabled.value) {
      return
    }

    const previousMode = previousStatus?.mode || null
    const nextMode = nextStatus?.mode || null
    const previousActive = normalizeActiveCommand(previousStatus?.active_command)
    const nextActive = normalizeActiveCommand(nextStatus?.active_command)
    const previousRequested = previousStatus?.requested_command || null
    const nextRequested = nextStatus?.requested_command || null

    const modeChanged = previousMode !== nextMode
    const activeChanged = previousActive !== nextActive
    const requestedChanged = previousRequested !== nextRequested

    if (!modeChanged && !activeChanged && !requestedChanged) {
      return
    }

    const transitionKey = buildTransitionToastKey(nextStatus, tenantId)
    const now = Date.now()
    if (lastTransitionToastKey.value === transitionKey && now - lastTransitionToastAt.value < TRANSITION_TOAST_DEBOUNCE_MS) {
      return
    }

    lastTransitionToastKey.value = transitionKey
    lastTransitionToastAt.value = now

    const modeLabel = nextMode ? String(nextMode).toUpperCase() : 'UNKNOWN'
    const activeLabel = (nextActive || 'idle').toUpperCase()
    const requestedLabel = nextRequested ? String(nextRequested).toUpperCase() : null
    const sourceLabel = nextStatus?.decision_source ? String(nextStatus.decision_source).toUpperCase() : null

    const reasonParts = [
      `Mode: ${modeLabel}`,
      `Action: ${activeLabel}`,
    ]
    if (requestedLabel) reasonParts.push(`Requested: ${requestedLabel}`)
    if (sourceLabel) reasonParts.push(`Source: ${sourceLabel}`)

    toast.add({
      id: `control-transition:${transitionKey}`,
      title: modeChanged ? 'Control Mode Transition' : 'Control Action Updated',
      description: reasonParts.join(' | '),
      color: nextMode === 'automatic' ? 'green' : 'blue',
      icon: nextMode === 'automatic' ? 'i-heroicons-cpu-chip' : 'i-heroicons-bolt',
    })
  }

  const emitActionToast = (input: ActionToastInput): void => {
    if (!transitionNotificationsEnabled.value) {
      return
    }

    const color = input.color || 'green'
    const toastId = input.dedupeKey
      ? `control-action:${input.tenantId || 'unknown'}:${input.dedupeKey}`
      : undefined

    toast.add({
      id: toastId,
      title: input.title || 'Battery Control Update',
      description: input.message,
      color,
      icon: input.icon || (color === 'red' ? 'i-heroicons-exclamation-circle' : 'i-heroicons-check-circle'),
    })
  }

  const resetTransitionDeduper = (): void => {
    lastTransitionToastKey.value = null
    lastTransitionToastAt.value = 0
  }

  return {
    transitionNotificationsEnabled,
    emitTransitionToastIfNeeded,
    emitActionToast,
    resetTransitionDeduper,
  }
}
