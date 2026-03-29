import { existsSync } from 'fs'
import { appendFile, mkdir, readFile } from 'fs/promises'
import path from 'path'

export type MlflowDiagnosticEvent = {
  timestamp: string
  service_role: 'runtime_diagnostic_capture'
  tracking_mode: 'diagnostic_only'
  event_kind: 'runtime_metric_capture'
  run_id: string
  action: string | null
  confidence: number | null
  actual_price: number | null
  predicted_profit: number | null
  actual_profit: number | null
  metrics: Record<string, unknown>
  params: Record<string, unknown>
  model_version: string | null
  environment: string
}

type DiagnosticFileReadResult = {
  filePath: string
  relativePath: string
  events: MlflowDiagnosticEvent[]
}

function toRelativePath(projectRoot: string, absolutePath: string): string {
  return path.relative(projectRoot, absolutePath).replace(/\\/g, '/')
}

export function resolveMlflowDiagnosticsFilePath(projectRoot: string, timestampIso: string): string {
  const dayStamp = timestampIso.slice(0, 10)
  return path.join(projectRoot, 'dashboard', 'data', 'mlflow-diagnostics', `runtime-events-${dayStamp}.jsonl`)
}

export async function appendMlflowDiagnosticEvent(projectRoot: string, event: MlflowDiagnosticEvent): Promise<{ filePath: string; relativePath: string }> {
  const filePath = resolveMlflowDiagnosticsFilePath(projectRoot, event.timestamp)
  await mkdir(path.dirname(filePath), { recursive: true })
  await appendFile(filePath, `${JSON.stringify(event)}\n`, 'utf-8')

  return {
    filePath,
    relativePath: toRelativePath(projectRoot, filePath),
  }
}

export async function readMlflowDiagnosticEvents(projectRoot: string, timestampIso: string): Promise<DiagnosticFileReadResult> {
  const filePath = resolveMlflowDiagnosticsFilePath(projectRoot, timestampIso)
  const relativePath = toRelativePath(projectRoot, filePath)

  if (!existsSync(filePath)) {
    return {
      filePath,
      relativePath,
      events: [],
    }
  }

  const content = await readFile(filePath, 'utf-8')
  const events = content
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .flatMap((line) => {
      try {
        const parsed = JSON.parse(line) as MlflowDiagnosticEvent
        return [parsed]
      } catch {
        return []
      }
    })

  return {
    filePath,
    relativePath,
    events,
  }
}