import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const PROJECT_ROOT = path.resolve(__dirname, '../../../')

const BATTERY_FILE = path.join(PROJECT_ROOT, 'data', 'battery_state.json')

// Find ML config file
const ML_CONFIG_PATHS = [
  path.join(PROJECT_ROOT, 'energy_ml/configs/user_config.json'),
  path.join(PROJECT_ROOT, '../energy_ml/configs/user_config.json'),
  path.join(PROJECT_ROOT, '../../energy_ml/configs/user_config.json'),
  'C:/Users/ilyaf/clawd/projects/smart-energy-ai/energy_ml/configs/user_config.json'
]

let ML_CONFIG_FILE = ML_CONFIG_PATHS[0]
for (const p of ML_CONFIG_PATHS) {
  if (fs.existsSync(p)) {
    ML_CONFIG_FILE = p
    break
  }
}

// Get capacity from ML config or use default
const getMLConfigCapacity = (): number => {
  try {
    if (fs.existsSync(ML_CONFIG_FILE)) {
      const config = JSON.parse(fs.readFileSync(ML_CONFIG_FILE, 'utf8'))
      return config.battery_capacity_kwh || 150
    }
  } catch (e) {
    console.warn('Failed to read ML config:', e)
  }
  return 150
}

const DEFAULT_STATE = {
  soc: 75,
  capacity: getMLConfigCapacity(), // Read from ML config
  voltage: 400,
  current: 0,
  temperature: 22,
  cycles: 1245,
  health: 98.5,
  lastUpdate: new Date().toISOString()
}

// Ensure data directory exists
const ensureDataDir = () => {
  const dataDir = path.dirname(BATTERY_FILE)
  if (!fs.existsSync(dataDir)) {
    fs.mkdirSync(dataDir, { recursive: true })
  }
}

export const getBatteryState = async () => {
  try {
    ensureDataDir()
    if (fs.existsSync(BATTERY_FILE)) {
      const data = JSON.parse(fs.readFileSync(BATTERY_FILE, 'utf8'))
      // Always use current ML config capacity
      data.capacity = getMLConfigCapacity()
      return data
    }
  } catch (e) {
    console.warn('Failed to load battery state:', e)
  }
  return DEFAULT_STATE
}

export const updateBatteryState = async (updates: Partial<typeof DEFAULT_STATE>) => {
  const current = await getBatteryState()
  const updated = {
    ...current,
    ...updates,
    lastUpdate: new Date().toISOString()
  }
  
  ensureDataDir()
  fs.writeFileSync(BATTERY_FILE, JSON.stringify(updated, null, 2))
  return updated
}

export const simulateBatteryBehavior = async () => {
  // Simulate random battery behavior for testing
  const state = await getBatteryState()
  
  // Random SOC change (-2% to +2%)
  const socChange = (Math.random() - 0.5) * 4
  state.soc = Math.max(15, Math.min(95, state.soc + socChange))
  
  // Random temperature change
  state.temperature += (Math.random() - 0.5) * 0.5
  
  // Random current based on SOC
  if (state.soc < 30) {
    state.current = Math.random() * 30 // Charging
  } else if (state.soc > 70) {
    state.current = -Math.random() * 30 // Discharging
  } else {
    state.current = (Math.random() - 0.5) * 10 // Idle/mixed
  }
  
  state.lastUpdate = new Date().toISOString()
  
  await updateBatteryState(state)
  return state
}
