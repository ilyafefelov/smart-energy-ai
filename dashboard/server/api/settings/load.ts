import fs from 'fs'
import path from 'path'

export default defineEventHandler(async (event) => {
  // GET /api/settings/load - Load settings from file

  try {
    const dataDir = path.join(process.cwd(), 'data')
    const settingsFile = path.join(dataDir, 'settings.json')

    if (fs.existsSync(settingsFile)) {
      const fileContent = fs.readFileSync(settingsFile, 'utf-8')
      const settings = JSON.parse(fileContent)

      return {
        success: true,
        settings,
        source: 'file'
      }
    } else {
      // File doesn't exist yet, return empty/null
      return {
        success: true,
        settings: null,
        source: 'none',
        message: 'No saved settings found (will use defaults)'
      }
    }
  } catch (error: any) {
    console.error('Failed to load settings:', error)

    return {
      success: false,
      settings: null,
      error: error.message || 'Failed to load settings'
    }
  }
})
