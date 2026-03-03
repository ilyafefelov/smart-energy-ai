import fs from 'fs'
import path from 'path'

export type TenantBatteryControlState = {
  powerCommand: number
  manualMode: boolean
  autoOptimization: boolean
  updatedAt: string
}

const DEFAULT_CONTROL_STATE: TenantBatteryControlState = {
  powerCommand: 0,
  manualMode: true,
  autoOptimization: false,
  updatedAt: new Date().toISOString(),
}

function normalizeTenantSegment(tenantId?: string | null): string | null {
  if (typeof tenantId !== 'string') return null
  const normalized = tenantId.trim().toLowerCase().replace(/[^a-z0-9_-]/g, '_')
  return normalized.length > 0 ? normalized : null
}

function resolveControlStateFilePath(tenantId?: string | null): string {
  const normalizedTenant = normalizeTenantSegment(tenantId)
  if (normalizedTenant) {
    return path.join(process.cwd(), 'data', 'tenants', normalizedTenant, 'battery_control_state.json')
  }
  return path.join(process.cwd(), 'data', 'battery_control_state.json')
}

function ensureDataDir(filePath: string) {
  const dataDir = path.dirname(filePath)
  if (!fs.existsSync(dataDir)) {
    fs.mkdirSync(dataDir, { recursive: true })
  }
}

function sanitizeState(input: unknown): TenantBatteryControlState {
  const raw = (input && typeof input === 'object') ? (input as Record<string, unknown>) : {}
  const powerCommand = Number(raw.powerCommand)
  return {
    powerCommand: Number.isFinite(powerCommand) ? Number(powerCommand.toFixed(3)) : 0,
    manualMode: Boolean(raw.manualMode),
    autoOptimization: Boolean(raw.autoOptimization),
    updatedAt: typeof raw.updatedAt === 'string' && raw.updatedAt.trim()
      ? raw.updatedAt
      : new Date().toISOString(),
  }
}

export async function getBatteryControlState(tenantId?: string | null): Promise<TenantBatteryControlState> {
  const tenantFile = resolveControlStateFilePath(tenantId)
  const legacyFile = resolveControlStateFilePath(null)

  try {
    ensureDataDir(tenantFile)
    if (fs.existsSync(tenantFile)) {
      return sanitizeState(JSON.parse(fs.readFileSync(tenantFile, 'utf8')))
    }

    if (!normalizeTenantSegment(tenantId) && fs.existsSync(legacyFile)) {
      return sanitizeState(JSON.parse(fs.readFileSync(legacyFile, 'utf8')))
    }
  } catch (e) {
    console.warn('Failed to load battery control state:', e)
  }

  return {
    ...DEFAULT_CONTROL_STATE,
    updatedAt: new Date().toISOString(),
  }
}

export async function updateBatteryControlState(
  updates: Partial<TenantBatteryControlState>,
  tenantId?: string | null,
): Promise<TenantBatteryControlState> {
  const current = await getBatteryControlState(tenantId)
  const next = sanitizeState({
    ...current,
    ...updates,
    updatedAt: new Date().toISOString(),
  })

  const filePath = resolveControlStateFilePath(tenantId)
  ensureDataDir(filePath)
  fs.writeFileSync(filePath, JSON.stringify(next, null, 2))
  return next
}
