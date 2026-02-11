# Codex CLI Implementation Instructions - Phase 4 SaaS Upgrade

**Project:** Smart Energy AI - Phase 4 SaaS Upgrade  
**Baseline:** v1.0.0-stable (fully working system)  
**Target:** Commercial SaaS with advanced battery modeling  
**Branch:** feature/battery-upgrades-v2

## 🎯 Mission Summary

Transform the current localhost smart energy system into a SaaS-ready platform with:
1. **Advanced battery modeling** (LFP, Lead-Acid, VRFB with degradation costs)
2. **Business operation simulation** (load profiles for different work schedules) 
3. **Ukraine 2026 tariff integration** (NKREKU pricing structure)
4. **User configuration system** (dashboard-based setup)
5. **Performance upgrades** (pandas→polars, modern libraries)

## 🔧 Implementation Strategy

### **Phase-by-Phase Approach**
Execute in order: 4A → 4B → 4C → 4E → 4D → 4F  
Test thoroughly after each phase before proceeding.

### **Baseline Protection**
- Never modify master branch directly
- Keep v1.0.0-stable as fallback
- Test each phase on feature/battery-upgrades-v2
- Only merge when fully tested

### **Testing Requirements**
- Unit tests for each new component
- Integration tests for pipeline changes
- Performance benchmarks (pandas vs polars)
- Dashboard functionality verification

## 📋 Phase 4A: Library & Architecture Upgrades

### **Priority:** HIGH | **Duration:** 3-5 days

### **Libraries to Install:**
```bash
pip install polars>=0.20.0
pip install pydantic>=2.6.0  
pip install tenacity>=8.0.0
pip install duckdb>=0.10.0
pip install --upgrade optuna>=4.7.0
```

### **Core Tasks:**

#### **1. Pandas → Polars Migration**
- **Files:** `energy_ml/assets/data_sources.py`, `features.py`, `models.py`
- **Approach:** Replace all `pd.DataFrame` with `pl.DataFrame`
- **Key Changes:**
  ```python
  # Old
  import pandas as pd
  df = pd.DataFrame(data)
  df.groupby('column').mean()
  
  # New  
  import polars as pl
  df = pl.DataFrame(data)
  df.group_by('column').mean()
  ```
- **Testing:** Verify all assets still execute correctly
- **Performance:** Measure execution time before/after

#### **2. Pydantic Config Models**
- **File:** Create `energy_ml/config_models.py`
- **Models to create:**
  ```python
  class BatteryConfig(BaseModel):
      type: Literal['LFP', 'Lead-Acid', 'VRFB']
      capacity_kwh: float
      efficiency: float = 0.95
      
  class UserProfile(BaseModel):
      battery: BatteryConfig
      solar_capacity_kw: float = 0
      business_hours: Dict[int, float]  # hour: load_coefficient
  ```

#### **3. Tenacity Retry Logic**
- **Files:** All API calls in `data_sources.py`
- **Pattern:** 
  ```python
  @retry(stop=stop_after_attempt(3), 
         wait=wait_exponential(multiplier=1, min=4, max=10))
  def fetch_oree_data():
      # existing API call logic
  ```

#### **4. DuckDB Analytics**
- **Purpose:** Fast analytics queries for dashboard
- **Integration:** Add to `mlflow/status.ts` API endpoints
- **Usage:** Replace slow Pandas aggregations

### **Phase 4A Success Criteria:**
- [ ] All assets execute with polars (no pandas)
- [ ] Performance improvement measured (target: 50%+ faster)
- [ ] Pydantic models validate correctly
- [ ] API retry logic handles failures gracefully
- [ ] No functionality regression

## 📋 Phase 4B: Advanced Battery Modeling

### **Priority:** HIGH | **Duration:** 5-7 days

### **Core Tasks:**

#### **1. Battery Type Models**
- **File:** Create `energy_ml/battery_models.py`
- **Models:**
  ```python
  class LFPBattery:
      degradation_cost_per_cycle = 1.35  # USD
      optimal_soc_range = (25, 75)  # %
      cycles_to_eol = 8000
      
  class LeadAcidBattery:
      degradation_cost_per_cycle = 4.59  # USD  
      optimal_soc_range = (20, 80)  # %
      cycles_to_eol = 600
  ```

#### **2. Dynamic Degradation Cost (MC_deg)**
- **Formula:** `C_deg = μ_deg * (P_ch + P_dis) * Δt`
- **Implementation:** Real-time cost calculation per hour
- **Integration:** Feed into Optuna optimization objective

#### **3. SOC Segmentation**
- **Approach:** Divide SOC range into 10 segments
- **Purpose:** Each segment has different degradation coefficient
- **Usage:** More accurate wear calculation

#### **4. Cyclic vs Calendar Aging**
- **Cyclic:** `SOH_cyc = 1 - EFC*(a_cyc*SOC + b_cyc + c_cyc*DOD)`
- **Calendar:** `SOH_cal = 1 - a(T)*t^0.75`
- **Integration:** Combined health prediction

#### **5. Knee Point Prediction**
- **Purpose:** Predict when degradation becomes non-linear
- **Implementation:** Track SEI layer resistance growth
- **Dashboard:** Show time to knee point

### **Dashboard Integration:**
- **New page:** `/health` - Battery health monitoring
- **Components:** SOH trend chart, degradation cost visualization
- **API:** New endpoints for battery health data

### **Phase 4B Success Criteria:**
- [ ] 3 battery types implemented (LFP, Lead-Acid, VRFB)
- [ ] MC_deg calculation working
- [ ] SOC segmentation accurate
- [ ] Knee point prediction functional
- [ ] Dashboard health page operational

## 📋 Phase 4C: Load Profile System

### **Priority:** HIGH | **Duration:** 4-6 days

### **Core Tasks:**

#### **1. Load_Profile_Asset**
- **File:** Create `energy_ml/assets/load_profiles.py`
- **Purpose:** Generate 24-hour consumption patterns
- **Templates:**
  ```python
  STANDARD_WORK = {9: 1.0, 10: 1.0, ..., 17: 1.0, 18: 0.3}  # 9-18 work
  TWO_SHIFT = {6: 1.0, 7: 1.0, ..., 14: 1.0, 22: 1.0, 23: 1.0}
  THREE_SHIFT = {0: 0.8, 1: 0.8, ..., 23: 0.8}  # 24/7
  ```

#### **2. Business Schedule Integration**
- **Input:** User selects template or custom hours
- **Output:** Hourly load coefficients for optimization
- **Economic Logic:** Balance self-consumption vs grid export

#### **3. Consumption Simulation**
- **Integration:** With battery discharge optimization
- **Metrics:** 
  - Daily arbitrage savings
  - Avoided imbalance costs
  - Optimal discharge schedule

### **Dashboard Integration:**
- **New page:** `/profiles` - Load profile configuration
- **Features:** Template selection, custom hour setup, preview charts

### **Phase 4C Success Criteria:**
- [ ] Load profile asset generating correct patterns
- [ ] 4+ business templates working
- [ ] Custom profile creation functional
- [ ] Dashboard profile page operational
- [ ] Integration with optimization working

## 📋 Phase 4D: Ukraine 2026 Tariff System

### **Priority:** MEDIUM | **Duration:** 3-4 days

### **Core Tasks:**

#### **1. NKREKU 2026 Tariff Structure**
- **File:** `energy_ml/ukraine_tariffs.py`
- **Implementation:**
  ```python
  class Ukraine2026Tariffs:
      transmission_q1 = 713.68  # UAH/MWh (Jan-Mar)
      transmission_q2_q4 = 742.91  # UAH/MWh (Apr-Dec)  
      dispatch = 110.03  # UAH/MWh
      price_cap_dam = 15000  # UAH/MWh
      price_cap_balancing = 16000  # UAH/MWh
  ```

#### **2. Date-Based Tariff Switching**
- **Logic:** Auto-switch tariffs on April 1st
- **Integration:** With cost calculation formulas

#### **3. Group A Hourly Pricing**
- **Purpose:** Commercial sector dynamic pricing
- **Integration:** With DAM (Day-Ahead Market) prices

### **Phase 4D Success Criteria:**
- [ ] Tariff structure implemented correctly
- [ ] Date switching functional
- [ ] Price caps enforced
- [ ] Integration with cost calculations working

## 📋 Phase 4E: User Configuration Dashboard

### **Priority:** HIGH | **Duration:** 4-5 days

### **Core Tasks:**

#### **1. Configuration Pages**
- **Pages to create:**
  - `/config` - Battery and solar setup
  - `/profiles` - Business hours configuration  
  - `/economics` - Tariff and cost settings

#### **2. Pydantic Integration**
- **Validation:** All user inputs validated via Pydantic models
- **Error handling:** Clear error messages for invalid configs

#### **3. Profile Management**
- **Features:** Save/load profiles, export/import, templates
- **Storage:** Local storage + database persistence

### **Phase 4E Success Criteria:**
- [ ] Config pages functional and user-friendly
- [ ] Pydantic validation working
- [ ] Profile management operational
- [ ] Integration with Dagster assets working

## 📋 Phase 4F: Integration & Optimization

### **Priority:** HIGH | **Duration:** 2-3 days

### **Final Integration Tasks:**
1. **Component Integration Testing**
2. **ML Pipeline Updates** - Incorporate all new features
3. **Performance Optimization** - Polars optimizations
4. **Documentation Updates** - Complete guides
5. **Production Readiness** - Final testing and validation

## 🧪 Testing Requirements

### **After Each Phase:**
```bash
# Run all tests
pytest tests/ -v

# Performance benchmarks
python benchmarks/phase4_performance.py

# Integration test
python tests/integration/test_full_pipeline.py

# Dashboard test
npm run test --prefix dashboard/
```

### **Before Phase Completion:**
- [ ] All unit tests passing
- [ ] Integration tests passing  
- [ ] Dashboard functionality verified
- [ ] Performance targets met
- [ ] Documentation updated

## 📝 Documentation Requirements

### **Update These Files:**
- `PHASE4_SAAS_UPGRADE_PLAN.md` - Progress tracking
- `README.md` - New features and setup
- `DATA_FLOW_EXPLAINED.md` - New data flows
- Create: `BATTERY_MODELING_GUIDE.md`
- Create: `LOAD_PROFILE_GUIDE.md`
- Create: `USER_CONFIG_GUIDE.md`

## 🎯 Success Metrics

### **Functionality:**
- All v1.0.0 features preserved ✅
- 3+ battery types supported ✅
- 5+ load profile templates ✅  
- Ukraine 2026 tariffs integrated ✅
- User configuration system working ✅

### **Performance:**
- 50%+ faster data processing (polars) ✅
- <30 seconds full pipeline execution ✅
- <3 seconds dashboard load ✅
- 95%+ battery prediction accuracy ✅

### **Production Readiness:**
- Comprehensive testing complete ✅
- Documentation updated ✅
- Clean git history maintained ✅
- v2.0.0 ready for tagging ✅

## 🚀 Final Deliverables

When all phases complete:
1. **Merge to master** - All changes integrated
2. **Tag v2.0.0-saas-ready** - New stable release
3. **Performance report** - Benchmarks vs v1.0.0
4. **Demo scenarios** - Show SaaS capabilities
5. **Production deployment guide** - Ready for scaling

---

**Remember: This system is already production-ready at v1.0.0-stable. We're enhancing it, not fixing it. Preserve all existing functionality while adding the new SaaS features. Test thoroughly at each step!**

## 🎯 MCP Server Usage

### **For Nuxt Dashboard Changes:**
- Use appropriate MCP servers for Vue/Nuxt development
- Ensure type safety with TypeScript
- Test dashboard functionality after each change
- Maintain responsive design principles

### **For Python/Dagster Changes:**
- Use standard Python development practices
- Maintain Dagster asset patterns
- Test asset execution after modifications
- Preserve existing MLflow integration

**Start with Phase 4A and proceed systematically. Good luck!** 🚀