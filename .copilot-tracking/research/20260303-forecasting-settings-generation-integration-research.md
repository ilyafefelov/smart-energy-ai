<!-- markdownlint-disable-file -->

# Task Research Notes: Forecasting Settings Generation Integration

## Research Executed

### File Analysis

- `dashboard/nuxt.config.ts`
  - Active Nuxt app root is `app/` (`srcDir: 'app'`), so `dashboard/app/**` is the primary runtime path for pages/stores/components.
- `dashboard/app/pages/settings.vue`
  - Current settings UX entrypoint with tabbed cards and mixed save paths (general/notifications/model via `settingsStore`, battery/generation/scenarios/preferences via dedicated components).
- `dashboard/app/stores/settingsStore.ts`
  - Persists only `general/battery/notifications/model` shape via `/api/settings/load` and `/api/settings/save`.
- `dashboard/server/api/settings/load.ts`
  - Loads tenant dashboard settings from `dashboard/data/tenants/<tenant>/settings.json` with defaults.
- `dashboard/server/api/settings/save.ts`
  - Saves tenant dashboard settings into `dashboard/data/tenants/<tenant>/settings.json`.
- `dashboard/server/api/config/current.get.ts`
  - Loads full ML/user config (including optimization + generation + location) from tenant `energy_ml/configs/tenants/<tenant>/user_config.json` with fallback.
- `dashboard/server/api/config/save.post.ts`
  - Saves full ML/user config tenant-scoped, tracks history, and writes recalculation triggers.
- `dashboard/app/components/Battery/ConfigPanel.vue`
  - Reads/writes battery config through `/api/config/current` and `/api/config/save` then mirrors summary fields back into `settingsStore`.
- `dashboard/app/components/Generation/SolarWindConfig.vue`
  - Reads/writes generation and location settings through `/api/config/current` and `/api/config/save`.
- `dashboard/app/components/Scenario/Manager.vue`
  - Reads/writes load scenario fields through `/api/config/current` and `/api/config/save`.
- `dashboard/app/components/Preferences/OptimizationProfile.vue`
  - Reads/writes optimization strategy/custom weights and selected ML horizon fields through `/api/config/*`.
- `dashboard/app/stores/mlStore.ts`
  - Fetches `/api/ml/recommendation` without tenant headers and stores only top-level recommendation/savings.
- `dashboard/server/api/ml/recommendation.get.ts`
  - Passes tenant-specific env (`ENERGY_ML_CONFIG_DIR`, `ENERGY_ML_TENANT_ID`) to Python subprocess.
- `dashboard/server/api/ml/predict.ts`
  - Uses Python subprocess + heuristic fallback, but does not pass tenant env vars.
- `dashboard/app/components/ML/ForecastChart.vue`
  - Derives BUY/SELL/HOLD from `pricesStore.forecast` and average-price thresholds, not from ML hourly forecast payload.
- `dashboard/app/stores/pricesStore.ts`
  - Forecast source for chart is `/api/prices/current` response and internal threshold logic.
- `ml_integration_api.py`
  - CLI bridge returns recommendation + hourly forecast and supports enhanced mode with optimization/physics/renewables integration.
- `energy_ml/pipeline.py`
  - Core recommendation pipeline uses several mock/static values (SOC/health/load coeff assumptions).
- `energy_ml/features.py`
  - Produces fixed 14-feature vector; battery and load features include mocked assumptions.
- `energy_ml/ml_integration.py`
  - Prediction service expects only 14 features (no explicit renewable feature columns).
- `energy_ml/user_config.py`
  - Rich config model includes optimization strategy, solar/wind/location and uses `extra='allow'`.
- `dashboard/server/api/retraining/start.ts`
  - Tenant-aware retraining launcher passes config overrides and tenant env to script.
- `scripts/train_model.py`
  - Retraining script is explicitly simulation-based but writes tenant artifacts and merged config.
- `dashboard/server/api/renewable/forecast.get.ts`
  - Python-backed renewable forecast endpoint.
- `dashboard/server/api/renewable/forecast.ts`
  - Separate deterministic simulation endpoint for same route namespace with query-driven capacities.
- `dashboard/app/pages/configuration.vue`
  - Legacy/stale page references non-existent store API shape (`saveConfig/loadConfig/settings.userConfig`).

### Code Search Results

- `srcDir:\s*'app'`
  - Found in `dashboard/nuxt.config.ts:5`; confirms active app path.
- `/api/settings/load|/api/settings/save`
  - Found in `dashboard/app/stores/settingsStore.ts:98`, `dashboard/app/stores/settingsStore.ts:165`.
- `/api/config/current|/api/config/save`
  - Found across active settings subcomponents:
  - `dashboard/app/components/Battery/ConfigPanel.vue:113`
  - `dashboard/app/components/Battery/ConfigPanel.vue:141`
  - `dashboard/app/components/Generation/SolarWindConfig.vue:92`
  - `dashboard/app/components/Generation/SolarWindConfig.vue:118`
  - `dashboard/app/components/Scenario/Manager.vue:110`
  - `dashboard/app/components/Scenario/Manager.vue:137`
  - `dashboard/app/components/Preferences/OptimizationProfile.vue:127`
  - `dashboard/app/components/Preferences/OptimizationProfile.vue:165`
- `settings.json` persistence
  - Found in `dashboard/server/api/settings/load.ts:20`, `dashboard/server/api/settings/save.ts:20`.
- `tenant user_config.json` persistence
  - Found in `dashboard/server/api/config/current.get.ts:20`, `dashboard/server/api/config/save.post.ts:82`.
- `ENERGY_ML_TENANT_ID`
  - Found in recommendation path `dashboard/server/api/ml/recommendation.get.ts:66`.
- `ml_integration_api.py` predict path + fallback
  - Found in `dashboard/server/api/ml/predict.ts:69`, `dashboard/server/api/ml/predict.ts:91`, `dashboard/server/api/ml/predict.ts:146`.
- `optimization_strategy|solar_capacity_kw|wind_capacity_kw`
  - Found in `energy_ml/user_config.py:58`, `energy_ml/user_config.py:62`, `energy_ml/user_config.py:63`.
- `hourly_coefficients=standard_coefficients`
  - Found in `energy_ml/pipeline.py:97`.
- `EXPECTED_FEATURES`
  - Found in `energy_ml/ml_integration.py:35` (14-feature schema).
- `simulate training`
  - Found in `scripts/train_model.py:6` and staged sleep-based training flow.
- stale configuration-page store usage
  - Found in `dashboard/app/pages/configuration.vue:358`, `dashboard/app/pages/configuration.vue:389`, `dashboard/app/pages/configuration.vue:295`.

### External Research

- #githubRepo:"nuxt/nuxt server route method suffix .get .post"
  - Nuxt server routing docs show method-suffixed handlers (`*.get.ts`, `*.post.ts`) are method-specific and return `405` for non-matching methods. This is relevant to `forecast.get.ts` vs `forecast.ts` coexistence and route behavior.
- #githubRepo:"vuejs/pinia core concepts setup store storeToRefs"
  - Pinia setup stores require returning all reactive state; direct destructuring of store object breaks reactivity, use `storeToRefs` for reactive extraction.
- #githubRepo:"pydantic/pydantic models extra allow forbid ignore"
  - Pydantic `extra` modes (`ignore/forbid/allow`) confirmed. `extra='allow'` permits unmodeled keys, reducing strict schema guardrails unless explicit validation constraints are added.
- #fetch:https://raw.githubusercontent.com/nuxt/nuxt/4.x/docs/2.directory-structure/1.server.md
  - Confirmed Nuxt 4 method-based route matching and `/server/api` behavior.
- #fetch:https://raw.githubusercontent.com/vuejs/pinia/v3/packages/docs/core-concepts/index.md
  - Confirmed Pinia setup-store behavior and reactivity constraints.
- #fetch:https://raw.githubusercontent.com/pydantic/pydantic/main/docs/concepts/models.md
  - Confirmed validation patterns, `model_validate`, and `extra` handling semantics.

### Project Conventions

- Standards referenced: `AGENTS.md` beads-first workflow, tenant-first API conventions in `dashboard/server/utils/tenant-context.ts`, Vue/Pinia composition practices from `vuejs3.instructions.md`.
- Instructions followed: `AGENTS.md`, `vscode-userdata:/.../vuejs3.instructions.md`, `vscode-userdata:/.../task-implementation.instructions.md` (scope acknowledged; applyTo is `**/.copilot-tracking/changes/*.md`).

## Key Discoveries

### Project Structure

- Active runtime path is `dashboard/app/**` because `dashboard/nuxt.config.ts:5` sets `srcDir: 'app'`.
- The codebase currently contains parallel store trees in both `dashboard/app/stores/*.ts` and `dashboard/stores/*.ts`, increasing integration ambiguity.
- `dashboard/app/stores/batteryPhysicsStore.ts:1` re-exports from root `dashboard/stores/batteryPhysicsStore.ts`, evidencing mixed layering.
- Settings UX exists in two places:
  - Active modern tabbed page: `dashboard/app/pages/settings.vue`.
  - Legacy/stale page: `dashboard/app/pages/configuration.vue`.

### Implementation Patterns

- Pattern A: Dashboard UI preferences path (`/api/settings/*`)
  - Store-level persistence for `general/battery/notifications/model` through `dashboard/app/stores/settingsStore.ts:98` and `dashboard/app/stores/settingsStore.ts:165`.
  - Backed by tenant dashboard file storage in `dashboard/server/api/settings/load.ts:20` and `dashboard/server/api/settings/save.ts:20`.
- Pattern B: Full ML/system config path (`/api/config/*`)
  - Settings tab components persist battery/generation/scenarios/preferences to config API (`dashboard/app/components/Battery/ConfigPanel.vue:141`, `dashboard/app/components/Generation/SolarWindConfig.vue:118`, `dashboard/app/components/Scenario/Manager.vue:137`, `dashboard/app/components/Preferences/OptimizationProfile.vue:165`).
  - Backed by tenant `user_config.json` in `dashboard/server/api/config/current.get.ts:20` and `dashboard/server/api/config/save.post.ts:82`.
- Pattern C: ML recommendation fetch
  - Frontend `mlStore` calls `/api/ml/recommendation` without explicit tenant request metadata (`dashboard/app/stores/mlStore.ts:33`).
  - API backend does support tenant env handoff to Python (`dashboard/server/api/ml/recommendation.get.ts:66`).

### Complete Examples

```ts
// Evidence: dual persistence paths in active UI
// 1) Dashboard settings store -> /api/settings/*
const response = await $fetch('/api/settings/load', {
  query: { tenantId },
  headers: { 'x-tenant-id': tenantId },
})

// 2) Battery/Generation/Scenario/Preferences tabs -> /api/config/*
const response = await $fetch('/api/config/save', {
  method: 'POST',
  query: { tenantId },
  headers: { 'x-tenant-id': tenantId },
  body: { ...form, tenantId },
})
```

### API and Schema Documentation

- `settings` API shape (dashboard preferences): `general`, `battery`, `notifications`, `model`.
- `config` API shape (full ML/system): battery/load/tariff/ML/dashboard prefs + optimization strategy + custom weights + solar/wind/location.
- Python config schema (`UserConfigModel`) includes generation and optimization fields:
  - `optimization_strategy` in `energy_ml/user_config.py:58`
  - `solar_capacity_kw` in `energy_ml/user_config.py:62`
  - `wind_capacity_kw` in `energy_ml/user_config.py:63`
- Model permissiveness: `extra='allow'` in `energy_ml/user_config.py:74`.

### Configuration Examples

```json
{
  "optimization_strategy": "balanced",
  "solar_capacity_kw": 0,
  "wind_capacity_kw": 0,
  "latitude": 50.45,
  "longitude": 30.52,
  "timezone": "Europe/Kiev"
}
```

### Technical Requirements

#### Top 10 Gaps (Evidence-Backed)

1. Split source of truth for settings/configuration causes drift between tabs and persisted artifacts.
   - `dashboard/app/stores/settingsStore.ts:98`
   - `dashboard/app/components/Battery/ConfigPanel.vue:141`
   - `dashboard/server/api/settings/save.ts:20`
   - `dashboard/server/api/config/save.post.ts:82`
2. Legacy per-domain settings endpoints still write non-tenant global config and bypass tenant guardrails.
   - `dashboard/server/api/settings/battery.post.ts:50`
   - `dashboard/server/api/settings/load-profile.post.ts:60`
3. ML recommendation request from frontend is not tenant-explicit; default tenant fallback can silently serve wrong tenant data.
   - `dashboard/app/stores/mlStore.ts:33`
   - `dashboard/server/utils/tenant-context.ts:221`
4. `ml/predict` path lacks tenant env propagation while `ml/recommendation` includes it; behavior diverges across ML endpoints.
   - `dashboard/server/api/ml/recommendation.get.ts:66`
   - `dashboard/server/api/ml/predict.ts:79`
   - `dashboard/server/api/ml/predict.ts:91`
5. Forecast visualization logic is heuristic from price averages, not ML hourly forecast actions/reasoning.
   - `dashboard/app/components/ML/ForecastChart.vue:73`
   - `dashboard/app/components/ML/ForecastChart.vue:86`
   - `dashboard/app/components/ML/ForecastChart.vue:89`
6. ML API returns rich hourly/daily forecast context, but store/UI only retain top-level recommendation and savings.
   - `dashboard/server/api/ml/recommendation.get.ts:84`
   - `dashboard/app/stores/mlStore.ts:5`
   - `dashboard/app/stores/mlStore.ts:38`
7. Core pipeline uses mocked SOC/health and fixed load coefficients, reducing personalization realism.
   - `energy_ml/pipeline.py:97`
   - `energy_ml/pipeline.py:144`
   - `energy_ml/pipeline.py:145`
8. Feature pipeline remains a 14-feature schema without explicit renewable/location features and includes mocked battery/load assumptions.
   - `energy_ml/features.py:21`
   - `energy_ml/features.py:207`
   - `energy_ml/features.py:263`
   - `energy_ml/ml_integration.py:35`
9. Retraining flow is simulation-first despite tenant-aware plumbing; production expectations can be overstated.
   - `scripts/train_model.py:6`
   - `scripts/train_model.py:72`
   - `scripts/train_model.py:84`
10. Two renewable forecast handlers exist (`forecast.get.ts` and `forecast.ts`) with different data sources/semantics, creating maintainability and behavior ambiguity.
   - `dashboard/server/api/renewable/forecast.get.ts:65`
   - `dashboard/server/api/renewable/forecast.ts:6`

#### Highest-Risk Integration Points

1. Tenant isolation risk in recommendation fetch path.
   - If frontend omits tenant metadata, resolver defaults to first tenant (`dashboard/server/utils/tenant-context.ts:221`) and can leak cross-tenant recommendations.
2. Settings/config divergence risk.
   - User-visible values can disagree because `/api/settings/*` and `/api/config/*` persist different schemas to different files.
3. Forecast action correctness risk.
   - UI action badges in forecast are generated from average-price heuristics, not ML `hourly_forecast` decisions.
4. Endpoint behavior divergence risk.
   - `ml/predict` vs `ml/recommendation` tenant/env differences can produce inconsistent recommendations for same tenant/session.
5. Legacy endpoint overwrite risk.
   - Global config writes from legacy settings routes can overwrite tenant assumptions if called.

## Recommended Approach

Adopt a single tenant-scoped "Configuration Contract" centered on `/api/config/*` and make all forecasting/recommendation rendering consume the same ML payload contract.

Selected approach details:
- Canonical persistence: keep `energy_ml/configs/tenants/<tenant>/user_config.json` as authoritative for all optimization/generation/model parameters.
- Compatibility adapter: keep `/api/settings/*` only as a thin view-model adapter to `/api/config/*` for UX fields needed by existing cards; avoid direct independent persistence.
- Tenant hardening: require explicit tenant propagation for all ML requests from frontend stores and normalize server handlers to reject ambiguous tenant-less write/read flows.
- Forecast wiring: feed `ForecastChart` from ML `hourly_forecast` (action/reasoning/confidence) and use price-store forecast only for raw market series overlays.
- Legacy containment: mark `settings/battery.post.ts`, `settings/load-profile.post.ts`, and stale `configuration.vue` as deprecated path candidates and remove from active navigation/consumers.
- Consistent route ownership: keep one renewable GET implementation path and fold capabilities into one contract.

## Implementation Guidance

- **Objectives**: Establish one end-to-end tenant-safe settings-to-ML pipeline where saved settings deterministically influence recommendation generation and forecast display.
- **Key Tasks**: Consolidate persistence APIs, align store contracts, pass tenant context in all ML client calls, bind chart rendering to ML hourly forecast, and deprecate legacy route/page/store paths.
- **Dependencies**: Nuxt server routing (`*.get.ts`/`*.post.ts`), Pinia store contract updates, tenant resolver behavior, Python `ConfigurationManager` and model feature contracts.
- **Success Criteria**: Saving any generation/optimization/model setting updates tenant `user_config.json`, retraining/recommendation endpoints read same tenant config, dashboard forecast actions match ML hourly output, and no active UI path writes global non-tenant config.
