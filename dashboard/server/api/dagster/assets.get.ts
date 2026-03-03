// API endpoint to get Dagster asset results from PostgreSQL
// Returns stored asset results for dashboard display

export default defineEventHandler(async (event) => {
  let pool: any = null

  try {
    const { Pool } = await import('pg')

    pool = new Pool({
      host: process.env.DB_HOST || 'localhost',
      port: parseInt(process.env.DB_PORT || '5432'),
      user: process.env.DB_USER || 'dagster',
      password: process.env.DB_PASSWORD || 'dagster',
      database: process.env.DB_NAME || 'dagster',
    })

    // Keep schema creation aligned with src/dagster_api/database.py.
    await pool.query(`
      CREATE TABLE IF NOT EXISTS asset_results (
        id SERIAL PRIMARY KEY,
        asset_name VARCHAR(255) NOT NULL,
        run_id VARCHAR(255),
        materialization_time TIMESTAMP DEFAULT NOW(),
        data JSONB,
        status VARCHAR(50) DEFAULT 'success',
        error_message TEXT,
        execution_time_ms INTEGER,
        UNIQUE(asset_name, run_id)
      )
    `)
    await pool.query('CREATE INDEX IF NOT EXISTS idx_asset_results_name ON asset_results(asset_name)')
    await pool.query('CREATE INDEX IF NOT EXISTS idx_asset_results_time ON asset_results(materialization_time DESC)')

    const result = await pool.query(`
      SELECT 
        asset_name,
        run_id,
        materialization_time,
        status,
        execution_time_ms,
        error_message
      FROM asset_results
      ORDER BY materialization_time DESC
      LIMIT 50
    `)

    // Group by asset
    const assets: Record<string, {
      name: string
      last_run: string
      status: string
      execution_time_ms: number | null
      runs: Array<{ run_id: string; time: string; status: string; error: string | null }>
    }> = {}

    for (const row of result.rows) {
      if (!assets[row.asset_name]) {
        assets[row.asset_name] = {
          name: row.asset_name,
          last_run: row.materialization_time,
          status: row.status,
          execution_time_ms: row.execution_time_ms,
          runs: []
        }
      }

      assets[row.asset_name].runs.push({
        run_id: row.run_id,
        time: row.materialization_time,
        status: row.status,
        error: row.error_message
      })
    }
    
    return {
      success: true,
      timestamp: new Date().toISOString(),
      assets: Object.values(assets),
      total_assets: Object.keys(assets).length
    }
  } catch (error) {
    console.error('[dagster/assets] Error:', error)
    return {
      success: false,
      error: error.message
    }
  } finally {
    if (pool) {
      await pool.end().catch(() => {})
    }
  }
})
