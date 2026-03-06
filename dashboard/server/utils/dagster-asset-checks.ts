import { execFile } from 'child_process'
import { existsSync } from 'fs'
import path from 'path'
import { promisify } from 'util'

const execFileAsync = promisify(execFile)

export type DagsterAssetCheckStatus = 'healthy' | 'warning' | 'degraded' | 'unknown' | 'not_applicable'

export type DagsterAssetCheckSummary = {
  overall_status: DagsterAssetCheckStatus
  total_checks: number
  passed_checks: number
  failed_checks: number
  warning_checks: number
  not_run_checks: number
  planned_checks: number
  latest_evaluated_at: string | null
  failing_check_names: string[]
  unevaluated_check_names: string[]
}

export type DagsterAssetCheckEntry = {
  asset_name: string
  check_name: string
  status: 'passed' | 'failed' | 'warning' | 'not_run' | 'planned'
  execution_status: string | null
  severity: string | null
  run_id: string | null
  timestamp: string | null
  description: string | null
  metadata: Record<string, unknown>
}

export type DagsterAssetCheckAsset = {
  asset_name: string
  summary: DagsterAssetCheckSummary
  checks: DagsterAssetCheckEntry[]
}

export type DagsterAssetChecksResponse = {
  success: boolean
  generated_at?: string
  dagster_home?: string
  summary: DagsterAssetCheckSummary
  assets: DagsterAssetCheckAsset[]
  checks: DagsterAssetCheckEntry[]
  error?: string
}

const EMPTY_SUMMARY: DagsterAssetCheckSummary = {
  overall_status: 'unknown',
  total_checks: 0,
  passed_checks: 0,
  failed_checks: 0,
  warning_checks: 0,
  not_run_checks: 0,
  planned_checks: 0,
  latest_evaluated_at: null,
  failing_check_names: [],
  unevaluated_check_names: [],
}

function resolveProjectRoot(projectRoot?: string) {
  if (projectRoot) return projectRoot
  return path.resolve(process.cwd(), '..')
}

function resolvePythonExecutable(projectRoot: string) {
  const venvPython = path.join(projectRoot, '.venv', 'Scripts', 'python.exe')
  if (existsSync(venvPython)) {
    return venvPython
  }
  return process.env.PYTHON_EXECUTABLE || process.env.PYTHON || 'python'
}

function parseJsonFromStdout(stdout: string) {
  const trimmed = stdout.trim()
  if (!trimmed) {
    throw new Error('Empty response from Dagster asset check reader')
  }

  try {
    return JSON.parse(trimmed)
  } catch {
    const lines = trimmed.split(/\r?\n/).reverse()
    for (const line of lines) {
      try {
        return JSON.parse(line)
      } catch {
        continue
      }
    }
  }

  throw new Error('Unable to parse Dagster asset check JSON response')
}

export async function readDagsterAssetChecks(projectRoot?: string): Promise<DagsterAssetChecksResponse> {
  const root = resolveProjectRoot(projectRoot)
  const scriptPath = path.join(root, 'scripts', 'read_dagster_asset_checks.py')
  if (!existsSync(scriptPath)) {
    return {
      success: false,
      error: `Dagster asset check reader script not found at ${scriptPath}`,
      summary: EMPTY_SUMMARY,
      assets: [],
      checks: [],
    }
  }

  try {
    const { stdout } = await execFileAsync(
      resolvePythonExecutable(root),
      [scriptPath, '--project-root', root],
      {
        cwd: root,
        timeout: 30000,
        env: {
          ...process.env,
          DAGSTER_HOME: path.join(root, 'data', 'dagster_home'),
        },
      },
    )

    const payload = parseJsonFromStdout(stdout) as DagsterAssetChecksResponse
    if (!payload.summary) {
      payload.summary = EMPTY_SUMMARY
    }
    if (!Array.isArray(payload.assets)) {
      payload.assets = []
    }
    if (!Array.isArray(payload.checks)) {
      payload.checks = []
    }
    return payload
  } catch (error: any) {
    return {
      success: false,
      error: error?.message || 'Failed to read Dagster asset checks',
      summary: EMPTY_SUMMARY,
      assets: [],
      checks: [],
    }
  }
}