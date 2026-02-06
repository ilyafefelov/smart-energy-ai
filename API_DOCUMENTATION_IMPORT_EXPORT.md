# API DOCUMENTATION: SETTINGS IMPORT/EXPORT
**Version:** 1.0  
**Last Updated:** 2026-02-07  

---

## OVERVIEW

Two new API endpoints enable configuration backup, transfer, and sharing between dashboard instances.

---

## ENDPOINT 1: EXPORT SETTINGS

### Request
```
GET /api/settings/export
```

### Response (Success 200)
```json
{
  "metadata": {
    "exported": "2026-02-07T01:30:00.000Z",
    "version": "1.0",
    "siteName": "Factory #1",
    "timestamp": 1707255000000
  },
  "settings": {
    "general": {
      "siteName": "Factory #1",
      "timezone": "Europe/Kiev (GMT+2)",
      "currency": "UAH",
      "notificationsEnabled": true
    },
    "battery": {
      "capacity": 150,
      "minSOC": 15,
      "maxChargeRate": 50,
      "maxDischargeRate": 50
    },
    "notifications": {
      "highPrice": true,
      "highPriceThreshold": 13.0,
      "lowPrice": true,
      "lowPriceThreshold": 7.0,
      "modelComplete": true,
      "systemAlerts": true
    },
    "model": {
      "learningRate": 0.0003,
      "batchSize": 64,
      "epochs": 20
    }
  }
}
```

### Response Headers (Download)
```
Content-Type: application/json
Content-Disposition: attachment; filename="settings-factory-1-2026-02-07.json"
```

### Error Response (500)
```json
{
  "statusCode": 500,
  "statusMessage": "Failed to export settings: [error details]"
}
```

### Usage Example
```typescript
// In Vue component
const exportSettings = async () => {
  const response = await $fetch('/api/settings/export')
  const blob = new Blob([JSON.stringify(response, null, 2)], { type: 'application/json' })
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = 'settings-export.json'
  link.click()
  window.URL.revokeObjectURL(url)
}
```

---

## ENDPOINT 2: IMPORT SETTINGS

### Request
```
POST /api/settings/import
Content-Type: multipart/form-data

Body:
- file: <JSON file with { metadata, settings }>
```

### Request Body Example
```json
{
  "metadata": {
    "exported": "2026-02-07T01:30:00.000Z",
    "version": "1.0",
    "siteName": "Factory #1",
    "timestamp": 1707255000000
  },
  "settings": {
    "general": { ... },
    "battery": { ... },
    "notifications": { ... },
    "model": { ... }
  }
}
```

### Response (Success 200)
```json
{
  "success": true,
  "message": "Settings imported successfully",
  "imported": {
    "siteName": "Factory #1",
    "timezone": "Europe/Kiev (GMT+2)",
    "batteryCapacity": 150,
    "timestamp": "2026-02-07T01:30:00.000Z"
  }
}
```

### Error Response (400)
```json
{
  "statusCode": 400,
  "statusMessage": "Import failed: [error details]"
}
```

### Possible Errors
```
"No file provided"
"File field not found"
"Invalid JSON file: [parse error]"
"Invalid file format: missing 'settings' key"
"Missing required section: general"
"Missing required section: battery"
"Missing required section: notifications"
"Missing required section: model"
```

### Usage Example
```typescript
// In Vue component
const handleFileImport = async (event: Event) => {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  
  const formData = new FormData()
  formData.append('file', file)
  
  try {
    const result = await $fetch('/api/settings/import', {
      method: 'POST',
      body: formData
    })
    
    console.log(`Imported from: ${result.imported.siteName}`)
    // Update local settings...
  } catch (error) {
    console.error(`Import failed: ${error.message}`)
  }
}
```

---

## VALIDATION RULES

### Export
- No validation required
- Falls back to defaults if file missing
- Always returns valid structure

### Import
- **File format:** Must be valid JSON
- **Root structure:** Must have `settings` key
- **Required sections:** general, battery, notifications, model
- **Backup:** Original settings backed up before save
- **File storage:** Backups in `data/backups/` with timestamp

### Schema Validation
```
settings.general: { siteName, timezone, currency, notificationsEnabled }
settings.battery: { capacity, minSOC, maxChargeRate, maxDischargeRate }
settings.notifications: { highPrice, highPriceThreshold, lowPrice, lowPriceThreshold, modelComplete, systemAlerts }
settings.model: { learningRate, batchSize, epochs }
```

---

## BACKUP STRATEGY

On successful import:
1. Original `data/settings.json` copied to `data/backups/`
2. Backup filename: `settings-backup-YYYY-MM-DDTHH-mm-ss-SSSZ.json`
3. Imported settings saved to `data/settings.json`

### Example Backup Directory
```
data/backups/
├── settings-backup-2026-02-07T01-25-00-000Z.json
├── settings-backup-2026-02-07T01-30-00-000Z.json
└── settings-backup-2026-02-07T01-35-00-000Z.json
```

---

## CLIENT IMPLEMENTATION

### Vue Component Integration

```vue
<script setup>
import { ref } from 'vue'

const fileInput = ref()
const isExporting = ref(false)
const isImporting = ref(false)

// Export handler
const exportSettings = async () => {
  isExporting.value = true
  try {
    const response = await $fetch('/api/settings/export')
    const blob = new Blob([JSON.stringify(response, null, 2)], { type: 'application/json' })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    const siteName = response.metadata.siteName.toLowerCase().replace(/\s+/g, '-')
    const dateStr = new Date().toISOString().split('T')[0]
    link.download = `settings-${siteName}-${dateStr}.json`
    link.href = url
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
  } finally {
    isExporting.value = false
  }
}

// Import handler
const handleFileImport = async (event) => {
  const file = event.target.files[0]
  if (!file) return
  
  isImporting.value = true
  try {
    const formData = new FormData()
    formData.append('file', file)
    
    const result = await $fetch('/api/settings/import', {
      method: 'POST',
      body: formData
    })
    
    console.log('Import successful:', result)
    // Update local settings from file content...
  } finally {
    isImporting.value = false
  }
}
</script>

<template>
  <button @click="exportSettings" :disabled="isExporting">
    {{ isExporting ? 'Exporting...' : 'Export Config' }}
  </button>
  
  <input ref="fileInput" type="file" accept=".json" @change="handleFileImport" />
  <button @click="$refs.fileInput.click()" :disabled="isImporting">
    {{ isImporting ? 'Importing...' : 'Import Config' }}
  </button>
</template>
```

---

## USE CASES

### 1. Backup & Recovery
```
Scenario: User wants to backup current configuration
1. Click "📤 Export Config"
2. Receives: settings-factory-1-2026-02-07.json
3. Store safely (cloud, USB, etc.)
4. Recover: Upload file via "📥 Import Config"
```

### 2. Multi-Site Replication
```
Scenario: Deploy same config to 5 factories
1. Configure Factory #1 perfectly
2. Export config
3. On each Factory #2-5:
   - Import the exported file
   - Modify siteName if needed
   - Save changes
Result: 5 factories with identical settings
```

### 3. Configuration Versioning
```
Scenario: Track configuration history
1. Export before each major change
2. Backups auto-created on import
3. Easy rollback to previous version
4. Archive exports for compliance
```

### 4. Team Collaboration
```
Scenario: Share optimized settings with other operators
1. Create optimized settings in your instance
2. Export config
3. Share file via email/Slack
4. Team members import in their instances
5. Standardized operations across team
```

---

## SECURITY CONSIDERATIONS

✅ **Implemented:**
- Multipart form validation
- File existence checks
- JSON schema validation
- Backup of original data
- Error message sanitization

⚠️ **Recommendations:**
- Store backup directory outside web root
- Implement size limit on imports
- Log import/export operations
- Consider AES encryption for sensitive configs
- Restrict API access to authenticated users only

---

## TESTING

```bash
# Test export
curl http://localhost:3000/api/settings/export > test-export.json

# Test import
curl -F "file=@test-export.json" http://localhost:3000/api/settings/import
```

---

## TROUBLESHOOTING

| Issue | Solution |
|-------|----------|
| "No file provided" | Ensure file input is selected |
| "Invalid JSON file" | Verify JSON syntax (use JSONLint) |
| "Missing required section" | Check all 4 main keys present |
| Import doesn't update UI | Refresh page after import |
| Backup not created | Check `data/` directory permissions |
| Download doesn't start | Check browser's download settings |

---

## FUTURE ENHANCEMENTS

- [ ] Encryption for exported files
- [ ] Cloud backup integration
- [ ] Version history with git-like diffs
- [ ] Settings merge (not just replace)
- [ ] Selective import (choose which sections)
- [ ] Batch operations (import multiple files)
- [ ] API key protection
- [ ] Audit logging
