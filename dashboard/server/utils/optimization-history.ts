import { Pool } from 'pg'

type OptimizationHistoryInsert = {
  timestamp: string
  predicted_action: number
  actual_action: number | null
  cost_baseline: number | null
  cost_rl: number | null
  battery_soc_start: number | null
  battery_soc_end: number | null
  solar_actual: number | null
  load_actual: number | null
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

function sanitizeDbIdentifier(value: string): string {
  return value.replace(/[^a-zA-Z0-9_]/g, '')
}

function resolveOptimizationDbConfig(): DbConfig {
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

  throw new Error('Unable to connect to PostgreSQL admin database to ensure optimization_history DB')
}

async function ensureSchema(optimizationPool: any): Promise<void> {
  await optimizationPool.query(`
    CREATE TABLE IF NOT EXISTS optimization_history (
      id SERIAL PRIMARY KEY,
      timestamp TIMESTAMP NOT NULL,
      predicted_action INTEGER NOT NULL,
      actual_action INTEGER,
      cost_baseline DOUBLE PRECISION,
      cost_rl DOUBLE PRECISION,
      battery_soc_start DOUBLE PRECISION,
      battery_soc_end DOUBLE PRECISION,
      solar_actual DOUBLE PRECISION,
      load_actual DOUBLE PRECISION,
      created_at TIMESTAMP DEFAULT NOW()
    )
  `)

  await optimizationPool.query(
    'CREATE INDEX IF NOT EXISTS idx_optimization_history_timestamp ON optimization_history(timestamp DESC)',
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

export async function persistOptimizationHistory(entry: OptimizationHistoryInsert): Promise<boolean> {
  const optimizationPool = await getOptimizationPool()
  if (!optimizationPool) {
    return false
  }

  try {
    await optimizationPool.query(
      `
      INSERT INTO optimization_history (
        timestamp,
        predicted_action,
        actual_action,
        cost_baseline,
        cost_rl,
        battery_soc_start,
        battery_soc_end,
        solar_actual,
        load_actual
      )
      VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
      `,
      [
        entry.timestamp,
        entry.predicted_action,
        entry.actual_action,
        entry.cost_baseline,
        entry.cost_rl,
        entry.battery_soc_start,
        entry.battery_soc_end,
        entry.solar_actual,
        entry.load_actual,
      ],
    )
    return true
  } catch (error) {
    console.warn('[optimization-history] Failed to persist row:', error)
    return false
  }
}
