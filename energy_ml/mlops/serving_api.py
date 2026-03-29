"""
Phase 4: Production ML Model Serving API
FastAPI serving layer with real-time prediction, WebSocket updates, and health checks
"""

import logging
import asyncio
import importlib.util
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime
import json
import time

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .model_registry import get_model_registry
from .feature_store import get_feature_store
from .battery_physics import BatteryPhysicsEngine
from .optimization_engine import OptimizationEngine
from .monitoring_dashboard import get_monitoring_dashboard
from .retraining_pipeline import get_retraining_pipeline, get_ab_test_manager
from ..user_config import UserConfigModel

try:
    from energy_ml.mlops.serving_api_support import (
        build_feature_vector,
        build_fallback_prediction,
        build_health_components,
        build_health_response_payload,
        build_prediction_response_payload,
        coerce_prediction_output,
        estimate_power_kw,
        estimate_profit_uah,
        prediction_value_from_decision,
        prune_disconnected_websockets,
        simulate_battery_response,
        summarize_model_versions,
    )
except ImportError:
    _SUPPORT_MODULE_NAME = "energy_ml.mlops.serving_api_support"
    _SUPPORT_PATH = Path(__file__).with_name("serving_api_support.py")
    _SUPPORT_SPEC = importlib.util.spec_from_file_location(_SUPPORT_MODULE_NAME, _SUPPORT_PATH)
    if _SUPPORT_SPEC is None or _SUPPORT_SPEC.loader is None:
        raise ImportError(f"Unable to load serving API support module from {_SUPPORT_PATH}")
    _SUPPORT_MODULE = sys.modules.get(_SUPPORT_MODULE_NAME)
    if _SUPPORT_MODULE is None:
        _SUPPORT_MODULE = importlib.util.module_from_spec(_SUPPORT_SPEC)
        sys.modules[_SUPPORT_MODULE_NAME] = _SUPPORT_MODULE
        _SUPPORT_SPEC.loader.exec_module(_SUPPORT_MODULE)
    build_feature_vector = _SUPPORT_MODULE.build_feature_vector
    build_fallback_prediction = _SUPPORT_MODULE.build_fallback_prediction
    build_health_components = _SUPPORT_MODULE.build_health_components
    build_health_response_payload = _SUPPORT_MODULE.build_health_response_payload
    build_prediction_response_payload = _SUPPORT_MODULE.build_prediction_response_payload
    coerce_prediction_output = _SUPPORT_MODULE.coerce_prediction_output
    estimate_power_kw = _SUPPORT_MODULE.estimate_power_kw
    estimate_profit_uah = _SUPPORT_MODULE.estimate_profit_uah
    prediction_value_from_decision = _SUPPORT_MODULE.prediction_value_from_decision
    prune_disconnected_websockets = _SUPPORT_MODULE.prune_disconnected_websockets
    simulate_battery_response = _SUPPORT_MODULE.simulate_battery_response
    summarize_model_versions = _SUPPORT_MODULE.summarize_model_versions

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
            chemistry: BatteryPhysicsEngine()
            for chemistry in BatteryPhysicsEngine.CHEMISTRY_PARAMS
        }
        
        # Initialize optimization engines
        self.optimization_engines = {
            strategy: OptimizationEngine()
            for strategy in OptimizationEngine.OPTIMIZATION_STRATEGIES
        }
            
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
            components = build_health_components(
                self._check_model_registry(),
                self._check_feature_store(),
                len(self.physics_engines),
                len(self.optimization_engines),
                self.cached_model,
            )
            latency_ms = (time.time() - start_time) * 1000

            return HealthCheckResponse(**build_health_response_payload(components, latency_ms, datetime.now()))
            
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
                features = self.feature_store.load_online_features(
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
                strategy = self._resolve_strategy(request.strategy)
                optimization_engine = self.optimization_engines[strategy]
                base_prediction = self._build_base_prediction(model, features)
                
                # Make optimization decision
                decision = optimization_engine.optimize_decision(
                    base_prediction,
                    strategy,
                )
                
                # Calculate latency
                latency_ms = (time.time() - start_time) * 1000
                
                # Log prediction for monitoring
                background_tasks.add_task(
                    self._log_prediction_async,
                    model_version, features, decision, request.user_id, latency_ms
                )
                
                response = self._build_prediction_response(
                    decision,
                    request,
                    prediction_id,
                    model_version,
                    strategy,
                )
                
                # Send real-time update to WebSocket clients
                await self._broadcast_websocket_update({
                    "type": "prediction",
                    "data": response.model_dump()
                })
                
                return response
            except HTTPException:
                raise
                
            except Exception as e:
                logger.error(f"Prediction failed: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")
                
        @self.app.post("/simulate/battery")
        async def simulate_battery_physics(request: BatterySimulationRequest):
            """Simulate battery physics for given power profile"""
            
            try:
                if request.battery_type not in self.physics_engines:
                    raise HTTPException(status_code=400, detail=f"Unsupported battery type: {request.battery_type}")
                return self._simulate_battery_request(request)
            except HTTPException:
                raise
                
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
                    **summarize_model_versions(production_models, staging_models, development_models)
                }
                
            except Exception as e:
                logger.error(f"Failed to list model versions: {str(e)}")
                raise HTTPException(status_code=500, detail="Failed to retrieve model versions")
                
    def _check_model_registry(self) -> bool:
        """Check if model registry is healthy"""
        try:
            models = self.model_registry.list_model_versions("energy_optimizer")
            if models is None:
                return False
            return len(models) > 0
        except Exception:
            return False
            
    def _check_feature_store(self) -> bool:
        """Check if feature store is healthy"""
        try:
            feature_views = getattr(self.feature_store, "feature_views", None)
            if feature_views is None:
                return False
            return len(feature_views) > 0
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

    def _resolve_strategy(self, requested_strategy: str) -> str:
        """Return a known optimization strategy token."""
        if requested_strategy in self.optimization_engines:
            return requested_strategy
        return "balanced"

    def _build_base_prediction(self, model: Any, features: Dict[str, Any]) -> Dict[str, Any]:
        """Adapt raw model output into the optimizer's dict contract."""
        if hasattr(model, "predict"):
            try:
                raw_prediction = model.predict(build_feature_vector(features))
                return self._coerce_prediction_output(raw_prediction, features)
            except Exception as exc:
                logger.warning(f"Model prediction adapter failed, using fallback decision seed: {exc}")

        return self._build_fallback_prediction(features)

    def _coerce_prediction_output(self, raw_prediction: Any, features: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize raw model output into a prediction envelope."""
        return coerce_prediction_output(raw_prediction, features, datetime.now())

    def _build_fallback_prediction(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """Create a conservative prediction envelope when the raw model is not directly adaptable."""
        return build_fallback_prediction(features, datetime.now())

    def _build_prediction_response(
        self,
        decision: Dict[str, Any],
        request: PredictionRequest,
        prediction_id: str,
        model_version: str,
        strategy: str,
    ) -> PredictionResponse:
        """Fill the serving response model from the optimizer's dict contract."""
        return PredictionResponse(
            **build_prediction_response_payload(decision, request, prediction_id, model_version, strategy, datetime.now())
        )

    def _estimate_power_kw(self, action: str, request: PredictionRequest) -> float:
        """Choose a bounded power estimate when the optimizer does not provide one."""
        return estimate_power_kw(action, float(request.load_demand_kw))

    def _estimate_profit_uah(self, action: str, power_kw: float, duration_h: float, grid_price_uah_kwh: float) -> float:
        """Compute a simple profit proxy for a stable API envelope."""
        return estimate_profit_uah(action, power_kw, duration_h, grid_price_uah_kwh)

    def _simulate_battery_request(self, request: BatterySimulationRequest) -> Dict[str, Any]:
        """Adapt the request to the current battery physics engine contract."""
        physics_engine = self.physics_engines[request.battery_type]
        config = UserConfigModel(
            battery_type=request.battery_type,
            battery_temperature_c=request.temperature,
        )
        physics_data = physics_engine.simulate_battery_behavior(config)
        return simulate_battery_response(physics_data, request, float(config.battery_capacity_kwh))
            
    async def _log_prediction_async(self, model_version: str, features: Dict[str, Any], decision, user_id: str, latency_ms: float):
        """Log prediction asynchronously for monitoring"""
        
        try:
            prediction_value = prediction_value_from_decision(decision)
            self.monitoring_dashboard.monitor.log_prediction(
                model_version=model_version,
                features=features,
                prediction=prediction_value,
                latency_ms=latency_ms
            )
            
            # Log A/B test result if applicable
            for test_name in self.ab_test_manager.active_tests.keys():
                self.ab_test_manager.log_ab_result(
                    test_name=test_name,
                    version=model_version,
                    prediction=prediction_value
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
                
        self.websocket_connections = prune_disconnected_websockets(self.websocket_connections, disconnected)
                
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