import fs from 'fs'
import path from 'path'

const DEFAULT_STATE = {
  soc: 75,
  capacity: 150,
  voltage: 400,
  current: 0,
  temperature: 22,
  cycles: 1245,
  health: 98.5,
  lastUpdate: new Date().toISOString()
}

function normalizeTenantSegment(tenantId?: string | null): string | null {
  if (typeof tenantId !== 'string') return null
  const normalized = tenantId.trim().toLowerCase().replace(/[^a-z0-9_-]/g, '_')
  return normalized.length > 0 ? normalized : null
}

function resolveBatteryFilePath(tenantId?: string | null): string {
  const normalizedTenant = normalizeTenantSegment(tenantId)
  if (normalizedTenant) {
    return path.join(process.cwd(), 'data', 'tenants', normalizedTenant, 'battery_state.json')
  }
  return path.join(process.cwd(), 'data', 'battery_state.json')
}

// Ensure data directory exists
const ensureDataDir = (filePath: string) => {
  const dataDir = path.dirname(filePath)
  if (!fs.existsSync(dataDir)) {
    fs.mkdirSync(dataDir, { recursive: true })
  }
}

export const getBatteryState = async (tenantId?: string | null) => {
  const tenantFile = resolveBatteryFilePath(tenantId)
  const legacyFile = resolveBatteryFilePath(null)

  try {
    ensureDataDir(tenantFile)
    if (fs.existsSync(tenantFile)) {
      const data = JSON.parse(fs.readFileSync(tenantFile, 'utf8'))
      return data
    }

    // Backward-compatible fallback for default tenant or unscoped calls.
    if (!normalizeTenantSegment(tenantId) && fs.existsSync(legacyFile)) {
      const data = JSON.parse(fs.readFileSync(legacyFile, 'utf8'))
      return data
    }
  } catch (e) {
    console.warn('Failed to load battery state:', e)
  }
  return {
    ...DEFAULT_STATE,
    lastUpdate: new Date().toISOString(),
  }
}

export const updateBatteryState = async (
  updates: Partial<typeof DEFAULT_STATE>,
  tenantId?: string | null,
) => {
  const current = await getBatteryState(tenantId)
  const updated = {
    ...current,
    ...updates,
    lastUpdate: new Date().toISOString()
  }
  
  const filePath = resolveBatteryFilePath(tenantId)
  ensureDataDir(filePath)
  fs.writeFileSync(filePath, JSON.stringify(updated, null, 2))
  return updated
}

export const simulateBatteryBehavior = async (tenantId?: string | null) => {
  // Simulate battery changes over time
  const state = await getBatteryState(tenantId)

  const deterministicNoise = (seed: number) => {
    const value = Math.sin(seed * 12.9898 + 78.233) * 43758.5453
    return value - Math.floor(value)
  }
  
  // SOC changes based on time of day and solar
  const now = new Date()
  const hour = now.getHours()
  const minuteSeed = Math.floor(now.getTime() / 60000)
  let socDelta = 0
  const nSoc = deterministicNoise(minuteSeed + hour * 37)
  
  if (hour >= 5 && hour <= 12) {
    // Solar charging period (morning)
    socDelta = nSoc * 0.8 // +0 to +0.8%/min
  } else if (hour >= 13 && hour <= 18) {
    // Peak solar, variable behavior
    socDelta = (nSoc - 0.6) * 0.5
  } else if (hour >= 19 && hour <= 23) {
    // Evening peak demand
    socDelta = -nSoc * 0.4
  } else {
    // Night: slight discharge or charge depending on tariff
    socDelta = (nSoc - 0.7) * 0.2
  }
  
  // Calculate new SOC
  let newSOC = Math.max(state.soc + socDelta, 0)
  newSOC = Math.min(newSOC, 100)
  
  // Simulate temperature variation based on current
  const nCurrent = deterministicNoise(minuteSeed + 11)
  const nTemp = deterministicNoise(minuteSeed + 23)
  const current = nCurrent * 50 - 25 // -25 to +25 A
  const temperature = 20 + nTemp * 10 + (Math.abs(current) / 50) * 5
  
  // Update voltage based on SOC
  const voltage = 320 + (newSOC / 100) * 80
  
  return updateBatteryState({
    soc: parseFloat(newSOC.toFixed(2)),
    current: parseFloat(current.toFixed(2)),
    voltage: parseFloat(voltage.toFixed(2)),
    temperature: parseFloat(temperature.toFixed(1))
  }, tenantId)
}
