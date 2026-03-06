// Python Script Runner Utility for Server APIs
import { exec } from 'child_process'
import { promisify } from 'util'
import path from 'path'
import { fileURLToPath } from 'url'
import { existsSync } from 'fs'

const execAsync = promisify(exec)

// Resolve the project root (nuxt_dashboard/../ = smart-energy-ai root)
const __dirname = path.dirname(fileURLToPath(import.meta.url))
const PROJECT_ROOT = path.resolve(__dirname, '../../../')

// Map script name to actual file
const SCRIPT_MAP = {
  'ml_integration': path.join(PROJECT_ROOT, 'ml_integration_api.py')
}


export async function execPython(scriptName, args = []) {
  const scriptPath = SCRIPT_MAP[scriptName]
  if (!scriptPath) {
    throw new Error(`Unknown script: ${scriptName}`)
  }

  // Prefer venv python if it exists, fall back to system python
  const venvPy = process.platform === 'win32'
    ? path.join(PROJECT_ROOT, 'venv', 'Scripts', 'python.exe')
    : path.join(PROJECT_ROOT, 'venv', 'bin', 'python')
  const pyExe = existsSync(venvPy) ? venvPy : 'python'

  const argsString = args.map(a => `"${a}"`).join(' ')
  const command = `"${pyExe}" "${scriptPath}" ${argsString}`

  const { stdout, stderr } = await execAsync(command, {
    cwd: PROJECT_ROOT,
    timeout: 30000,
    env: { ...process.env, PYTHONPATH: PROJECT_ROOT }
  })

  if (stderr && !stdout) {
    throw new Error(`Python stderr: ${stderr}`)
  }

  return stdout.trim()
}