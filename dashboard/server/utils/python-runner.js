// Python Script Runner Utility for Server APIs
import { exec } from 'child_process'
import { promisify } from 'util'
import path from 'path'

const execAsync = promisify(exec)

export async function execPython(scriptName, args = []) {
  const pythonEnvPath = path.resolve('./../../energy_ml')
  const scriptPath = path.join(pythonEnvPath, 'scripts', scriptName)
  const argsString = args.join(' ')
  const command = `python "${scriptPath}" ${argsString}`
  
  try {
    const { stdout, stderr } = await execAsync(command, {
      cwd: pythonEnvPath,
      timeout: 30000,
      env: { ...process.env, PYTHONPATH: pythonEnvPath }
    })
    
    return stdout.trim()
  } catch (error) {
    throw new Error(`Python execution failed: ${error.message}`)
  }
}