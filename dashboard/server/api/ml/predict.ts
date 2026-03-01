/**
 * Server API endpoint for ML model predictions and optimization
 * Integrates with energy_ml ML pipeline via Python subprocess
 */

import { exec } from 'child_process'
import { promisify } from 'util'
import { resolve, dirname } from 'path'
import { fileURLToPath } from 'url'

const execAsync = promisify(exec)

// Get __dirname equivalent in ESM
const getDirname = (importMetaUrl: string) => {
  return dirname(fileURLToPath(importMetaUrl))
}

export default defineEventHandler(async (event) => {
  const method = getMethod(event)
  
  if (method === 'POST') {
    const body = await readBody(event)
    const { strategy = 'balanced', battery_soc = 50, price = 14.26 } = body
    
    try {
      // Get project root - go up from dashboard/server/api/ml/
      const projectRoot = resolve(process.cwd(), '..')
      const pythonScript = resolve(projectRoot, 'energy_ml/ml_integration_api.py')
      
      console.log('[predict] Project root:', projectRoot)
      console.log('[predict] Python script:', pythonScript)
      
      // Call the Python ML integration API
      const pythonCmd = `python "${pythonScript}" recommendation --strategy ${strategy} --battery-soc ${battery_soc} --price ${price}`
      
      let pythonResult = null
      let pythonError = null
      
      try {
        const { stdout, stderr } = await execAsync(pythonCmd, { 
          timeout: 30000,
          maxBuffer: 10 * 1024 * 1024,
          cwd: projectRoot
        })
        pythonResult = stdout
        pythonError = stderr
      } catch (execError: any) {
        console.warn('[predict] Python subprocess failed:', execError.message)
        pythonError = execError.message
      }
      
      // Try to parse Python output
      let recommendation = null
      if (pythonResult) {
        try {
          recommendation = JSON.parse(pythonResult.trim())
        } catch (parseError) {
          console.warn('[predict] Failed to parse Python output:', pythonResult.substring(0, 200))
        }
      }
      
      // If we got valid recommendation from Python, use it
      if (recommendation && recommendation.action) {
        return {
          status: 'success',
          timestamp: new Date().toISOString(),
          recommendation: {
            action: recommendation.action,
            confidence: recommendation.confidence || 0.75,
            rationale: recommendation.rationale || 'From ML model'
          },
          model_info: {
            strategy,
            version: recommendation.version || '1.0.0',
            source: 'energy_ml/ml_integration_api.py',
            python_error: pythonError
          },
          raw_output: recommendation
        }
      }
      
      // Fallback: use simple heuristic if Python fails
      let action = 'HOLD'
      let confidence = 0.75
      let rationale = 'Moderate price, no action needed'
      
      if (price < 12 && battery_soc < 90) {
        action = 'BUY'
        confidence = 0.85
        rationale = 'Low price, battery has capacity'
      } else if (price > 16 && battery_soc > 30) {
        action = 'SELL'
        confidence = 0.88
        rationale = 'High price, selling from battery'
      } else if (price > 18 && battery_soc > 50) {
        action = 'DISCHARGE'
        confidence = 0.82
        rationale = 'Peak price, discharging battery'
      }
      
      return {
        status: 'success',
        timestamp: new Date().toISOString(),
        recommendation: {
          action,
          confidence,
          rationale
        },
        model_info: {
          strategy,
          version: '1.0.0',
          source: 'fallback_heuristic',
          python_error: pythonError
        }
      }
      
    } catch (error: any) {
      console.error('[predict] Error:', error)
      return {
        status: 'error',
        error: error.message,
        fallback: {
          action: 'HOLD',
          confidence: 0.5
        }
      }
    }
  }
  
  // GET request - return API info
  return {
    status: 'ok',
    message: 'ML Prediction API',
    usage: 'POST with { strategy, battery_soc, price }',
    available_strategies: ['max_earn', 'max_battery_health', 'max_charge', 'balanced'],
    example: {
      strategy: 'balanced',
      battery_soc: 50,
      price: 14.26
    }
  }
})
