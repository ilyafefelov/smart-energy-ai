# Configuration System Documentation

## Overview

The active configuration flow is centered on tenant-scoped settings consumed by the canonical Nuxt dashboard and the Python bridge. Older Streamlit-era configuration instructions in this repo are obsolete and should not be used as the primary operator path.

## Canonical Runtime Path

- `dashboard/ is the canonical operator UI` for this repository.
- `dashboard/server/api/config/current.get.ts` returns normalized tenant configuration to the UI.
- `dashboard/server/api/config/save.post.ts` validates and persists operator changes.
- `dashboard/app/components/Preferences/OptimizationProfile.vue` is the active operator surface for Stage 2 settings such as connected power and market-regime override.
- `ml_integration_api.py` is the canonical Python bridge that reads the saved configuration during dashboard-driven ML and optimization flows.

## Storage Model

- Tenant settings are persisted under tenant-scoped config locations rather than a single global Streamlit form workflow.
- Dashboard APIs resolve tenant context first, then read or write the relevant config payload.
- The Python side consumes the resolved config through the shared configuration manager contract instead of a separate frontend-specific file format.

## Recommended Usage

### Operator workflow

1. Start the local stack or the dashboard app.
2. Open the dashboard at `http://127.0.0.1:3600`.
3. Use the preferences/config surfaces in `dashboard/` to update runtime settings.
4. Let the dashboard config APIs persist the change and trigger any downstream recalculation behavior.

### API surfaces

- `GET /api/config/current` for the normalized current config.
- `POST /api/config/save` for validated config updates.
- `GET /api/history` for downstream financial telemetry that reflects the saved config.

## Current Notes

- `streamlit_dashboard/` is legacy and should be treated as reference-only.
- `archive/nuxt_dashboard_legacy_20260306/` is archived legacy UI code, not an active config surface.
- New documentation should describe the dashboard plus config API flow, not the older Streamlit workflow.
