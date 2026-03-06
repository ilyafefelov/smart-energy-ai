<!-- markdownlint-disable-file -->
# Release Changes: SaaS Billing Integration Framework

**Related Plan**: `.copilot-tracking/plans/20260303-saas-billing-integration-framework-plan.instructions.md`
**Implementation Date**: 2026-03-03

## Summary

Implemented a tenant-scoped billing framework with usage event capture hooks, entitlement-aware draft charge calculation, and a billing draft API for multi-tenant validation flows.

## Changes

### Added

- `.copilot-tracking/plans/20260303-saas-billing-integration-framework-plan.instructions.md` - Added implementation plan for billing framework delivery and validation.
- `.copilot-tracking/changes/20260303-saas-billing-integration-framework-changes.md` - Added release tracking document for billing framework workstream.
- `dashboard/server/utils/billing.ts` - Added billing event model, tenant-scoped event persistence, plan entitlements, provider abstraction, and default local rate-card provider.
- `dashboard/server/api/billing/draft.get.ts` - Added tenant-aware billing draft invoice endpoint with period and include-events controls.
- `tests/test_dashboard_billing_api.py` - Added integration test that verifies usage capture and draft invoice isolation across multiple tenants.

### Modified

- `dashboard/server/api/control/execute.post.ts` - Added non-blocking billing usage capture hooks for command execution outcomes.
- `dashboard/server/api/control/schedule.post.ts` - Added non-blocking billing usage capture hooks for schedule creation outcomes.

### Removed

- None.

## Release Summary

### Files Created

- `.copilot-tracking/plans/20260303-saas-billing-integration-framework-plan.instructions.md` - Task plan and completion checklist for billing integration.
- `.copilot-tracking/changes/20260303-saas-billing-integration-framework-changes.md` - Progressive and release summary tracking for this implementation.
- `dashboard/server/utils/billing.ts` - Core billing framework internals and provider abstraction surface.
- `dashboard/server/api/billing/draft.get.ts` - Runtime API for tenant-scoped draft invoice generation.
- `tests/test_dashboard_billing_api.py` - Multi-tenant integration checks for draft billing behavior.

### Files Modified

- `dashboard/server/api/control/execute.post.ts` - Emits billing usage events for executed control commands.
- `dashboard/server/api/control/schedule.post.ts` - Emits billing usage events for scheduled control intents.

### Files Removed

- None.

### Dependencies & Infrastructure

- **New Dependencies**: None.
- **Updated Dependencies**: None.
- **Infrastructure Changes**: Added tenant-scoped billing event ledger under `dashboard/data/tenants/<tenantId>/billing/usage-events.jsonl`.
- **Configuration Updates**: Added static tenant-plan defaults and optional environment override via `TENANT_BILLING_PLAN_MAP`.

### Deployment Notes

No migration is required. The billing draft endpoint is available at `/api/billing/draft`; usage events are captured automatically by control execute/schedule APIs.
