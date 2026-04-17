type GlobalControlState = typeof globalThis & {
  scheduledCommands?: ScheduledCommandRecord[]
  commandHistory?: CommandHistoryRecord[]
  __controlModeByTenant?: Record<string, ControlModeState>
  __scheduleIdCounter?: number
}

type TenantScopedRecord = {
  tenant_id?: string | null
  tenantId?: string | null
}

export type ScheduledCommandRecord = TenantScopedRecord & {
  id?: string
  schedule_id?: string | null
  command_id?: string | null
  command?: string | null
  power_kw?: number | null
  scheduled_time?: string | null
  reason?: string | null
  user_id?: string | null
  created_at?: string | null
  status?: string | null
  decision_snapshot?: {
    version?: string | null
    [key: string]: unknown
  } | null
  [key: string]: unknown
}

export type CommandHistoryRecord = TenantScopedRecord & {
  command_id?: string | null
  schedule_id?: string | null
  command?: string | null
  requested_command?: string | null
  resolved_command?: string | null
  power_kw?: number | null
  timestamp?: string | null
  executed_at?: string | null
  reason?: string | null
  decision_source?: string | null
  result?: {
    estimated_completion?: string | null
    [key: string]: unknown
  } | null
  [key: string]: unknown
}

export type ControlModeState = {
  mode?: 'manual' | 'automatic' | string
  active_command?: 'charge' | 'discharge' | 'hold' | null | string
  requested_command?: 'charge' | 'discharge' | 'hold' | 'auto' | null | string
  decision_source?: string | null
  reason?: string | null
  updated_at?: string | null
}

const globalControlState = globalThis as GlobalControlState

export function getScheduledCommands(): ScheduledCommandRecord[] {
  return Array.isArray(globalControlState.scheduledCommands) ? globalControlState.scheduledCommands : []
}

export function ensureScheduledCommands(): ScheduledCommandRecord[] {
  if (!Array.isArray(globalControlState.scheduledCommands)) {
    globalControlState.scheduledCommands = []
  }
  return globalControlState.scheduledCommands
}

export function setScheduledCommands(commands: ScheduledCommandRecord[]): void {
  globalControlState.scheduledCommands = commands
}

export function getCommandHistory(): CommandHistoryRecord[] {
  return Array.isArray(globalControlState.commandHistory) ? globalControlState.commandHistory : []
}

export function getControlModeState(tenantId: string): ControlModeState | null {
  if (!globalControlState.__controlModeByTenant) {
    return null
  }
  return globalControlState.__controlModeByTenant[tenantId] ?? null
}

export function getErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof Error && error.message) {
    return error.message
  }
  if (typeof error === 'string' && error.trim()) {
    return error
  }
  return fallback
}

export function hasStatusCode(error: unknown): error is { statusCode: number } {
  return typeof error === 'object'
    && error !== null
    && 'statusCode' in error
    && typeof (error as { statusCode?: unknown }).statusCode === 'number'
}