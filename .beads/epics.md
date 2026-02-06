# Smart Energy AI V2 - Software-Defined Assets (Stage 1)
**Phase:** Stage 1 - No IoT Integration (Synthetic User Data)
**Target:** Dagster-based data orchestration with Dual-Engine feature engineering
**Timeline:** 3 weeks implementation

## Epics

### E001: Software-Defined Assets Architecture
**Status:** Planning
**Priority:** P0
**Description:** Implement Dagster-based asset pipeline with lineage tracking

#### Tasks:
- T001: Setup Dagster workspace configuration
- T002: Implement market_data_asset (ENTSO-E/Ukrenergo API)
- T003: Implement weather_asset (Open-Meteo API)  
- T004: Implement client_state_asset (synthetic data based on user config)
- T005: Implement feature_matrix hybrid asset
- T006: Implement decision_model assets (XGBoost + Optuna)

### E002: Dual-Engine Feature Engineering
**Status:** Planning  
**Priority:** P0
**Description:** CPU (Polars) vs GPU (NVTabular) benchmarking system

#### Tasks:
- T007: Implement polars_engine.py with defensive imports
- T008: Implement nvtabular_engine.py with defensive imports
- T009: Create engine selection logic based on hardware detection
- T010: Implement MLflow integration for benchmarking
- T011: Create performance comparison framework

### E003: Economic & Physical Modeling
**Status:** Planning
**Priority:** P1  
**Description:** Advanced battery degradation and economic modeling

#### Tasks:
- T012: Implement LCOS (Levelized Cost of Storage) calculations
- T013: Implement Marginal Cost of Degradation (MC_deg) formulas
- T014: Implement SEI layer growth modeling for "Knee Point" analysis
- T015: Create battery type comparison system (LFP vs Lead-Acid)

### E004: AWS Free Tier Deployment
**Status:** Planning
**Priority:** P1
**Description:** Hybrid deployment architecture optimized for free tier

#### Tasks:
- T016: Setup EC2 t3.micro for Dagster webserver + daemon
- T017: Implement AWS Lambda workers with 15-min partitioning
- T018: Setup S3 storage with PickleIOManager
- T019: Setup RDS PostgreSQL for metadata
- T020: Implement dynamic partitioning for Lambda limitations

### E005: Multi-tenancy & Asset Factories  
**Status:** Planning
**Priority:** P2
**Description:** Scale to hundreds of clients via YAML-driven asset generation

#### Tasks:
- T021: Create customers.yaml configuration system
- T022: Implement Dagster Asset Factory pattern
- T023: Create client-specific asset isolation
- T024: Implement customer dashboard system
- T025: Create SaaS billing integration framework

## Stage 1 Scope (Current)
- Software-defined assets with Dagster
- Dual-engine feature engineering benchmarking
- Advanced economic modeling
- Synthetic data based on user energy capabilities
- AWS Free Tier deployment architecture

## Stage 2 Scope (Future)
- Real IoT integration via MQTT
- Hardware sensor data streams
- Real-time telemetry processing
- Edge device deployment
- Industrial SCADA integration

## Success Metrics
- Dagster pipeline runs successfully with lineage tracking
- Dual-engine benchmarking shows clear performance differences
- Economic model accurately predicts degradation costs
- AWS Free Tier deployment stays within limits
- Multi-tenant system supports 10+ virtual clients

## Dependencies
- V1 system knowledge and lessons learned
- Dagster framework setup
- AWS account with free tier access
- MLflow experiment tracking
- Economic modeling research