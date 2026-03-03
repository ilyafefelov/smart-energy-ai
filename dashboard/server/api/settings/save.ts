import fs from 'fs'
import path from 'path'
import { getTenantResponseMetadata, resolveTenantContext } from '../../utils/tenant-context'

export default defineEventHandler(async (event) => {
  // POST /api/settings/save - Save settings to file

  const body = await readBody(event)

  try {
    const tenant = await resolveTenantContext(event, { body })
    // Ensure data directory exists
    const dataDir = path.join(process.cwd(), 'data')
    const tenantDataDir = path.join(dataDir, 'tenants', tenant.id)
    if (!fs.existsSync(tenantDataDir)) {
      fs.mkdirSync(tenantDataDir, { recursive: true })
    }

    // Save settings to JSON file
    const settingsFile = path.join(tenantDataDir, 'settings.json')
    const timestamp = new Date().toISOString()

    const settingsData = {
      ...body,
      lastUpdated: timestamp,
      version: '1.0'
    }

    fs.writeFileSync(
      settingsFile,
      JSON.stringify(settingsData, null, 2),
      'utf-8'
    )

    return {
      success: true,
      tenant: getTenantResponseMetadata(tenant),
      message: 'Settings saved successfully',
      timestamp,
      settings: settingsData
    }
  } catch (error: any) {
    const errorData = error?.data
    if (errorData?.error?.code === 'INVALID_TENANT') {
      return errorData
    }

    console.error('Failed to save settings:', error)

    return {
      success: false,
      error: error.message || 'Failed to save settings'
    }
  }
})
