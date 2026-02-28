// Sync settings from Nuxt to ML pipeline config

import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const PROJECT_ROOT = path.resolve(__dirname, '../../../../../')

const POSSIBLE_PATHS = [
  path.join(PROJECT_ROOT, 'energy_ml/configs/user_config.json'),
  path.join(PROJECT_ROOT, '../energy_ml/configs/user_config.json'),
  path.join(PROJECT_ROOT, '../../energy_ml/configs/user_config.json'),
  'C:/Users/ilyaf/clawd/projects/smart-energy-ai/energy_ml/configs/user_config.json'
]

let CONFIG_FILE = POSSIBLE_PATHS[0]
for (const p of POSSIBLE_PATHS) {
  if (fs.existsSync(p)) {
    CONFIG_FILE = p
    break
  }
}

export default defineEventHandler(async (event) => {
  const method = getMethod(event)
  
  if (method === 'POST') {
    try {
      let config: any = {}
      if (fs.existsSync(CONFIG_FILE)) {
        config = JSON.parse(fs.readFileSync(CONFIG_FILE, 'utf8'))
      }
      
      const body = await readBody(event)
      console.log('[settings/sync] Received body:', JSON.stringify(body, null, 2))
      
      // Battery settings
      if (body.battery) {
        config.battery_capacity_kwh = body.battery.capacity ?? config.battery_capacity_kwh
        config.battery_c_rate_charge = (body.battery.maxChargeRate ?? 50) / (body.battery.capacity ?? 150)
        config.battery_c_rate_discharge = (body.battery.maxDischargeRate ?? 50) / (body.battery.capacity ?? 150)
        config.battery_soc_min = (body.battery.minSOC ?? 15) / 100
        config.battery_soc_max = (body.battery.maxSOC ?? 95) / 100
      }
      
      // Generation settings - handle both formats
      // Nuxt sends: { solarCapacity: 50, windCapacity: 10 }
      if (body.generation) {
        config.solar_capacity_kw = body.generation.solarCapacity ?? body.generation.solar?.capacity ?? config.solar_capacity_kw
        config.wind_capacity_kw = body.generation.windCapacity ?? body.generation.wind?.capacity ?? config.wind_capacity_kw
      }
      
      // Optimization settings
      if (body.optimization) {
        config.optimization_strategy = body.optimization.strategy ?? config.optimization_strategy
      }
      
      fs.writeFileSync(CONFIG_FILE, JSON.stringify(config, null, 2))
      console.log('[settings/sync] Updated config:', JSON.stringify(config, null, 2))
      
      return { success: true, config }
    } catch (error: any) {
      console.error('[settings/sync] Error:', error)
      return { success: false, error: error.message }
    }
  }
  
  if (method === 'GET') {
    try {
      if (fs.existsSync(CONFIG_FILE)) {
        const config = JSON.parse(fs.readFileSync(CONFIG_FILE, 'utf8'))
        return { success: true, config }
      }
      return { success: false, error: 'No config found' }
    } catch (error: any) {
      return { success: false, error: error.message }
    }
  }
  
  return { success: false, error: 'Method not allowed' }
})
