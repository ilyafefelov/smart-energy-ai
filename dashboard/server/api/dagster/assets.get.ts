// API endpoint to get Dagster asset results from PostgreSQL
// Returns stored asset results for dashboard display

export default defineEventHandler(async (event) => {
  try {
    const { Pool } = await import('pg')
    
    const pool = new Pool({
      host: process.env.DB_HOST || 'localhost',
      port: parseInt(process.env.DB_PORT || '5432'),
      user: process.env.DB_USER || 'dagster',
      password: process.env.DB_PASSWORD || 'dagster',
      database: process.env.DB_NAME || 'dagster',
    })
    
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
    
    await pool.end()
    
    // Group by asset
    const assets = {}
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
  }
})
