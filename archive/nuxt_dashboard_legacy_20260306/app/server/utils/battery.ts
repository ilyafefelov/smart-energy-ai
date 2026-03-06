import fs from 'fs'
import path from 'path'

const BATTERY_FILE = path.join(process.cwd(), 'data', 'battery_state.json')

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
  // Simulate battery changes over time
  const state = await getBatteryState()
  
  // SOC changes based on time of day and solar
  const hour = new Date().getHours()
  let socDelta = 0
  
  if (hour >= 5 && hour <= 12) {
    // Solar charging period (morning)
    socDelta = Math.random() * 0.8 // +0 to +0.8%/min
  } else if (hour >= 13 && hour <= 18) {
    // Peak solar, variable behavior
    socDelta = (Math.random() - 0.6) * 0.5
  } else if (hour >= 19 && hour <= 23) {
    // Evening peak demand
    socDelta = -Math.random() * 0.4
  } else {
    // Night: slight discharge or charge depending on tariff
    socDelta = (Math.random() - 0.7) * 0.2
  }
  
  // Calculate new SOC
  let newSOC = Math.max(state.soc + socDelta, 0)
  newSOC = Math.min(newSOC, 100)
  
  // Simulate temperature variation based on current
  const current = Math.random() * 50 - 25 // -25 to +25 A
  const temperature = 20 + Math.random() * 10 + (Math.abs(current) / 50) * 5
  
  // Update voltage based on SOC
  const voltage = 320 + (newSOC / 100) * 80
  
  return updateBatteryState({
    soc: parseFloat(newSOC.toFixed(2)),
    current: parseFloat(current.toFixed(2)),
    voltage: parseFloat(voltage.toFixed(2)),
    temperature: parseFloat(temperature.toFixed(1))
  })
}
