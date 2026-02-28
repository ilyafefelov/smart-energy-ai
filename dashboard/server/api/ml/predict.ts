/**
 * Server API endpoint for ML model predictions and optimization
 * Integrates with Phase 1-3 MLOps infrastructure
 */

import { BatteryPhysicsEngine, OptimizationEngine, OptimizationStrategy } from '../../energy_ml/mlops'

// Initialize ML components (would normally be done at server startup)
let physicsEngine: BatteryPhysicsEngine
let optimizationEngines: Record<string, OptimizationEngine> = {}

// Initialize physics and optimization engines
function initializeMLComponents() {
  if (!physicsEngine) {
    physicsEngine = new BatteryPhysicsEngine('LFP')
    
    // Initialize optimization engines for each strategy
    const strategies = ['max_earn', 'max_battery_health', 'max_charge', 'balanced']
    
    strategies.forEach(strategy => {
      const engine = new OptimizationEngine(physicsEngine, strategy as OptimizationStrategy)
      optimizationEngines[strategy] = engine
    })
  }
}

export default defineEventHandler(async (event) => {
  const method = getMethod(event)
  
  if (method === 'POST') {
    try {
      initializeMLComponents()
      
      const body = await readBody(event)
      const {
        user_id = 'dashboard_user',
        battery_soc = 0.6,
        grid_price_uah_kwh = 10.0,
        solar_generation_kw = 0.0,
        wind_generation_kw = 0.0,
        load_demand_kw = 3.0,
        temperature_celsius = 25.0,
        strategy = 'balanced'
      } = body
      
      // Validate inputs
      if (battery_soc < 0 || battery_soc > 1) {
        throw createError({
          statusCode: 400,
          statusMessage: 'Battery SOC must be between 0 and 1'
        })
      }
      
      if (!optimizationEngines[strategy]) {
        throw createError({
          statusCode: 400,
          statusMessage: `Invalid strategy: ${strategy}. Use one of: ${Object.keys(optimizationEngines).join(', ')}`
        })
      }
      
      // Get optimization engine for requested strategy
      const optimizer = optimizationEngines[strategy]
      
      // Make optimization decision using ML pipeline
      const decision = await optimizer.optimize_decision({
        grid_price_uah_kwh,
        load_demand_kw,
        solar_generation_kw,
        wind_generation_kw,
        temperature: temperature_celsius
      })
      
      // Generate prediction ID and timestamp
      const prediction_id = `pred_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
      const timestamp = new Date().toISOString()
      
      // Simulate model version (in production this would come from model registry)
      const model_version = `energy_optimizer_v${new Date().toISOString().split('T')[0].replace(/-/g, '')}`
      
      // Return prediction response matching the MLOps API format
      return {
        action: decision.action,
        power_kw: decision.power_kw,
        duration_h: decision.duration_h,
        confidence: decision.confidence,
        expected_profit_uah: decision.expected_profit_uah,
        health_impact_percent: decision.health_impact_percent,
        reasoning: decision.reasoning,
        strategy_used: decision.strategy_used,
        prediction_id,
        timestamp,
        model_version,
        
        // Additional context for dashboard
        physics_constraints: decision.physics_constraints,
        battery_state: {
          soc_percent: battery_soc * 100,
          temperature_celsius,
          estimated_cycles_remaining: decision.physics_constraints?.estimated_remaining_cycles || 2000
        },
        market_context: {
          grid_price_uah_kwh,
          net_load_kw: Math.max(0, load_demand_kw - solar_generation_kw - wind_generation_kw),
          renewable_generation_kw: solar_generation_kw + wind_generation_kw
        }
      }
      
    } catch (error) {
      console.error('ML prediction error:', error)
      
      throw createError({
        statusCode: 500,
        statusMessage: `Prediction failed: ${error.message || 'Unknown error'}`
      })
    }
  }
  
  // Handle GET request - return API status and available strategies
  if (method === 'GET') {
    initializeMLComponents()
    
    return {
      status: 'ready',
      timestamp: new Date().toISOString(),
      available_strategies: Object.keys(optimizationEngines),
      physics_engines: ['LFP', 'Lead-Acid', 'VRFB'],
      api_version: '2.0.0',
      features: [
        'Real-time energy optimization',
        'Multi-chemistry battery physics',
        'User preference strategies',
        'Profit and health optimization',
        'Physics-aware constraints'
      ]
    }
  }
  
  throw createError({
    statusCode: 405,
    statusMessage: 'Method not allowed. Use GET for status or POST for predictions.'
  })
})