---
applyTo: '.copilot-tracking/changes/20260303-customer-dashboard-system-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Customer Dashboard System

## Overview

Implement tenant-aware dashboard API and UI flows so metrics and control surfaces are scoped to the selected customer without cross-tenant leakage.

## Objectives

- Enforce a tenant-context contract from dashboard request boundaries through API handlers and persistence/query paths.
- Deliver tenant-scoped dashboard UX plus automated API/e2e/smoke guardrails for no-leakage verification across at least two configured tenants.

## Research Summary

### Project Files

- `dashboard/app/pages/control.vue` - Current control page sends unscoped requests and static user identity.
- `dashboard/app/stores/metricsStore.ts` - Metrics store currently fetches tenant-agnostic data.
- `dashboard/server/api/history.ts` - Current SQL aggregation has no tenant predicate.
- `dashboard/server/api/metrics/dashboard.ts` - Dashboard metrics endpoint composes multiple unscoped internal calls.
- `dashboard/server/utils/optimization-history.ts` - Canonical economics persistence schema currently lacks `tenant_id`.
- `src/assets/multi_tenant/asset_factory.py` - Existing tenant namespace and leakage guard pattern to reuse.

### External References

- #file:../research/20260303-customer-dashboard-system-research.md - Verified implementation evidence and tenant-scoping recommendations.
- #githubRepo:"nuxt/nuxt server directory api routes defineEventHandler" - Nuxt server route/method conventions for tenant-aware endpoints.
- #githubRepo:"microsoft/api-guidelines azure api idempotency error schema collections filtering" - API filtering and stable contract patterns.
- #fetch:https://nuxt.com/docs/4.x/guide/directory-structure/server - Practical Nuxt route and handler examples.
- #fetch:https://learn.microsoft.com/en-us/azure/architecture/guide/multitenant/considerations/map-requests - Tenant mapping strategies.
- #fetch:https://learn.microsoft.com/en-us/azure/architecture/guide/multitenant/approaches/storage-data - Multitenant storage isolation patterns.

### Standards References

- #file:../../AGENTS.md - Beads-first workflow and completion requirements.
- #file:../../dashboard/nuxt.config.ts - Nuxt app directory and store conventions.
- #file:../../dashboard/CODEX_MCP_GUIDE.md - Dashboard runtime guidance and validation operations.

## Implementation Checklist

### [ ] Phase 1: Tenant Context and API Boundary

- [ ] Task 1.1: Add tenant resolution and validation contract
  - Details: .copilot-tracking/details/20260303-customer-dashboard-system-details.md (Lines 11-29)

- [ ] Task 1.2: Enforce tenant scoping for metrics/history/control reads
  - Details: .copilot-tracking/details/20260303-customer-dashboard-system-details.md (Lines 31-52)

### [ ] Phase 2: Tenant-Scoped Persistence and State

- [ ] Task 2.1: Add tenant key to optimization history contract
  - Details: .copilot-tracking/details/20260303-customer-dashboard-system-details.md (Lines 56-76)

- [ ] Task 2.2: Partition file-backed runtime state by tenant
  - Details: .copilot-tracking/details/20260303-customer-dashboard-system-details.md (Lines 78-102)

### [ ] Phase 3: Tenant-Aware Dashboard UX and Guardrails

- [ ] Task 3.1: Add frontend tenant selector and request propagation
  - Details: .copilot-tracking/details/20260303-customer-dashboard-system-details.md (Lines 106-129)

- [ ] Task 3.2: Add tenant isolation tests and smoke assertions
  - Details: .copilot-tracking/details/20260303-customer-dashboard-system-details.md (Lines 131-149)

## Dependencies

- Claimed Beads issue `smart-energy-ai-djb` in `in_progress` state.
- `customers.yaml` tenant definitions as request-validation source of truth.
- Dashboard API runtime (`3600`) and Dagster runtime (`3000`) available for verification.
- PostgreSQL connectivity for tenant-scoped `optimization_history` reads/writes.

## Success Criteria

- Tenant metadata is resolved, validated, and propagated across dashboard API responses.
- Dashboard metrics/control/settings/retraining paths are tenant-scoped and no longer use shared unscoped reads.
- Automated API/e2e/smoke tests include tenant no-leakage assertions and pass for at least two tenant IDs.
