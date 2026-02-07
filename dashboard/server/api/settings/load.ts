import fs from 'fs'
import path from 'path'

interface SettingsData {
  general?: any
  battery?: any
  notifications?: any
  model?: any
}

export default defineEventHandler(async (event) => {
  // GET /api/settings/load - Load settings from file
  // STANDARDIZED RESPONSE FORMAT: { success: bool, settings: { general, battery, notifications, model } }

  try {
    const dataDir = path.join(process.cwd(), 'data')
    const settingsFile = path.join(dataDir, 'settings.json')

    // Default structure to ensure all keys exist
    const defaultSettings: SettingsData = {
      general: {
        siteName: 'Factory #1',
        timezone: 'Europe/Kiev (GMT+2)',
        currency: 'UAH',
        notificationsEnabled: true
      },
      battery: {
        capacity: 150,
        minSOC: 15,
        maxChargeRate: 50,
        maxDischargeRate: 50
      },
      notifications: {
        highPrice: true,
        highPriceThreshold: 13.0,
        lowPrice: true,
        lowPriceThreshold: 7.0,
        modelComplete: true,
        systemAlerts: true
      },
      model: {
        learningRate: 0.0003,
        batchSize: 64,
        epochs: 20
      }
    }

    if (fs.existsSync(settingsFile)) {
      const fileContent = fs.readFileSync(settingsFile, 'utf-8')
      const loaded = JSON.parse(fileContent)

      // Merge with defaults to ensure all keys are present
      const settings: SettingsData = {
        general: { ...defaultSettings.general, ...loaded.general },
        battery: { ...defaultSettings.battery, ...loaded.battery },
        notifications: { ...defaultSettings.notifications, ...loaded.notifications },
        model: { ...defaultSettings.model, ...loaded.model }
      }

      return {
        success: true,
        settings
      }
    } else {
      // File doesn't exist yet, return defaults
      return {
        success: true,
        settings: defaultSettings
      }
    }
  } catch (error: any) {
    console.error('Failed to load settings:', error)

    return {
      success: false,
      error: error.message || 'Failed to load settings',
      settings: null
    }
  }
})
