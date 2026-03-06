# Plan: SaaS Billing Integration Framework

**Issue**: `smart-energy-ai-8yj`
**Date**: 2026-03-03

## Objective

Design and implement a tenant-scoped SaaS billing scaffold that captures usage events, applies entitlement-aware pricing hooks via a provider abstraction, and exposes draft invoice computation for multiple tenants.

## Phase 1: Billing Domain Scaffold [x]

- [x] Add billing event model and tenant-scoped event persistence utility.
- [x] Add provider abstraction for invoice generation with a default local rate-card implementation.
- [x] Add plan/entitlement model and rate hooks for billable features.

## Phase 2: Runtime Integration Hooks [x]

- [x] Record billing usage events in control command execution flow.
- [x] Record billing usage events in control scheduling flow.
- [x] Ensure billing hooks are non-blocking and cannot fail control APIs.

## Phase 3: API Surface and Validation [x]

- [x] Add billing draft API endpoint with tenant resolution and period filtering.
- [x] Add integration test coverage for multi-tenant draft billing behavior.
- [x] Validate lint/build for modified TypeScript and test files.

## Completion Notes

All three phases were implemented and validated in this session. Billing remains intentionally provider-agnostic with a local default provider and can be extended with external billing vendors without changing API contracts.
