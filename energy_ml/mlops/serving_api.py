"""
Phase 4: Production ML Model Serving API
FastAPI serving layer with real-time prediction, WebSocket updates, and health checks
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import numpy as np

from .model_registry import get_model_registry
from .feature_store import get_feature_store
from .battery_physics import BatteryPhysicsEngine
from .optimization_engine import OptimizationEngine, OptimizationStrategy
from .monitoring_dashboard import get_monitoring_dashboard
from .retraining_pipeline import get_retraining_pipeline, get_ab_test_manager

logger = logging.getLogger(__name__)

# Pydantic models for API
class PredictionRequest(BaseModel):
    """Energy prediction request"""
    user_id: str = "default_user"
    battery_soc: float = Field(..., ge=0.0, le=1.0, description="Battery SOC (0-1)")
    grid_price_uah_kwh: float = Field(..., ge=0.0, description="Grid price UAH/kWh")
    solar_generation_kw: float = Field(default=0.0, ge=0.0, description="Solar generation kW")
    wind_generation_kw: float = Field(default=0.0, ge=0.0, description="Wind generation kW") 
    load_demand_kw: float = Field(..., ge=0.0, description="Load demand kW")
    temperature_celsius: float = Field(default=25.0, description="Temperature °C")
    strategy: str = Field(default="balanced", description="Optimization strategy")

class PredictionResponse(BaseModel):
    """Energy prediction response"""
    action: str
    power_kw: float
    duration_h: float
    confidence: float
    expected_profit_uah: float
    health_impact_percent: float
    reasoning: str
    strategy_used: str
    prediction_id: str
    timestamp: str
    model_version: str

class BatterySimulationRequest(BaseModel):
    """Battery physics simulation request"""
    battery_type: str = Field(default="LFP", description="Battery chemistry")
    power_kw: float = Field(..., description="Power for simulation (+ charge, - discharge)")
    duration_h: float = Field(..., ge=0.0, le=24.0, description="Duration in hours")
    temperature: float = Field(default=25.0, description="Temperature °C")

class HealthCheckResponse(BaseModel):
    """Health check response"""
    status: str
    timestamp: str
    version: str
    models_loaded: bool
    latency_ms: float
    components: Dict[str, Any]

class MLServingAPI:
    """Production ML serving API for Smart Energy AI"""
    
    def __init__(self):
        self.app = FastAPI(
            title="Smart Energy AI - ML Serving API",
            description="Production ML API for energy optimization and battery control",
            version="2.0.0"
        )
        
        # Add CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Initialize ML components
        self.model_registry = get_model_registry()
        self.feature_store = get_feature_store()
        self.monitoring_dashboard = get_monitoring_dashboard()
        self.retraining_pipeline = get_retraining_pipeline()
        self.ab_test_manager = get_ab_test_manager()
        
        # Initialize physics engines for different chemistries
        self.physics_engines = {
            "LFP": BatteryPhysicsEngine("LFP"),
            "Lead-Acid": BatteryPhysicsEngine("Lead-Acid"),
            "VRFB": BatteryPhysicsEngine("VRFB")
        }
        
        # Initialize optimization engines
        self.optimization_engines = {}
        for strategy in OptimizationStrategy:
            engine = OptimizationEngine(self.physics_engines["LFP"], strategy)
            self.optimization_engines[strategy.value] = engine
            
        # WebSocket connections for real-time updates
        self.websocket_connections: List[WebSocket] = []
        
        # Production model cache
        self.cached_model = None
        self.cached_model_version = None
        
        self._setup_routes()
        self._load_production_model()
        
        # Start background tasks
        self._start_background_tasks()
        
    def _setup_routes(self):
        """Setup API routes"""
        
        @self.app.get("/health", response_model=HealthCheckResponse)
        async def health_check():
            """Health check endpoint with detailed status"""
            start_time = time.time()
            
            # Check component health
            components = {
                "model_registry": self._check_model_registry(),
                "feature_store": self._check_feature_store(),
                "physics_engines": len(self.physics_engines) > 0,
                "optimization_engines": len(self.optimization_engines) > 0,
                "cached_model": self.cached_model is not None
            }
            
            all_healthy = all(components.values())
            latency_ms = (time.time() - start_time) * 1000
            
            return HealthCheckResponse(
                status="healthy" if all_healthy else "degraded",
                timestamp=datetime.now().isoformat(),
                version="2.0.0",
                models_loaded=self.cached_model is not None,
                latency_ms=latency_ms,
                components=components
            )
            
        @self.app.post("/predict", response_model=PredictionResponse)
        async def predict_optimization(request: PredictionRequest, background_tasks: BackgroundTasks):
            """Make energy optimization prediction"""
            start_time = time.time()
            prediction_id = f"pred_{int(time.time() * 1000)}"
            
            try:
                # Get model version (A/B test routing)
                model_version = self.ab_test_manager.route_prediction(request.user_id)
                if model_version == "production":
                    model = self.cached_model
                    model_version = self.cached_model_version
                else:
                    # Load specific version for A/B test
                    model = self._load_model_version(model_version)
                    
                if model is None:
                    raise HTTPException(status_code=503, detail="No model available for prediction")
                    
                # Get real-time features
                features = self.feature_store.get_online_features(
                    "energy_features",
                    {"user_id": request.user_id, "timestamp": datetime.now()}
                )
                
                # Update features with request data
                features.update({
                    "battery_soc": request.battery_soc,
                    "grid_price_uah_kwh": request.grid_price_uah_kwh,
                    "solar_generation_kw": request.solar_generation_kw,
                    "wind_generation_kw": request.wind_generation_kw,
                    "load_demand_kw": request.load_demand_kw,
                    "temperature_celsius": request.temperature_celsius
                })
                
                # Get optimization engine for strategy
                strategy = OptimizationStrategy(request.strategy) if request.strategy in [s.value for s in OptimizationStrategy] else OptimizationStrategy.BALANCED
                optimization_engine = self.optimization_engines[strategy.value]
                
                # Make optimization decision
                decision = optimization_engine.optimize_decision(
                    grid_price_uah_kwh=request.grid_price_uah_kwh,
                    load_demand_kw=request.load_demand_kw,
                    solar_generation_kw=request.solar_generation_kw,
                    wind_generation_kw=request.wind_generation_kw,
                    temperature=request.temperature_celsius
                )
                
                # Calculate latency
                latency_ms = (time.time() - start_time) * 1000
                
                # Log prediction for monitoring
                background_tasks.add_task(
                    self._log_prediction_async,
                    model_version, features, decision, request.user_id, latency_ms
                )
                
                response = PredictionResponse(
                    action=decision.action,
                    power_kw=decision.power_kw,
                    duration_h=decision.duration_h,
                    confidence=decision.confidence,
                    expected_profit_uah=decision.expected_profit_uah,
                    health_impact_percent=decision.health_impact_percent,
                    reasoning=decision.reasoning,
                    strategy_used=decision.strategy_used.value,
                    prediction_id=prediction_id,
                    timestamp=datetime.now().isoformat(),
                    model_version=model_version
                )
                
                # Send real-time update to WebSocket clients
                await self._broadcast_websocket_update({
                    "type": "prediction",
                    "data": response.dict()
                })
                
                return response
                
            except Exception as e:
                logger.error(f"Prediction failed: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")
                
        @self.app.post("/simulate/battery")
        async def simulate_battery_physics(request: BatterySimulationRequest):
            """Simulate battery physics for given power profile"""
            
            try:
                if request.battery_type not in self.physics_engines:
                    raise HTTPException(status_code=400, detail=f"Unsupported battery type: {request.battery_type}")
                    
                physics_engine = self.physics_engines[request.battery_type]
                
                # Store initial state
                initial_state = physics_engine.current_model.state
                
                # Run simulation
                final_state = physics_engine.simulate_charge_discharge(
                    request.power_kw,
                    request.duration_h,
                    request.temperature
                )
                
                # Get physics summary
                summary = physics_engine.get_physics_summary()
                
                # Restore initial state (don't modify global state)
                physics_engine.current_model.state = initial_state
                
                return {
                    "initial_state": {
                        "soc_percent": initial_state.soc * 100,
                        "soh_percent": initial_state.soh * 100,
                        "voltage": initial_state.voltage,
                        "temperature": initial_state.temperature
                    },
                    "final_state": {
                        "soc_percent": final_state.soc * 100,
                        "soh_percent": final_state.soh * 100,
                        "voltage": final_state.voltage,
                        "temperature": final_state.temperature,
                        "cycles_completed": final_state.cycles_completed
                    },
                    "physics_summary": summary,
                    "simulation_params": {
                        "power_kw": request.power_kw,
                        "duration_h": request.duration_h,
                        "temperature": request.temperature,
                        "battery_type": request.battery_type
                    }
                }
                
            except Exception as e:
                logger.error(f"Battery simulation failed: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Simulation failed: {str(e)}")
                
        @self.app.get("/monitoring/dashboard")
        async def get_monitoring_dashboard():
            """Get ML monitoring dashboard data"""
            
            try:
                dashboard_data = self.monitoring_dashboard.get_dashboard_data()
                return dashboard_data
            except Exception as e:
                logger.error(f"Failed to get dashboard data: {str(e)}")
                raise HTTPException(status_code=500, detail="Dashboard data unavailable")
                
        @self.app.post("/models/retrain")
        async def trigger_retraining(background_tasks: BackgroundTasks):
            """Trigger model retraining"""
            
            try:
                # Check if retraining is needed
                triggers = self.retraining_pipeline.check_retraining_triggers()
                
                if not triggers['should_retrain']:
                    return {
                        "message": "Retraining not needed at this time",
                        "reasons": "No performance degradation or drift detected"
                    }
                    
                # Trigger retraining in background
                background_tasks.add_task(self._retrain_model_async)
                
                return {
                    "message": "Model retraining initiated",
                    "reasons": triggers['reasons'],
                    "estimated_duration_minutes": 15
                }
                
            except Exception as e:
                logger.error(f"Failed to trigger retraining: {str(e)}")
                raise HTTPException(status_code=500, detail="Retraining failed to start")
                
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket endpoint for real-time updates"""
            
            await websocket.accept()
            self.websocket_connections.append(websocket)
            
            try:
                while True:
                    # Keep connection alive
                    data = await websocket.receive_text()
                    
                    # Handle client messages (ping, subscribe, etc.)
                    try:
                        message = json.loads(data)
                        if message.get("type") == "ping":
                            await websocket.send_json({"type": "pong", "timestamp": datetime.now().isoformat()})
                    except json.JSONDecodeError:
                        pass
                        
            except WebSocketDisconnect:
                self.websocket_connections.remove(websocket)
                logger.info("WebSocket client disconnected")
                
        @self.app.get("/models/versions")
        async def list_model_versions():
            """List available model versions"""
            
            try:
                production_models = self.model_registry.list_model_versions("energy_optimizer", stage="production")
                staging_models = self.model_registry.list_model_versions("energy_optimizer", stage="staging")
                development_models = self.model_registry.list_model_versions("energy_optimizer", stage="development")
                
                return {
                    "production": [
                        {
                            "version_id": m.version_id,
                            "created_at": m.created_at.isoformat(),
                            "performance_mape": m.performance_metrics.get("test_mape", 0),
                            "health_status": m.health_status
                        }
                        for m in production_models[:5]  # Latest 5
                    ],
                    "staging": [
                        {
                            "version_id": m.version_id,
                            "created_at": m.created_at.isoformat(),
                            "performance_mape": m.performance_metrics.get("test_mape", 0),
                            "health_status": m.health_status
                        }
                        for m in staging_models[:5]
                    ],
                    "development": len(development_models)
                }
                
            except Exception as e:
                logger.error(f"Failed to list model versions: {str(e)}")
                raise HTTPException(status_code=500, detail="Failed to retrieve model versions")
                
    def _check_model_registry(self) -> bool:
        """Check if model registry is healthy"""
        try:
            models = self.model_registry.list_model_versions("energy_optimizer")
            return len(models) > 0
        except Exception:
            return False
            
    def _check_feature_store(self) -> bool:
        """Check if feature store is healthy"""
        try:
            return len(self.feature_store.feature_views) > 0
        except Exception:
            return False
            
    def _load_production_model(self):
        """Load current production model into cache"""
        try:
            model = self.model_registry.get_production_model()
            if model is not None:
                self.cached_model = model
                
                # Get model version info
                production_versions = self.model_registry.list_model_versions("energy_optimizer", stage="production")
                if production_versions:
                    self.cached_model_version = production_versions[0].version_id
                    
                logger.info(f"Loaded production model: {self.cached_model_version}")
            else:
                logger.warning("No production model found")
        except Exception as e:
            logger.error(f"Failed to load production model: {str(e)}")
            
    def _load_model_version(self, version_id: str):
        """Load specific model version"""
        try:
            version = self.model_registry.get_model_version(version_id)
            if version:
                import joblib
                model_file = version.artifacts_path / "model.joblib"
                return joblib.load(model_file)
            return None
        except Exception as e:
            logger.error(f"Failed to load model version {version_id}: {str(e)}")
            return None
            
    async def _log_prediction_async(self, model_version: str, features: Dict[str, Any], decision, user_id: str, latency_ms: float):
        """Log prediction asynchronously for monitoring"""
        
        try:
            self.monitoring_dashboard.monitor.log_prediction(
                model_version=model_version,
                features=features,
                prediction=decision.expected_profit_uah,  # Use profit as prediction value
                latency_ms=latency_ms
            )
            
            # Log A/B test result if applicable
            for test_name in self.ab_test_manager.active_tests.keys():
                self.ab_test_manager.log_ab_result(
                    test_name=test_name,
                    version=model_version,
                    prediction=decision.expected_profit_uah
                )
                
        except Exception as e:
            logger.error(f"Failed to log prediction: {str(e)}")
            
    async def _retrain_model_async(self):
        """Retrain model asynchronously"""
        
        try:
            result = self.retraining_pipeline.trigger_retraining("API trigger")
            
            if result['success']:
                # Reload production model if new version was deployed
                self._load_production_model()
                
                # Broadcast update to WebSocket clients
                await self._broadcast_websocket_update({
                    "type": "model_update",
                    "data": {
                        "message": "New model version deployed",
                        "version": result['new_model_version'],
                        "performance": result['metrics']
                    }
                })
                
            logger.info(f"Model retraining completed: {result}")
            
        except Exception as e:
            logger.error(f"Background retraining failed: {str(e)}")
            
    async def _broadcast_websocket_update(self, message: Dict[str, Any]):
        """Broadcast update to all WebSocket connections"""
        
        if not self.websocket_connections:
            return
            
        disconnected = []
        
        for websocket in self.websocket_connections:
            try:
                await websocket.send_json(message)
            except Exception:
                disconnected.append(websocket)
                
        # Remove disconnected clients
        for ws in disconnected:
            if ws in self.websocket_connections:
                self.websocket_connections.remove(ws)
                
    def _start_background_tasks(self):
        """Start background monitoring tasks"""
        
        async def monitoring_loop():
            """Background monitoring loop"""
            while True:
                try:
                    # Check for alerts and model health
                    from .monitoring_dashboard import monitor_energy_model
                    monitoring_result = monitor_energy_model()
                    
                    # Broadcast monitoring updates
                    await self._broadcast_websocket_update({
                        "type": "monitoring_update",
                        "data": monitoring_result
                    })
                    
                    # Check for automatic retraining
                    triggers = self.retraining_pipeline.check_retraining_triggers()
                    if triggers['should_retrain']:
                        logger.info("Automatic retraining triggered")
                        await self._retrain_model_async()
                        
                    await asyncio.sleep(300)  # Check every 5 minutes
                    
                except Exception as e:
                    logger.error(f"Monitoring loop error: {str(e)}")
                    await asyncio.sleep(60)  # Wait before retrying
                    
        # Start monitoring loop
        asyncio.create_task(monitoring_loop())

# FastAPI app instance
ml_serving_api = MLServingAPI()
app = ml_serving_api.app

# For testing
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)