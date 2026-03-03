import fs from 'fs'
import path from 'path'
import { getTenantResponseMetadata, resolveTenantContext } from '../../utils/tenant-context'

export default defineEventHandler(async (event) => {
  try {
    const tenant = await resolveTenantContext(event)
    const tenantDataDir = path.join(process.cwd(), 'data', 'tenants', tenant.id)
    const tenantSettingsFile = path.join(tenantDataDir, 'settings.json')
    const legacySettingsFile = path.join(process.cwd(), 'data', 'settings.json')
    const SETTINGS_FILE = fs.existsSync(tenantSettingsFile)
      ? tenantSettingsFile
      : tenant.id === tenant.defaultTenantId
        ? legacySettingsFile
        : tenantSettingsFile
    
    // Load settings
    let settings: any = null
    if (fs.existsSync(SETTINGS_FILE)) {
      const data = fs.readFileSync(SETTINGS_FILE, 'utf8')
      settings = JSON.parse(data)
    } else {
      // Return default settings if file doesn't exist
      settings = {
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
    }
    
    // Create export object with metadata
    const now = new Date()
    const dateStr = now.toISOString().split('T')[0]
    const siteName = settings.general?.siteName || 'Factory'
    
    const exportData = {
      metadata: {
        exported: now.toISOString(),
        version: '1.0',
        tenant: getTenantResponseMetadata(tenant),
        siteName: siteName,
        timestamp: now.getTime()
      },
      settings: settings
    }
    
    // Set headers for file download
    const filename = `settings-${siteName.toLowerCase().replace(/\s+/g, '-')}-${dateStr}.json`
    setHeader(event, 'Content-Type', 'application/json')
    setHeader(event, 'Content-Disposition', `attachment; filename="${filename}"`)
    
    return exportData
  } catch (error: any) {
    const errorData = error?.data
    if (errorData?.error?.code === 'INVALID_TENANT') {
      return errorData
    }

    throw createError({
      statusCode: 500,
      statusMessage: `Failed to export settings: ${error.message}`
    })
  }
})
