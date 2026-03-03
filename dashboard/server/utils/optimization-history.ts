import { Pool } from 'pg'
import { createHash } from 'node:crypto'

export type OptimizationHistoryInsert = {
  execution_key: string
  command_id: string | null
  schedule_id: string | null
  execution_source: string
  timestamp: string
  predicted_action: number
  actual_action: number | null
  cost_baseline: number | null
  cost_rl: number | null
  price_uah_kwh: number | null
  duration_minutes: number | null
  energy_kwh: number | null
  economics_method: string | null
  economics_version: string | null
  fallback_reason: string | null
  price_source: string | null
  tariff_window: string | null
  interval_start: string | null
  interval_end: string | null
  battery_soc_start: number | null
  battery_soc_end: number | null
  solar_actual: number | null
  load_actual: number | null
  is_reconciled?: boolean
  reconciled_at?: string | null
  reconciliation_note?: string | null
}

export type PersistOptimizationHistoryResult = {
  ok: boolean
  inserted: boolean
  updated: boolean
  executionKey: string
  error?: string
}

type ExecutionKeyInput = {
  commandId: string | null
  scheduleId: string | null
  timestamp: string
  command: string
  powerKw: number
  durationMinutes: number | null
  userId: string
  reason: string
  source: string
}

type DbConfig = {
  host: string
  port: number
  user: string
  password: string
  database: string
}

let pool: any | null = null
let initPromise: Promise<any | null> | null = null

function normalizeNullableText(value: unknown): string | null {
  if (typeof value !== 'string') {
    return null
  }
  const normalized = value.trim()
  return normalized ? normalized : null
}

export function buildOptimizationExecutionKey(input: ExecutionKeyInput): string {
  const canonicalPayload = [
    normalizeNullableText(input.commandId) || '',
    normalizeNullableText(input.scheduleId) || '',
    input.timestamp,
    input.command,
    Number(input.powerKw).toFixed(6),
    input.durationMinutes == null ? '' : String(Math.round(input.durationMinutes)),
    input.userId,
    input.reason,
    input.source,
  ].join('|')

  const digest = createHash('sha256').update(canonicalPayload).digest('hex')
  return `exec_${digest.slice(0, 40)}`
}

function sanitizeDbIdentifier(value: string): string {
  return value.replace(/[^a-zA-Z0-9_]/g, '')
}

export function resolveOptimizationDbConfig(): DbConfig {
  const database = process.env.APP_DB_NAME || process.env.OPTIMIZATION_DB_NAME || 'smart_energy_ai'

  const databaseUrl = process.env.DATABASE_URL
  if (databaseUrl?.startsWith('postgres://') || databaseUrl?.startsWith('postgresql://')) {
    try {
      const parsed = new URL(databaseUrl)
      return {
        host: parsed.hostname || process.env.DB_HOST || 'localhost',
        port: Number(parsed.port || process.env.DB_PORT || 5432),
        user: decodeURIComponent(parsed.username || process.env.DB_USER || 'dagster'),
        password: decodeURIComponent(parsed.password || process.env.DB_PASSWORD || 'dagster'),
        database: sanitizeDbIdentifier(database),
      }
    } catch {
      // Fall through to env defaults.
    }
  }

  return {
    host: process.env.APP_DB_HOST || process.env.DB_HOST || 'localhost',
    port: Number(process.env.APP_DB_PORT || process.env.DB_PORT || 5432),
    user: process.env.APP_DB_USER || process.env.DB_USER || 'dagster',
    password: process.env.APP_DB_PASSWORD || process.env.DB_PASSWORD || 'dagster',
    database: sanitizeDbIdentifier(database),
  }
}

async function ensureDatabaseExists(config: DbConfig): Promise<void> {
  const adminDbs = ['postgres', 'dagster']

  for (const adminDb of adminDbs) {
    const adminPool = new Pool({
      host: config.host,
      port: config.port,
      user: config.user,
      password: config.password,
      database: adminDb,
    })

    try {
      const existsResult = await adminPool.query('SELECT 1 FROM pg_database WHERE datname = $1', [config.database])
      if (existsResult.rowCount === 0) {
        await adminPool.query(`CREATE DATABASE ${config.database}`)
      }
      return
    } catch {
      // Try the next admin DB target.
    } finally {
      await adminPool.end().catch(() => {})
    }
  }

  // Do not hard-fail here. In some environments admin DB access is restricted,
  // but the target application DB already exists and is reachable.
  console.warn('[optimization-history] Admin DB checks unavailable; will try target DB connection directly')
}

async function ensureSchema(optimizationPool: any): Promise<void> {
  await optimizationPool.query(`
    CREATE TABLE IF NOT EXISTS optimization_history (
      id SERIAL PRIMARY KEY,
      execution_key VARCHAR(64) NOT NULL,
      command_id VARCHAR(128),
      schedule_id VARCHAR(128),
      execution_source VARCHAR(64) NOT NULL DEFAULT 'unknown',
      timestamp TIMESTAMP NOT NULL,
      predicted_action INTEGER NOT NULL,
      actual_action INTEGER,
      cost_baseline DOUBLE PRECISION,
      cost_rl DOUBLE PRECISION,
      price_uah_kwh DOUBLE PRECISION,
      duration_minutes INTEGER,
      energy_kwh DOUBLE PRECISION,
      economics_method VARCHAR(64),
      economics_version VARCHAR(64),
      fallback_reason TEXT,
      price_source VARCHAR(64),
      tariff_window VARCHAR(32),
      interval_start TIMESTAMP,
      interval_end TIMESTAMP,
      battery_soc_start DOUBLE PRECISION,
      battery_soc_end DOUBLE PRECISION,
      solar_actual DOUBLE PRECISION,
      load_actual DOUBLE PRECISION,
      is_reconciled BOOLEAN NOT NULL DEFAULT FALSE,
      reconciled_at TIMESTAMP,
      reconciliation_note TEXT,
      created_at TIMESTAMP DEFAULT NOW(),
      updated_at TIMESTAMP DEFAULT NOW()
    )
  `)

  await optimizationPool.query(`ALTER TABLE optimization_history ADD COLUMN IF NOT EXISTS execution_key VARCHAR(64)`)
  await optimizationPool.query(`ALTER TABLE optimization_history ADD COLUMN IF NOT EXISTS command_id VARCHAR(128)`)
  await optimizationPool.query(`ALTER TABLE optimization_history ADD COLUMN IF NOT EXISTS schedule_id VARCHAR(128)`)
  await optimizationPool.query(`ALTER TABLE optimization_history ADD COLUMN IF NOT EXISTS execution_source VARCHAR(64)`)
  await optimizationPool.query(`ALTER TABLE optimization_history ALTER COLUMN execution_source SET DEFAULT 'unknown'`)
  await optimizationPool.query(`UPDATE optimization_history SET execution_source = 'unknown' WHERE execution_source IS NULL`)
  await optimizationPool.query(`ALTER TABLE optimization_history ALTER COLUMN execution_source SET NOT NULL`)
  await optimizationPool.query(`ALTER TABLE optimization_history ADD COLUMN IF NOT EXISTS price_uah_kwh DOUBLE PRECISION`)
  await optimizationPool.query(`ALTER TABLE optimization_history ADD COLUMN IF NOT EXISTS duration_minutes INTEGER`)
  await optimizationPool.query(`ALTER TABLE optimization_history ADD COLUMN IF NOT EXISTS energy_kwh DOUBLE PRECISION`)
  await optimizationPool.query(`ALTER TABLE optimization_history ADD COLUMN IF NOT EXISTS economics_method VARCHAR(64)`)
  await optimizationPool.query(`ALTER TABLE optimization_history ADD COLUMN IF NOT EXISTS economics_version VARCHAR(64)`)
  await optimizationPool.query(`ALTER TABLE optimization_history ADD COLUMN IF NOT EXISTS fallback_reason TEXT`)
  await optimizationPool.query(`ALTER TABLE optimization_history ADD COLUMN IF NOT EXISTS price_source VARCHAR(64)`)
  await optimizationPool.query(`ALTER TABLE optimization_history ADD COLUMN IF NOT EXISTS tariff_window VARCHAR(32)`)
  await optimizationPool.query(`ALTER TABLE optimization_history ADD COLUMN IF NOT EXISTS interval_start TIMESTAMP`)
  await optimizationPool.query(`ALTER TABLE optimization_history ADD COLUMN IF NOT EXISTS interval_end TIMESTAMP`)
  await optimizationPool.query(`ALTER TABLE optimization_history ADD COLUMN IF NOT EXISTS is_reconciled BOOLEAN NOT NULL DEFAULT FALSE`)
  await optimizationPool.query(`ALTER TABLE optimization_history ADD COLUMN IF NOT EXISTS reconciled_at TIMESTAMP`)
  await optimizationPool.query(`ALTER TABLE optimization_history ADD COLUMN IF NOT EXISTS reconciliation_note TEXT`)
  await optimizationPool.query(`ALTER TABLE optimization_history ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW()`)
  await optimizationPool.query(`
    UPDATE optimization_history
    SET execution_key = CONCAT(
      'legacy_',
      id,
      '_',
      TO_CHAR(COALESCE(timestamp, NOW()), 'YYYYMMDDHH24MISS')
    )
    WHERE execution_key IS NULL
  `)
  await optimizationPool.query(`ALTER TABLE optimization_history ALTER COLUMN execution_key SET NOT NULL`)

  await optimizationPool.query(
    'CREATE INDEX IF NOT EXISTS idx_optimization_history_timestamp ON optimization_history(timestamp DESC)',
  )
  await optimizationPool.query(
    'CREATE UNIQUE INDEX IF NOT EXISTS uq_optimization_history_execution_key ON optimization_history(execution_key)',
  )
  await optimizationPool.query(
    'CREATE INDEX IF NOT EXISTS idx_optimization_history_command_id ON optimization_history(command_id)',
  )
  await optimizationPool.query(
    'CREATE INDEX IF NOT EXISTS idx_optimization_history_schedule_id ON optimization_history(schedule_id)',
  )
}

async function getOptimizationPool(): Promise<any | null> {
  if (pool) {
    return pool
  }

  if (initPromise) {
    return initPromise
  }

  initPromise = (async () => {
    try {
      const config = resolveOptimizationDbConfig()
      await ensureDatabaseExists(config)

      const poolConfig = {
        host: config.host,
        port: config.port,
        user: config.user,
        password: config.password,
        database: config.database,
      }

      const createdPool = new Pool(poolConfig)
      await ensureSchema(createdPool)
      pool = createdPool
      return createdPool
    } catch (error) {
      console.warn('[optimization-history] Failed to initialize database pool:', error)
      return null
    } finally {
      initPromise = null
    }
  })()

  return initPromise
}

export async function persistOptimizationHistory(
  entry: OptimizationHistoryInsert,
): Promise<PersistOptimizationHistoryResult> {
  const optimizationPool = await getOptimizationPool()
  if (!optimizationPool) {
    return {
      ok: false,
      inserted: false,
      updated: false,
      executionKey: entry.execution_key,
      error: 'optimization pool unavailable',
    }
  }

  try {
    const result = await optimizationPool.query(
      `
      INSERT INTO optimization_history (
        execution_key,
        command_id,
        schedule_id,
        execution_source,
        timestamp,
        predicted_action,
        actual_action,
        cost_baseline,
        cost_rl,
        price_uah_kwh,
        duration_minutes,
        energy_kwh,
        economics_method,
        economics_version,
        fallback_reason,
        price_source,
        tariff_window,
        interval_start,
        interval_end,
        battery_soc_start,
        battery_soc_end,
        solar_actual,
        load_actual,
        is_reconciled,
        reconciled_at,
        reconciliation_note,
        updated_at
      )
      VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23, $24, $25, $26, NOW())
      ON CONFLICT (execution_key)
      DO UPDATE SET
        command_id = EXCLUDED.command_id,
        schedule_id = EXCLUDED.schedule_id,
        execution_source = EXCLUDED.execution_source,
        timestamp = EXCLUDED.timestamp,
        predicted_action = EXCLUDED.predicted_action,
        actual_action = EXCLUDED.actual_action,
        cost_baseline = EXCLUDED.cost_baseline,
        cost_rl = EXCLUDED.cost_rl,
        price_uah_kwh = EXCLUDED.price_uah_kwh,
        duration_minutes = EXCLUDED.duration_minutes,
        energy_kwh = EXCLUDED.energy_kwh,
        economics_method = EXCLUDED.economics_method,
        economics_version = EXCLUDED.economics_version,
        fallback_reason = EXCLUDED.fallback_reason,
        price_source = EXCLUDED.price_source,
        tariff_window = EXCLUDED.tariff_window,
        interval_start = EXCLUDED.interval_start,
        interval_end = EXCLUDED.interval_end,
        battery_soc_start = EXCLUDED.battery_soc_start,
        battery_soc_end = EXCLUDED.battery_soc_end,
        solar_actual = EXCLUDED.solar_actual,
        load_actual = EXCLUDED.load_actual,
        is_reconciled = EXCLUDED.is_reconciled,
        reconciled_at = EXCLUDED.reconciled_at,
        reconciliation_note = EXCLUDED.reconciliation_note,
        updated_at = NOW()
      RETURNING (xmax = 0) AS inserted
      `,
      [
        entry.execution_key,
        entry.command_id,
        entry.schedule_id,
        entry.execution_source,
        entry.timestamp,
        entry.predicted_action,
        entry.actual_action,
        entry.cost_baseline,
        entry.cost_rl,
        entry.price_uah_kwh,
        entry.duration_minutes,
        entry.energy_kwh,
        entry.economics_method,
        entry.economics_version,
        entry.fallback_reason,
        entry.price_source,
        entry.tariff_window,
        entry.interval_start,
        entry.interval_end,
        entry.battery_soc_start,
        entry.battery_soc_end,
        entry.solar_actual,
        entry.load_actual,
        entry.is_reconciled ?? false,
        entry.reconciled_at ?? null,
        entry.reconciliation_note ?? null,
      ],
    )
    const inserted = Boolean(result.rows?.[0]?.inserted)
    console.info('[optimization-history] persisted row', {
      execution_key: entry.execution_key,
      command_id: entry.command_id,
      schedule_id: entry.schedule_id,
      execution_source: entry.execution_source,
      inserted,
      updated: !inserted,
    })

    return {
      ok: true,
      inserted,
      updated: !inserted,
      executionKey: entry.execution_key,
    }
  } catch (error) {
    console.warn('[optimization-history] Failed to persist row:', error)
    return {
      ok: false,
      inserted: false,
      updated: false,
      executionKey: entry.execution_key,
      error: error instanceof Error ? error.message : String(error),
    }
  }
}
