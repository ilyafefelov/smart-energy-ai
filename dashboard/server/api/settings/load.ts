import fs from 'fs'
import path from 'path'
import { getTenantResponseMetadata, resolveTenantContext } from '../../utils/tenant-context'

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
    const tenant = await resolveTenantContext(event)
    const dataDir = path.join(process.cwd(), 'data')
    const tenantDataDir = path.join(dataDir, 'tenants', tenant.id)
    const tenantSettingsFile = path.join(tenantDataDir, 'settings.json')
    const legacySettingsFile = path.join(dataDir, 'settings.json')

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

    const effectiveSettingsFile = fs.existsSync(tenantSettingsFile)
      ? tenantSettingsFile
      : tenant.id === tenant.defaultTenantId && fs.existsSync(legacySettingsFile)
        ? legacySettingsFile
        : null

    if (effectiveSettingsFile) {
      const fileContent = fs.readFileSync(effectiveSettingsFile, 'utf-8')
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
        tenant: getTenantResponseMetadata(tenant),
        settings,
      }
    } else {
      // File doesn't exist yet, return defaults
      return {
        success: true,
        tenant: getTenantResponseMetadata(tenant),
        settings: defaultSettings,
      }
    }
  } catch (error: any) {
    const errorData = error?.data
    if (errorData?.error?.code === 'INVALID_TENANT') {
      return errorData
    }

    console.error('Failed to load settings:', error)

    return {
      success: false,
      error: error.message || 'Failed to load settings',
      settings: null
    }
  }
})
