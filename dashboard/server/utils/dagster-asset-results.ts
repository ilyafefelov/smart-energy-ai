type Queryable = {
  query: (sql: string, params?: unknown[]) => Promise<{ rowCount: number; rows?: Array<Record<string, any>> }>
}

type DagsterAssetResultsDbConfig = {
  host: string
  port: number
  user: string
  password: string
  database: string
}

const LEGACY_UNSCOPED_TENANT_ID = '__legacy_unscoped__'

export function normalizeDagsterTenantId(value: unknown): string | null {
  if (typeof value !== 'string') {
    return null
  }

  const normalized = value.trim().toLowerCase()
  return normalized || null
}

export function resolveDagsterAssetResultsDbConfig(): DagsterAssetResultsDbConfig {
  return {
    host: process.env.DB_HOST || 'localhost',
    port: Number(process.env.DB_PORT || 5432),
    user: process.env.DB_USER || 'dagster',
    password: process.env.DB_PASSWORD || 'dagster',
    database: process.env.DB_NAME || 'dagster',
  }
}

export async function ensureDagsterAssetResultsSchema(pool: Queryable): Promise<void> {
  await pool.query(`
    CREATE TABLE IF NOT EXISTS asset_results (
      id SERIAL PRIMARY KEY,
      asset_name VARCHAR(255) NOT NULL,
      run_id VARCHAR(255),
      tenant_id VARCHAR(128) NOT NULL,
      materialization_time TIMESTAMP DEFAULT NOW(),
      data JSONB,
      status VARCHAR(50) DEFAULT 'success',
      error_message TEXT,
      execution_time_ms INTEGER,
      UNIQUE(asset_name, run_id)
    )
  `)
  await pool.query('ALTER TABLE asset_results ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(128)')
  await pool.query(`
    UPDATE asset_results
    SET tenant_id = LOWER(BTRIM(data->>'tenant_id'))
    WHERE (tenant_id IS NULL OR BTRIM(tenant_id) = '')
      AND data IS NOT NULL
      AND NULLIF(BTRIM(data->>'tenant_id'), '') IS NOT NULL
  `)
  await pool.query(
    `
    UPDATE asset_results
    SET tenant_id = $1
    WHERE tenant_id IS NULL OR BTRIM(tenant_id) = ''
    `,
    [LEGACY_UNSCOPED_TENANT_ID],
  )
  await pool.query(`ALTER TABLE asset_results ALTER COLUMN tenant_id SET NOT NULL`)
  await pool.query('CREATE INDEX IF NOT EXISTS idx_asset_results_name ON asset_results(asset_name)')
  await pool.query('CREATE INDEX IF NOT EXISTS idx_asset_results_time ON asset_results(materialization_time DESC)')
  await pool.query('CREATE INDEX IF NOT EXISTS idx_asset_results_tenant_id ON asset_results(tenant_id)')
  await pool.query('CREATE INDEX IF NOT EXISTS idx_asset_results_tenant_asset_time ON asset_results(tenant_id, asset_name, materialization_time DESC)')
}

export async function dagsterAssetResultsTableExists(pool: Queryable): Promise<boolean> {
  const result = await pool.query(`SELECT to_regclass('public.asset_results') AS table_name`)
  return Boolean(result.rows?.[0]?.table_name)
}

export async function dagsterAssetResultsHasTenantColumn(pool: Queryable): Promise<boolean> {
  const result = await pool.query(
    `
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'asset_results'
      AND column_name = 'tenant_id'
      AND is_nullable = 'NO'
    LIMIT 1
    `,
  )

  return result.rowCount > 0
}

export function buildStrictDagsterTenantPredicate(): string {
  return `tenant_id = $1`
}