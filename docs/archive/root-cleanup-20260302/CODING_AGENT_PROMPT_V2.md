# Role: Senior Python MLOps Engineer & Dagster Architect

**Context:** You are implementing Smart Energy AI V2 - a production evolution from our successful V1 system that achieved 28.6% cost savings through RL optimization. V1 proved the business case; V2 focuses on scalable architecture and advanced modeling.

**V1 Lessons Learned:**
- Real Ukrainian OREE market data integration works well
- RL-based optimization (PPO) achieved significant cost reduction  
- User configuration system is essential for flexibility
- Streamlit dashboard provides good user experience
- Comprehensive testing and documentation are critical
- Economic modeling with battery degradation is key differentiator

## Task: Implement Smart Energy AI V2 - Software-Defined Assets Architecture

**Target:** Dagster-based data orchestration with Dual-Engine benchmarking for Master's Thesis research, optimized for AWS Free Tier deployment.

---

## Phase 1: Dagster Foundation & Asset Architecture

### 1.1 Project Structure Setup
Initialize the complete folder structure as defined in the project README:

```
src/
├── definitions.py                     # Main Dagster entry point
├── assets/
│   ├── core/                         # Market & weather data
│   ├── multi_tenant/                 # Client-specific assets
│   └── benchmarks/                   # Dual-engine comparison
├── resources/                        # I/O managers & MLflow
├── physics/                          # Battery & economic models
└── engines/                          # Polars vs NVTabular engines
```

### 1.2 Core Configuration Files
Create essential Dagster configuration:
- `dagster.yaml` - Deployment configuration for local dev + AWS
- `workspace.yaml` - Asset location definitions  
- `customers.yaml` - Multi-tenant customer definitions (minimum 3 sample clients)

### 1.3 Physics & Economics Module
Implement `src/physics/battery_lfp.py` with advanced modeling:

**DegradationModel Class:**
```python
class DegradationModel:
    def calculate_marginal_cost(self, soc: float, temp: float, cycle_depth: float) -> float:
        """Calculate MC_deg using: (Capex / LifeCycles) * StressFactor"""
        
    def predict_sei_growth(self, time: float, temp: float) -> float:
        """Model SEI layer growth for 'Knee Point' prediction"""
        
    def get_stress_factor(self, soc: float, temp: float) -> float:
        """LFP stress increases sharply at SoC > 90% and Temp > 35°C"""
```

**Key Requirements:**
- Use realistic LFP battery parameters (280Ah cells, ~6000 cycles)
- Implement non-linear degradation curves
- Include temperature compensation models
- Add comprehensive docstrings explaining thesis relevance

---

## Phase 2: Dual-Engine Implementation & Benchmarking

### 2.1 Engine Architecture
Create defensive import pattern for GPU/CPU compatibility:

**src/engines/polars_engine.py:**
```python
import polars as pl
class PolarsEngine:
    """CPU-optimized engine using Rust-based Polars for edge/free-tier deployment"""
    def process_features(self, df: pl.DataFrame) -> pl.DataFrame:
        # Implement feature engineering logic
```

**src/engines/nvtabular_engine.py:**
```python
try:
    import nvtabular as nvt
    import cupy as cp
    HAS_GPU = True
except ImportError:
    HAS_GPU = False
    
class NVTabularEngine:
    """GPU-accelerated engine for high-performance training scenarios"""
    def __init__(self):
        if not HAS_GPU:
            raise ImportError("NVTabular/CUDA not available - use PolarsEngine")
```

### 2.2 Benchmarking Framework
Implement MLflow integration for thesis research:
- Track processing time per 1M rows
- Compare memory usage patterns  
- Log engine selection decisions
- Generate comparative performance reports

---

## Phase 3: Dagster Asset Implementation

### 3.1 Core Data Assets
**src/assets/core/market.py:**
```python
@asset(group_name="market_data")
def market_data_asset(context) -> pl.DataFrame:
    """Fetch OREE/ENTSO-E prices with metadata tracking"""
    # Build on V1 OREE integration experience
    # Add Dagster metadata for lineage tracking
```

**src/assets/core/weather.py:**
```python  
@asset(group_name="weather_data", deps=[market_data_asset])
def weather_asset(context) -> pl.DataFrame:
    """Enhanced Open-Meteo integration with solar irradiance modeling"""
    # Leverage V1 weather integration knowledge
```

### 3.2 Multi-Tenant Asset Factory
**src/assets/multi_tenant/optimization.py:**
```python
def create_client_assets(client_config: dict):
    """Asset factory generating client-specific optimization assets"""
    
    @asset(name=f"{client_id}_optimization")
    def client_optimization_asset(context, feature_matrix) -> dict:
        """Optuna-based optimization for specific client battery configuration"""
        
    return client_optimization_asset
```

### 3.3 Feature Engineering Assets  
**src/assets/benchmarks/feature_eng.py:**
```python
@asset(group_name="feature_engineering")
def feature_matrix(context, market_data_asset, weather_asset, config) -> pl.DataFrame:
    """Hybrid feature engineering asset with engine selection"""
    
    engine_type = config.get("execution_mode", "polars")
    
    if engine_type == "nvtabular" and HAS_GPU:
        engine = NVTabularEngine()
    else:
        engine = PolarsEngine()
        
    return engine.process_features(raw_data)
```

---

## Phase 4: AWS Integration & Deployment

### 4.1 S3 I/O Manager
**src/resources/s3_io_manager.py:**
```python
class S3PickleIOManager(IOManager):
    """Lambda-compatible I/O manager for asset data persistence"""
    
    def handle_output(self, context, obj):
        """Store DataFrames as optimized pickle files in S3"""
        
    def load_input(self, context):
        """Load and deserialize from S3 with error handling"""
```

### 4.2 Lambda Partitioning Strategy
Implement dynamic partitioning to handle Lambda's 15-minute limit:
- Split large datasets by time windows (daily/weekly partitions)
- Use Dagster's partition system for automatic parallelization
- Store intermediate results in S3 between Lambda invocations

### 4.3 MLflow Resource Integration
**src/resources/mlflow_resource.py:**
```python
@resource
def mlflow_resource(context):
    """MLflow experiment tracking for benchmarking results"""
    # Track dual-engine performance comparisons
    # Log optimization results and model metrics
```

---

## Implementation Constraints & Best Practices

### Code Quality Requirements:
- **Type Hints:** Full mypy compatibility throughout
- **Error Handling:** Robust exception handling with Dagster failure policies
- **Documentation:** Comprehensive docstrings explaining thesis relevance
- **Testing:** Unit tests for each asset and engine
- **Defensive Programming:** Graceful fallbacks for missing dependencies

### Performance Requirements:
- Assets must complete within Lambda timeout limits
- Memory usage optimization for free tier constraints
- Efficient data serialization for S3 transfers
- Minimal cold start overhead

### Research Integration:
- Every benchmarking decision must be logged to MLflow
- Generate comparative reports between engines
- Track economic model accuracy vs V1 baseline
- Document scalability improvements over V1 architecture

---

## Success Criteria

**Functional Requirements:**
✅ All Dagster assets execute successfully with lineage tracking  
✅ Dual-engine system switches correctly based on hardware detection  
✅ Multi-tenant system supports 3+ simultaneous client configurations  
✅ Economic model produces realistic degradation cost calculations  
✅ AWS deployment stays within Free Tier limits  

**Research Requirements:**  
✅ MLflow captures comprehensive benchmarking data  
✅ Performance comparison between Polars and NVTabular documented  
✅ Economic modeling improvements over V1 quantified  
✅ Scalability benefits vs monolithic V1 architecture proven  

**Quality Requirements:**
✅ >90% test coverage maintained  
✅ Complete type hint coverage  
✅ Comprehensive documentation for thesis submission  
✅ Production-ready error handling and monitoring  

---

## Next Steps After Implementation

1. **Deploy to AWS:** Use provided deployment scripts for free tier setup
2. **Run Benchmarks:** Execute dual-engine comparison studies  
3. **Scale Testing:** Validate multi-tenant performance with 10+ virtual clients
4. **Documentation:** Generate thesis-ready technical documentation
5. **V2 vs V1 Analysis:** Quantify improvements in scalability and maintainability

Begin with Phase 1 and implement incrementally, ensuring each phase is fully functional before proceeding to the next.