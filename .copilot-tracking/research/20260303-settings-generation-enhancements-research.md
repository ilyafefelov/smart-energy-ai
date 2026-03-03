<!-- markdownlint-disable-file -->

# Task Research Notes: Settings Generation Enhancements

## Research Executed

### File Analysis

- `dashboard/app/pages/settings.vue`
	- Current Nuxt app settings shell renders tabbed modules for battery, generation, scenarios, and optimization (`dashboard/app/pages/settings.vue:155`, `dashboard/app/pages/settings.vue:161`, `dashboard/app/pages/settings.vue:171`, `dashboard/app/pages/settings.vue:176`) and includes only summary cards at page level (`dashboard/app/pages/settings.vue:47`).
- `dashboard/app/components/Generation/SolarWindConfig.vue`
	- Current generation UI persists tenant-scoped fields (`latitude`, `longitude`, `timezone`, `solar_capacity_kw`, `wind_capacity_kw`) through `/api/config/current` and `/api/config/save` with `tenantId` and `x-tenant-id` (`dashboard/app/components/Generation/SolarWindConfig.vue:92`, `dashboard/app/components/Generation/SolarWindConfig.vue:118`, `dashboard/app/components/Generation/SolarWindConfig.vue:124`).
- `dashboard/components/Generation/SolarWindConfig.vue` (legacy)
	- Legacy component still contains richer wind/solar controls and simulation fields (`cutInSpeed`, `ratedSpeed`, `systemLosses`) but its save API is commented and non-persistent (`dashboard/components/Generation/SolarWindConfig.vue:524`).
- `dashboard/app/components/Battery/ConfigPanel.vue`
	- Battery type exists as a simple form control and persists through `/api/config/save`, but lacks explanatory card treatment today (`dashboard/app/components/Battery/ConfigPanel.vue:19`, `dashboard/app/components/Battery/ConfigPanel.vue:141`).
- `dashboard/app/components/Scenario/Manager.vue`
	- Scenario/load profile management persists to `/api/config/save` and includes `load_profile_type` but minimal guided UX (`dashboard/app/components/Scenario/Manager.vue:16`, `dashboard/app/components/Scenario/Manager.vue:137`).
- `dashboard/app/components/Preferences/OptimizationProfile.vue`
	- Optimization strategy is canonicalized and mapped between UI IDs and API values, then persisted via `/api/config/save` (`dashboard/app/components/Preferences/OptimizationProfile.vue:73`, `dashboard/app/components/Preferences/OptimizationProfile.vue:114`, `dashboard/app/components/Preferences/OptimizationProfile.vue:165`).
- `dashboard/app/stores/settingsStore.ts`
	- App store schema is limited to `general/battery/notifications/model` and uses `/api/settings/load|save` + localStorage fallback, separate from operational config domain (`dashboard/app/stores/settingsStore.ts:35`, `dashboard/app/stores/settingsStore.ts:98`, `dashboard/app/stores/settingsStore.ts:165`).
- `dashboard/stores/settingsStore.ts` (legacy)
	- Legacy store includes broader `userConfig` domain model, confirming prior support for richer settings families (`dashboard/stores/settingsStore.ts:33`, `dashboard/stores/settingsStore.ts:82`).
- `dashboard/server/api/config/current.get.ts`
	- Tenant-aware config read path includes defaults for `optimization_strategy`, `solar_capacity_kw`, `wind_capacity_kw`, and location fields (`dashboard/server/api/config/current.get.ts:19`, `dashboard/server/api/config/current.get.ts:69`, `dashboard/server/api/config/current.get.ts:71`).
- `dashboard/server/api/config/save.post.ts`
	- Tenant-aware save merges incoming config and recalculation triggers on significant fields including optimization/generation/location (`dashboard/server/api/config/save.post.ts:92`, `dashboard/server/api/config/save.post.ts:112`, `dashboard/server/api/config/save.post.ts:265`, `dashboard/server/api/config/save.post.ts:268`).
- `dashboard/server/api/retraining/start.ts`
	- Retraining start is tenant-scoped and passes tenant config env vars to Python (`dashboard/server/api/retraining/start.ts:34`, `dashboard/server/api/retraining/start.ts:90`).
- `dashboard/server/api/retraining/progress.ts`
	- Progress/metrics artifacts are tenant-scoped under `data/tenants/<tenantId>/retraining` (`dashboard/server/api/retraining/progress.ts:13`, `dashboard/server/api/retraining/progress.ts:23`, `dashboard/server/api/retraining/progress.ts:50`).
- `scripts/train_model.py`
	- Training metrics persist the effective `used_config`, including optimization strategy and solar/wind/location fields, verifying end-to-end training input capture (`scripts/train_model.py:124`, `scripts/train_model.py:125`, `scripts/train_model.py:131`, `scripts/train_model.py:132`).
- `energy_ml/user_config.py`
	- ML schema explicitly supports `optimization_strategy`, `solar_capacity_kw`, `wind_capacity_kw`, `latitude`, and `longitude` (`energy_ml/user_config.py:58`, `energy_ml/user_config.py:62`, `energy_ml/user_config.py:63`, `energy_ml/user_config.py:64`).
- `dashboard/server/api/ml/recommendation.get.ts`
	- Runtime recommendation path is tenant-aware and forwards tenant-specific ML config env (`dashboard/server/api/ml/recommendation.get.ts:47`, `dashboard/server/api/ml/recommendation.get.ts:65`, `dashboard/server/api/ml/recommendation.get.ts:66`).
- `dashboard/server/api/ml/predict.ts`
	- Predict endpoint executes Python recommendation flow but has no tenant-resolution call in handler scope, creating tenant consistency risk vs other ML endpoints (`dashboard/server/api/ml/predict.ts:63`, `dashboard/server/api/ml/predict.ts:69`, `dashboard/server/api/ml/predict.ts:79`).
- `dashboard/server/api/ml/recalculate.post.ts`, `dashboard/server/api/ml/recalculate-status.get.ts`
	- Recalculation status is global file based (`../energy_ml/configs/recalculation_status.json`) and not tenant-partitioned (`dashboard/server/api/ml/recalculate.post.ts:15`, `dashboard/server/api/ml/recalculate-status.get.ts:13`).
- `dashboard/server/utils/tenant-context.ts`
	- Canonical tenant resolution order is body -> query -> headers -> default (`dashboard/server/utils/tenant-context.ts:171`, `dashboard/server/utils/tenant-context.ts:179`, `dashboard/server/utils/tenant-context.ts:190`).
- `dashboard/server/api/settings/export.ts`, `dashboard/server/api/settings/import.ts`
	- Settings import/export APIs are tenant-aware and write `data/tenants/<tenantId>/settings.json` (`dashboard/server/api/settings/export.ts:7`, `dashboard/server/api/settings/export.ts:9`, `dashboard/server/api/settings/import.ts:24`, `dashboard/server/api/settings/import.ts:27`).
- `dashboard/COMPLETE_SETTINGS_FIX.md`
	- Historical doc still references a localStorage-only fix path, which is partially superseded by current tenant config APIs (`dashboard/COMPLETE_SETTINGS_FIX.md:6`, `dashboard/COMPLETE_SETTINGS_FIX.md:36`).

### Code Search Results

- `GenerationSolarWindConfig|ScenarioManager|PreferencesOptimizationProfile`
	- Confirmed current settings tab composition and active module mount points in `dashboard/app/pages/settings.vue` (6+ matches).
- `solar_capacity_kw|wind_capacity_kw|timezone|latitude|longitude` (app generation component)
	- Confirmed UI controls, defaults, and load/save wiring in `dashboard/app/components/Generation/SolarWindConfig.vue` (20 matches).
- `/api/generation/config|saveConfiguration` (legacy generation component)
	- Found commented save API and simulation-oriented behavior in `dashboard/components/Generation/SolarWindConfig.vue` (4 matches).
- `optimization_strategy|solar_capacity_kw|wind_capacity_kw` (config APIs)
	- Verified default and significant-change recalculation fields in `dashboard/server/api/config/current.get.ts` and `dashboard/server/api/config/save.post.ts` (16 matches combined).
- `resolveTenantContext|ENERGY_ML_CONFIG_DIR|ENERGY_ML_TENANT_ID`
	- Verified tenant-scoped retraining and recommendation endpoints; no equivalent predict endpoint match for tenant resolver (cross-endpoint consistency gap).
- `recalculation_status.json`
	- Verified global status file usage in recalc endpoints (2 matches).

### External Research

- #githubRepo:"nuxt/nuxt server api handler methods"
	- Nuxt server conventions confirm method-scoped handlers (`*.get.ts`, `*.post.ts`), `readBody`/`getQuery`, and route auto-registration under `server/api`, aligning with current API architecture and supporting endpoint harmonization strategy.
- #githubRepo:"vuejs/pinia state store definition persistence patterns"
	- Pinia docs confirm all mutable state keys must be declared upfront and persistence can be implemented via `$subscribe`/storage patterns, supporting consolidation strategy for settings domains.
- #fetch:https://nuxt.com/docs/4.x/guide/directory-structure/server
	- Verified official server route/file naming and request helper guidance relevant to tenant-safe endpoint refactor.
- #fetch:https://pinia.vuejs.org/core-concepts/state.html
	- Verified direct state mutation, `$patch`, and declared-state constraints, relevant to avoiding split schemas.
- #fetch:https://www.nngroup.com/articles/cards-component/
	- Card UI best use: grouping heterogeneous content, clear visual grouping via common regions, and careful scanability trade-offs.
- #fetch:https://www.nngroup.com/articles/progressive-disclosure/
	- Progressive disclosure reduces novice error and improves efficiency by showing core settings first and advanced options on demand.

### Project Conventions

- Standards referenced: `AGENTS.md` (mandatory beads-first workflow, tenant-aware operational context), `VueJS 3 Development Instructions` (Composition API + Pinia conventions), Nuxt server conventions from official docs.
- Instructions followed: research-only scope enforced (no source-code changes), findings recorded only in `.copilot-tracking/research/`.

## Key Discoveries

### Project Structure

Settings currently operate through two parallel persistence systems:

1. UI/general system: `dashboard/app/stores/settingsStore.ts` + `/api/settings/*` + localStorage fallback (`dashboard/app/stores/settingsStore.ts:98`, `dashboard/app/stores/settingsStore.ts:165`).
2. Operational/ML system: `app/components/*` -> `/api/config/current|save` -> tenant `energy_ml/configs/tenants/<id>/user_config.json` (`dashboard/server/api/config/current.get.ts:20`, `dashboard/server/api/config/save.post.ts:82`).

The operational system is already where generation and optimization values are persisted for ML use; the remaining risk is cross-endpoint tenant consistency and UX clarity.

### Implementation Patterns

- Canonical operational flow is tenant-first:
	- UI sends `tenantId` in query/header/body.
	- API resolves tenant via `resolveTenantContext`.
	- API reads/writes tenant-scoped config and may trigger recalculation.
- Current gap pattern:
	- Some ML endpoints (`recommendation.get.ts`, retraining) are tenant-aware.
	- Others (`ml/predict.ts`, recalculate status file) are not tenant-partitioned.
- UX pattern gap:
	- Settings tabs are functional, but explanatory card content is shallow and inconsistent across Battery/Scenario/Optimization modules.

### Complete Examples

```ts
// Source: dashboard/server/api/config/save.post.ts + dashboard/server/api/retraining/start.ts
// Verified tenant-scoped save + recalculation criteria + retraining env handoff.

const tenant = await resolveTenantContext(event, { body })
const { configPath, sourcePath } = resolveConfigPaths(tenant.id)

const mergedConfig = {
	...currentConfig,
	...sanitizedBody,
}
mergedConfig.optimization_strategy = normalizeOptimizationStrategy(mergedConfig.optimization_strategy)

const needsRecalculation = detectSignificantChanges(currentConfig, newConfig)

const significantFields = [
	'optimization_strategy',
	'latitude',
	'longitude',
	'solar_capacity_kw',
	'wind_capacity_kw',
]

const trainProcess = spawn('python', [pythonScript, '--tenant-id', tenant.id, '--config', JSON.stringify(body)], {
	env: {
		...process.env,
		ENERGY_ML_CONFIG_DIR: tenantConfigDir,
		ENERGY_ML_TENANT_ID: tenant.id,
	},
})
```

### API and Schema Documentation

- Generation and optimization fields used by ML:
	- `optimization_strategy`: `energy_ml/user_config.py:58`
	- `solar_capacity_kw`: `energy_ml/user_config.py:62`
	- `wind_capacity_kw`: `energy_ml/user_config.py:63`
	- `latitude`/`longitude`: `energy_ml/user_config.py:64`
- Training evidence that values are consumed and recorded:
	- `scripts/train_model.py:124`-`scripts/train_model.py:135` (`used_config` payload)
- Endpoint role map:
	- Read config: `GET /api/config/current` (`dashboard/server/api/config/current.get.ts:19`)
	- Write config: `POST /api/config/save` (`dashboard/server/api/config/save.post.ts:92`)
	- Start retrain: `POST /api/retraining/start` (`dashboard/server/api/retraining/start.ts:34`)
	- Recommendation: `GET /api/ml/recommendation` (`dashboard/server/api/ml/recommendation.get.ts:47`)

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

Default values verified in `dashboard/server/api/config/current.get.ts:69`-`dashboard/server/api/config/current.get.ts:75`.

### Technical Requirements

1. Keep generation settings on canonical `/api/config/*` + tenant config path; do not reintroduce legacy non-persistent save flow.
2. Restore advanced generation controls only if mapped to schema-backed fields in `energy_ml/user_config.py`; avoid orphan UI knobs.
3. Keep optimization strategy in one canonical UI entry point (`Preferences/OptimizationProfile.vue`) and one canonical storage field (`optimization_strategy`).
4. Unify tenant behavior across all ML endpoints before claiming end-to-end correctness:
	- Tenant-aware now: `ml/recommendation`, retraining.
	- High risk: `ml/predict` and global `recalculation_status.json` usage.
5. Add explanatory cards using progressive disclosure:
	- Primary cards: intent, outcomes, recommended defaults.
	- Advanced panels: reveal secondary parameters only on demand.

## Recommended Approach

Selected approach: extend the current Nuxt app components and tenant-scoped `/api/config/*` pipeline, and do not reuse the legacy generation component as-is.

Why this is the optimal path based on evidence:

1. Current app components already persist core generation/optimization/scenario values through tenant-scoped APIs (`dashboard/app/components/Generation/SolarWindConfig.vue:118`, `dashboard/app/components/Preferences/OptimizationProfile.vue:165`, `dashboard/app/components/Scenario/Manager.vue:137`).
2. Backend save path already triggers recalculation on exactly the relevant generation/optimization/location fields (`dashboard/server/api/config/save.post.ts:265`, `dashboard/server/api/config/save.post.ts:268`).
3. Retraining and recommendation APIs already consume tenant-scoped config context, so preserving this path minimizes integration risk (`dashboard/server/api/retraining/start.ts:90`, `dashboard/server/api/ml/recommendation.get.ts:65`).
4. Legacy generation UI is feature-rich but non-persistent by design in current state (`dashboard/components/Generation/SolarWindConfig.vue:524`), making direct reuse unsafe.

UX direction within this selected path:

1. Add explanatory cards to Battery Type, Scenario Profile, and Optimization Strategy modules with concise "When to use" and "Expected tradeoff" text.
2. Add optional advanced accordions for generation details (wind curve and solar system factors), gated by progressive disclosure and bound only to schema-backed fields.
3. Maintain one source of truth for strategy and generation fields in operational config; avoid duplicating same control in multiple tabs.

## Implementation Guidance

- **Objectives**: Strengthen settings UX clarity while preserving tenant-scoped persistence and ML pipeline correctness for generation/strategy/scenario inputs.
- **Key Tasks**: (1) enrich card UX in battery/scenario/optimization modules, (2) add advanced generation controls mapped to persistent schema fields, (3) align all ML endpoints to tenant-context resolver and tenant-scoped status artifacts, (4) remove/retire stale localStorage-only narratives in docs.
- **Dependencies**: `dashboard/app/components/*` settings modules, `dashboard/server/api/config/*`, `dashboard/server/api/ml/*`, `dashboard/server/api/retraining/*`, `energy_ml/user_config.py`, `scripts/train_model.py`, tenant resolver utility.
- **Success Criteria**: generation and strategy changes are saved per tenant, visible in `user_config.json`, reflected in retraining `used_config`, consumed by recommendation/predict/recalc flows with consistent tenant scoping, and accompanied by clear explanatory card UX for end users.
