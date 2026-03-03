// Python Script Runner Utility for Server APIs
import { execFile } from 'child_process'
import { existsSync } from 'fs'
import { promisify } from 'util'
import path from 'path'

const execFileAsync = promisify(execFile)

function resolvePythonEnvPath() {
  const cwd = process.cwd()
  const candidates = [
    path.resolve(cwd, 'energy_ml'),
    path.resolve(cwd, '..', 'energy_ml'),
  ]

  for (const candidate of candidates) {
    if (existsSync(candidate)) {
      return candidate
    }
  }

  return candidates[0]
}

function normalizeArgName(key) {
  return `--${String(key).replace(/_/g, '-')}`
}

function toArgv(args) {
  if (Array.isArray(args)) {
    return args.map((value) => String(value))
  }

  if (args && typeof args === 'object') {
    const argv = []
    for (const [key, rawValue] of Object.entries(args)) {
      if (rawValue === undefined || rawValue === null || rawValue === '') {
        continue
      }

      const flag = normalizeArgName(key)
      if (rawValue === true) {
        argv.push(flag)
        continue
      }
      if (rawValue === false) {
        continue
      }

      if (Array.isArray(rawValue)) {
        for (const value of rawValue) {
          if (value === undefined || value === null || value === '') {
            continue
          }
          argv.push(flag, String(value))
        }
        continue
      }

      argv.push(flag, String(rawValue))
    }
    return argv
  }

  if (args === undefined || args === null) {
    return []
  }

  return [String(args)]
}

function resolvePythonExecutable() {
  return process.env.PYTHON_EXECUTABLE || process.env.PYTHON || 'python'
}

export function getPythonScriptPath(scriptName) {
  const pythonEnvPath = resolvePythonEnvPath()
  return path.join(pythonEnvPath, 'scripts', scriptName)
}

export function hasPythonScript(scriptName) {
  return existsSync(getPythonScriptPath(scriptName))
}

export async function execPython(scriptName, args = []) {
  const pythonEnvPath = resolvePythonEnvPath()
  const scriptPath = getPythonScriptPath(scriptName)

  if (!existsSync(scriptPath)) {
    throw new Error(`Python script not found: ${scriptName}`)
  }

  const argv = [scriptPath, ...toArgv(args)]
  const pythonExecutable = resolvePythonExecutable()
  
  try {
    const { stdout } = await execFileAsync(pythonExecutable, argv, {
      cwd: pythonEnvPath,
      timeout: 30000,
      env: { ...process.env, PYTHONPATH: pythonEnvPath }
    })
    
    return stdout.trim()
  } catch (error) {
    throw new Error(`Python execution failed: ${error.message}`)
  }
}