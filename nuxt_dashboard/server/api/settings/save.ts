import fs from 'fs'
import path from 'path'

export default defineEventHandler(async (event) => {
  // POST /api/settings/save - Save settings to file

  const body = await readBody(event)

  try {
    // Ensure data directory exists
    const dataDir = path.join(process.cwd(), 'data')
    if (!fs.existsSync(dataDir)) {
      fs.mkdirSync(dataDir, { recursive: true })
    }

    // Save settings to JSON file
    const settingsFile = path.join(dataDir, 'settings.json')
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
      message: 'Settings saved successfully',
      timestamp,
      settings: settingsData
    }
  } catch (error: any) {
    console.error('Failed to save settings:', error)

    return {
      success: false,
      error: error.message || 'Failed to save settings'
    }
  }
})
