import fs from 'fs'
import path from 'path'

export default defineEventHandler(async (event) => {
  try {
    const SETTINGS_FILE = path.join(process.cwd(), 'data/settings.json')
    const BACKUP_DIR = path.join(process.cwd(), 'data/backups')
    
    // Ensure backup directory exists
    if (!fs.existsSync(BACKUP_DIR)) {
      fs.mkdirSync(BACKUP_DIR, { recursive: true })
    }
    
    // Parse multipart form data
    const formData = await readMultipartFormData(event)
    
    if (!formData || formData.length === 0) {
      throw new Error('No file provided')
    }
    
    // Get the file from form data
    const fileField = formData.find(f => f.name === 'file')
    if (!fileField || !fileField.data) {
      throw new Error('File field not found')
    }
    
    // Parse the JSON file
    let importedSettings: any
    try {
      const fileContent = fileField.data.toString('utf-8')
      const parsedData = JSON.parse(fileContent)
      
      // Validate structure
      if (!parsedData.settings) {
        throw new Error('Invalid file format: missing "settings" key')
      }
      
      importedSettings = parsedData.settings
    } catch (parseError: any) {
      throw new Error(`Invalid JSON file: ${parseError.message}`)
    }
    
    // Validate required settings structure
    const requiredKeys = ['general', 'battery', 'notifications', 'model']
    for (const key of requiredKeys) {
      if (!importedSettings[key]) {
        throw new Error(`Missing required section: ${key}`)
      }
    }
    
    // Backup existing settings
    if (fs.existsSync(SETTINGS_FILE)) {
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-')
      const backupFile = path.join(BACKUP_DIR, `settings-backup-${timestamp}.json`)
      fs.copyFileSync(SETTINGS_FILE, backupFile)
    }
    
    // Save imported settings
    fs.writeFileSync(
      SETTINGS_FILE,
      JSON.stringify(importedSettings, null, 2)
    )
    
    return {
      success: true,
      message: 'Settings imported successfully',
      imported: {
        siteName: importedSettings.general?.siteName,
        timezone: importedSettings.general?.timezone,
        batteryCapacity: importedSettings.battery?.capacity,
        timestamp: new Date().toISOString()
      }
    }
  } catch (error: any) {
    throw createError({
      statusCode: 400,
      statusMessage: `Import failed: ${error.message}`
    })
  }
})
