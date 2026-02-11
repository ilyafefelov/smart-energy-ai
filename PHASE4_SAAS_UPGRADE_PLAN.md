# Smart Energy AI v2 - SaaS Upgrade Implementation Plan

**Date:** 2026-02-11  
**Current State:** Phase 3 Complete (Nuxt 4 + Dagster ML + MLflow)  
**Target:** SaaS-ready system with multi-tenancy, advanced battery modeling, Ukraine 2026 tariffs  

## 📊 Current System Analysis

### ✅ What We Have (v1.0.0-stable)
```
Nuxt 4 Dashboard: 4 pages, real-time data, interactive charts
Dagster ML Pipeline: 31 assets, 72.5% accuracy, XGBoost
Data Sources: OREE (scraper) + OpenWeather API + Battery BMS
Features: 73 engineered features
Model: XGBoost classifier (BUY/SELL/HOLD/DISCHARGE)
Integration: Dashboard ↔ ML pipeline via 4 API endpoints
Documentation: Complete guides, data flow docs
Git: Clean, v1.0.0-stable tagged
```

### 🎯 Upgrade Requirements (from NotebookLM conversation)

#### 1. **Library Modernization**
```
Current → Upgrade To
pandas → polars (CPU performance)
Add: nvtabular (GPU acceleration)  
Add: dask.distributed (parallelization)
optuna: Already have → Upgrade to 4.7.0+ (multi-objective)
Add: pydantic (user config validation)
Add: tenacity (resilient retries)
Add: duckdb (analytics OLAP)
```

#### 2. **Multi-Tenancy (SaaS Ready)**
```
Current: Single user system
Target: Asset Factories for hundreds of clients
Implementation: YAML configs per client
Architecture: PostgreSQL for client data + Dagster asset generation
```

#### 3. **Advanced Battery Modeling**
```
Current: Simple SOC tracking
Target: Dynamic degradation cost calculation
- LFP vs Lead-Acid vs VRFB battery types
- Cyclic aging (SoH_cyc) + Calendar aging (SoH_cal)
- Marginal Cost of Degradation (MC_deg)
- Knee Point prediction (non-linear degradation)
- C-rate impact modeling
```

#### 4. **Load Profile Simulation**
```
Current: Static battery simulation
Target: Business operation modeling
- Standard work hours (9-18)
- Multi-shift operations (2/3 shifts)
- 24/7 operations
- Custom hourly load profiles
- Self-consumption vs Grid export optimization
```

#### 5. **Ukraine 2026 Tariff Integration**
```
Current: Simple OREE prices
Target: Full NKREKU 2026 tariff structure
- Transmission tariff: 713.68 → 742.91 UAH/MWh (April change)
- Dispatch tariff: 110.03 UAH/MWh
- Group A hourly pricing (commercial sector)
- Price caps: 15,000 UAH/MWh (DAM), 16,000 UAH/MWh (balancing)
```

#### 6. **User Configuration System**
```
Current: Hard-coded configs
Target: Dashboard-based user input
- Battery capacity, type, efficiency
- Solar/wind generation capacity
- Business operation hours
- Load profile templates
- Economic parameters
```

## 🚧 Implementation Challenges & Incompatibilities

### ❌ **Not Feasible/Makes No Sense:**

1. **AWS Lambda Focus**: We're on localhost development, not AWS deployment
   - Skip: Lambda layers, RDS, S3 integration 
   - Keep: Core algorithms and models

2. **NVTabular GPU**: Likely overkill for single-user development
   - Skip: GPU acceleration initially
   - Keep: Polars CPU optimization

3. **IoT Integration**: Phase 1 explicitly avoids IoT
   - Skip: MQTT, Modbus protocols
   - Keep: User configuration approach

### ⚠️ **Requires Adaptation:**

1. **Multi-tenancy**: Adapt for single-user with profiles
   - Modify: Asset Factories → Config profiles
   - Keep: Multiple scenario simulation

2. **PostgreSQL**: We use local development
   - Modify: Use SQLite/DuckDB for local storage
   - Keep: Database structure concepts

## 🎯 Phase 4 Implementation Plan

### **Phase 4A: Library & Architecture Upgrades (Week 1)**
```
Priority: HIGH
Duration: 3-5 days
Focus: Modernize data processing stack

Tasks:
1. Upgrade libraries (polars, optuna 4.7+, add pydantic)
2. Replace pandas with polars in all assets
3. Add tenacity for API retry logic
4. Implement pydantic user config models
5. Add duckdb for analytics queries
6. Update dependency management
```

### **Phase 4B: Advanced Battery Modeling (Week 2)**
```
Priority: HIGH  
Duration: 5-7 days
Focus: Implement dynamic degradation modeling

Tasks:
1. Implement battery type models (LFP, Lead-Acid, VRFB)
2. Add degradation cost calculation (MC_deg)
3. Implement SOC segmentation (10 segments)
4. Add cyclic vs calendar aging models  
5. Implement Knee Point prediction
6. Add C-rate impact calculation
7. Update dashboard battery health visualization
```

### **Phase 4C: Load Profile System (Week 2-3)**
```
Priority: HIGH
Duration: 4-6 days  
Focus: Business operation simulation

Tasks:
1. Create Load_Profile_Asset in Dagster
2. Implement profile templates (standard, shifts, 24/7, custom)
3. Add hourly consumption modeling
4. Integrate self-consumption vs export logic
5. Update dashboard for load profile configuration
6. Add business metrics (arbitrage savings, avoided costs)
```

### **Phase 4D: Ukraine 2026 Tariff System (Week 3)**
```  
Priority: MEDIUM
Duration: 3-4 days
Focus: Accurate tariff modeling

Tasks:
1. Implement NKREKU 2026 tariff structure
2. Add date-based tariff switching (April 1st)
3. Integrate Group A hourly pricing
4. Add price cap limits
5. Update cost calculation formulas
6. Test with real 2026 scenarios
```

### **Phase 4E: User Configuration Dashboard (Week 3-4)**
```
Priority: HIGH
Duration: 4-5 days
Focus: User-friendly configuration

Tasks:
1. Create user config UI pages
2. Implement pydantic validation
3. Add config profiles/templates
4. Integrate with Dagster asset generation
5. Add configuration export/import
6. Test multi-profile scenarios
```

### **Phase 4F: Integration & Optimization (Week 4)**
```
Priority: HIGH
Duration: 2-3 days
Focus: System integration and performance

Tasks:
1. Integrate all Phase 4 components
2. Update ML pipeline with new features
3. Performance optimization with polars
4. Update documentation
5. Add comprehensive testing
6. Final integration testing
```

## 🛠️ Technical Architecture Changes

### **New Libraries to Add:**
```bash
# Core data processing
pip install polars>=0.20.0
pip install duckdb>=0.10.0  
pip install pydantic>=2.6.0

# Optimization & ML
pip install optuna>=4.7.0
pip install tenacity>=8.0.0

# Optional (Phase 4B+)
pip install nvtabular  # If GPU needed later
pip install dask[distributed]>=2024.1.0
```

### **New Dagster Assets:**
```python
# Phase 4B: Battery modeling
battery_degradation_asset
battery_soh_asset  
marginal_cost_asset

# Phase 4C: Load profiles  
load_profile_asset
business_schedule_asset
consumption_simulation_asset

# Phase 4D: Tariff system
ukraine_tariff_asset
transmission_cost_asset
price_cap_asset

# Phase 4E: User config
user_config_asset
profile_validation_asset
```

### **New Dashboard Pages:**
```
/config - User configuration (battery, solar, business hours)
/profiles - Load profile templates and custom creation
/economics - Tariff settings and cost modeling
/health - Battery health monitoring and predictions
```

### **Database Schema Updates:**
```sql
-- User profiles table
CREATE TABLE user_profiles (
    id UUID PRIMARY KEY,
    name VARCHAR(255),
    battery_type VARCHAR(50), -- 'LFP', 'Lead-Acid', 'VRFB'  
    battery_capacity_kwh DECIMAL,
    solar_capacity_kw DECIMAL,
    business_hours JSONB,
    created_at TIMESTAMP
);

-- Load profiles table
CREATE TABLE load_profiles (
    id UUID PRIMARY KEY,
    user_profile_id UUID REFERENCES user_profiles(id),
    profile_type VARCHAR(50), -- 'standard', 'multi-shift', '24/7', 'custom'
    hourly_coefficients DECIMAL[24],
    created_at TIMESTAMP
);

-- Battery health tracking
CREATE TABLE battery_health_log (
    id UUID PRIMARY KEY,
    user_profile_id UUID REFERENCES user_profiles(id),
    timestamp TIMESTAMP,
    soh_percentage DECIMAL,
    equivalent_full_cycles INTEGER,
    marginal_cost_deg DECIMAL
);
```

## 🧪 Testing Strategy

### **Phase 4A Testing:**
```bash
# Library compatibility
pytest tests/test_polars_migration.py
pytest tests/test_pydantic_models.py

# Performance benchmarks
python benchmarks/pandas_vs_polars.py
```

### **Phase 4B Testing:**
```bash
# Battery modeling accuracy  
pytest tests/test_battery_degradation.py
pytest tests/test_soh_calculation.py
pytest tests/test_knee_point_prediction.py

# Economic calculations
pytest tests/test_marginal_cost.py
```

### **Phase 4C Testing:**
```bash
# Load profile generation
pytest tests/test_load_profiles.py
pytest tests/test_business_schedules.py

# Consumption simulation
pytest tests/test_consumption_modeling.py
```

### **Integration Testing:**
```bash
# End-to-end scenarios
pytest tests/integration/test_full_pipeline.py
pytest tests/integration/test_dashboard_integration.py

# Performance testing
python tests/performance/test_asset_execution_time.py
```

## 📝 Documentation Updates Required

### **New Documentation Files:**
```
PHASE4_ARCHITECTURE.md - New system architecture
BATTERY_MODELING_GUIDE.md - Advanced battery calculations
LOAD_PROFILE_GUIDE.md - Business operation modeling  
UKRAINE_TARIFF_2026.md - Tariff implementation details
USER_CONFIG_GUIDE.md - Configuration system usage
MIGRATION_GUIDE.md - v1.0 → v2.0 migration steps
```

### **Updated Documentation:**
```
DATA_FLOW_EXPLAINED.md - Add new data flows
PHASE3_COMPLETE.md - Mark as v1.0, add v2.0 roadmap
README.md - Update with Phase 4 features
```

## 🎯 Success Metrics

### **Performance Targets:**
```
Data Processing: 50%+ faster with polars vs pandas
Asset Execution: <30 seconds for full pipeline  
Dashboard Load: <3 seconds for all pages
Battery Prediction: 95%+ accuracy for degradation
Load Profile Sim: Support 100+ different business scenarios
```

### **Feature Completeness:**
```
✅ 3+ battery types supported (LFP, Lead-Acid, VRFB)
✅ 5+ load profile templates  
✅ Ukraine 2026 tariff integration
✅ User configuration system
✅ Advanced degradation modeling
✅ Multi-scenario comparison
```

## 🚀 Codex CLI Implementation Strategy

### **Phase 4A Commands:**
```bash
# Library upgrades
codex upgrade pandas polars energy_ml/
codex add pydantic optuna tenacity duckdb
codex test migration pandas-to-polars

# Architecture refactoring  
codex refactor data-processing polars
codex implement retry-logic tenacity
```

### **Phase 4B Commands:**
```bash
# Battery modeling
codex implement battery-degradation-models
codex add soh-calculation cyclic-calendar-aging  
codex create marginal-cost-calculator
codex test battery-accuracy degradation-prediction
```

### **Phase 4C Commands:**
```bash  
# Load profiles
codex create load-profile-system business-schedules
codex implement consumption-simulation
codex add dashboard-load-config
codex test load-profile-accuracy
```

### **Phase 4D Commands:**
```bash
# Ukraine tariffs
codex implement ukraine-2026-tariffs
codex add tariff-date-switching price-caps
codex integrate nkreku-pricing-structure  
codex test tariff-calculations
```

### **Integration Commands:**
```bash
# Full system integration
codex integrate phase4-components
codex test end-to-end-pipeline
codex optimize performance-polars
codex document phase4-architecture
```

## 📋 Implementation Checklist

### **Pre-Implementation:**
- [ ] Review current v1.0.0-stable system
- [ ] Create Phase 4 branch: `feature/saas-upgrade-phase4`  
- [ ] Set up testing environment
- [ ] Install new dependencies
- [ ] Create database schema updates

### **Phase 4A (Library Upgrades):**
- [ ] Replace pandas with polars in all assets
- [ ] Add pydantic config models
- [ ] Implement tenacity retry logic
- [ ] Add duckdb analytics queries  
- [ ] Update optuna to 4.7.0+
- [ ] Performance benchmarking

### **Phase 4B (Battery Modeling):**  
- [ ] Implement LFP/Lead-Acid/VRFB models
- [ ] Add SOC segmentation (10 segments)
- [ ] Create degradation cost calculator
- [ ] Implement Knee Point prediction
- [ ] Add C-rate impact modeling
- [ ] Battery health dashboard integration

### **Phase 4C (Load Profiles):**
- [ ] Create Load_Profile_Asset
- [ ] Implement business hour templates
- [ ] Add consumption simulation
- [ ] Self-consumption vs export logic
- [ ] Dashboard configuration UI
- [ ] Business metrics calculation

### **Phase 4D (Ukraine Tariffs):**
- [ ] NKREKU 2026 tariff structure  
- [ ] Date-based tariff switching
- [ ] Price cap implementation
- [ ] Group A hourly pricing
- [ ] Cost formula updates
- [ ] Tariff testing scenarios

### **Phase 4E (User Config):**
- [ ] User configuration dashboard pages
- [ ] Pydantic validation integration
- [ ] Config profile templates  
- [ ] Export/import functionality
- [ ] Multi-profile support
- [ ] Configuration persistence

### **Phase 4F (Integration):**
- [ ] Component integration testing
- [ ] ML pipeline updates
- [ ] Performance optimization
- [ ] Documentation updates  
- [ ] Comprehensive testing
- [ ] Production readiness check

## 💡 Key Implementation Notes

### **Priority Order:**
1. **Phase 4A** (libraries) - Foundation for everything else
2. **Phase 4B** (battery) - Core business value  
3. **Phase 4C** (load profiles) - Essential SaaS feature
4. **Phase 4E** (user config) - User experience
5. **Phase 4D** (tariffs) - Market accuracy
6. **Phase 4F** (integration) - Production readiness

### **Risk Mitigation:**
- Keep v1.0.0-stable as fallback
- Implement feature flags for gradual rollout
- Comprehensive testing at each phase
- Performance monitoring throughout
- Documentation updates in parallel

### **Success Criteria:**
- All current functionality preserved
- Performance improved (polars)
- New SaaS features working  
- User configuration system functional
- Advanced battery modeling accurate
- Ukraine 2026 tariffs integrated
- Production deployment ready

---

**This plan transforms the current single-user system into a SaaS-ready platform with advanced battery modeling, business operation simulation, and Ukraine-specific energy market integration. Ready for Codex CLI implementation!**