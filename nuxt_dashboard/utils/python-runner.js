// Python Script Runner Utility for Dashboard APIs
// Executes Python scripts from the energy_ml directory

import { exec } from 'child_process'
import { promisify } from 'util'
import path from 'path'
import { fileURLToPath } from 'url'

const execAsync = promisify(exec)
const __dirname = path.dirname(fileURLToPath(import.meta.url))

// Path to the Python environment and scripts
const PYTHON_ENV_PATH = path.join(__dirname, '../../energy_ml')
const PYTHON_SCRIPTS_PATH = path.join(PYTHON_ENV_PATH, 'scripts')

/**
 * Execute a Python script with optional arguments
 * @param {string} scriptName - Name of the Python script (e.g., 'get_battery_physics.py')
 * @param {Array<string>} args - Command line arguments for the script
 * @param {Object} options - Execution options
 * @returns {Promise<string>} - Stdout from the Python script
 */
export async function execPython(scriptName, args = [], options = {}) {
  const {
    timeout = 30000, // 30 second default timeout
    cwd = PYTHON_ENV_PATH,
    encoding = 'utf8'
  } = options

  try {
    // Build the command
    const scriptPath = path.join(PYTHON_SCRIPTS_PATH, scriptName)
    const argsString = args.map(arg => `"${arg}"`).join(' ')
    const command = `python "${scriptPath}" ${argsString}`
    
    console.log(`[Python Runner] Executing: ${command}`)
    console.log(`[Python Runner] Working directory: ${cwd}`)
    
    // Execute the Python script
    const { stdout, stderr } = await execAsync(command, {
      cwd,
      timeout,
      encoding,
      env: {
        ...process.env,
        PYTHONPATH: PYTHON_ENV_PATH,
        PYTHONUNBUFFERED: '1'
      }
    })
    
    if (stderr && stderr.trim()) {
      console.warn(`[Python Runner] Warning from ${scriptName}:`, stderr.trim())
    }
    
    if (!stdout || !stdout.trim()) {
      throw new Error(`No output from Python script: ${scriptName}`)
    }
    
    console.log(`[Python Runner] Success: ${scriptName} completed`)
    return stdout.trim()
    
  } catch (error) {
    console.error(`[Python Runner] Error executing ${scriptName}:`, {
      message: error.message,
      code: error.code,
      signal: error.signal,
      cmd: error.cmd
    })
    
    // Re-throw with more context
    throw new Error(`Python script execution failed: ${scriptName} - ${error.message}`)
  }
}

/**
 * Execute Python code directly (for small snippets)
 * @param {string} code - Python code to execute
 * @param {Object} options - Execution options
 * @returns {Promise<string>} - Output from the Python code
 */
export async function execPythonCode(code, options = {}) {
  const {
    timeout = 10000,
    cwd = PYTHON_ENV_PATH
  } = options

  try {
    const command = `python -c "${code.replace(/"/g, '\\"')}"`
    
    console.log(`[Python Runner] Executing code: ${code.substring(0, 100)}...`)
    
    const { stdout, stderr } = await execAsync(command, {
      cwd,
      timeout,
      env: {
        ...process.env,
        PYTHONPATH: PYTHON_ENV_PATH,
        PYTHONUNBUFFERED: '1'
      }
    })
    
    if (stderr && stderr.trim()) {
      console.warn(`[Python Runner] Warning from inline code:`, stderr.trim())
    }
    
    return stdout.trim()
    
  } catch (error) {
    console.error(`[Python Runner] Error executing Python code:`, error.message)
    throw new Error(`Python code execution failed: ${error.message}`)
  }
}

/**
 * Test Python environment availability
 * @returns {Promise<Object>} - Environment info
 */
export async function testPythonEnvironment() {
  try {
    const pythonVersion = await execPythonCode('import sys; print(sys.version)')
    const availableModules = await execPythonCode(`
import pkgutil
modules = [name for importer, name, ispkg in pkgutil.iter_modules()]
energy_modules = [m for m in modules if 'energy' in m.lower()]
print('|'.join(energy_modules[:10]))  # First 10 energy-related modules
    `)
    
    return {
      available: true,
      python_version: pythonVersion,
      energy_modules: availableModules.split('|').filter(m => m.trim()),
      env_path: PYTHON_ENV_PATH,
      scripts_path: PYTHON_SCRIPTS_PATH
    }
    
  } catch (error) {
    return {
      available: false,
      error: error.message,
      env_path: PYTHON_ENV_PATH,
      scripts_path: PYTHON_SCRIPTS_PATH
    }
  }
}

// Default export for convenience
export default execPython