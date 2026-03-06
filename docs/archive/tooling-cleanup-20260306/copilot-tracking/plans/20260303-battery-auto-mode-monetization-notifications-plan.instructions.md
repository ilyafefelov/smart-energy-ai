---
applyTo: ".copilot-tracking/changes/20260303-battery-auto-mode-monetization-notifications-changes.md"
---

<!-- markdownlint-disable-file -->

# Task Checklist: Battery Auto Mode Monetization and Notifications

## Overview

Harden battery auto mode so it follows smart recommendations, persists realized earnings historically, and notifies users on key control-state transitions.

## Objectives

- Ensure auto mode executes recommendation-backed charge/discharge/hold actions with one authoritative state machine across control surfaces.
- Establish realized earnings as canonical historical truth and wire corner transition notifications plus reactive charts to that source.

## Research Summary

### Project Files

- `dashboard/server/api/battery/simulate.ts` - Current auto mode uses local heuristic and module-global state.
- `dashboard/server/api/control/execute.post.ts` - Execution persistence path for control economics and actions.
- `dashboard/server/utils/optimization-history.ts` - Canonical optimization history schema/upsert implementation.
- `dashboard/server/api/history.ts` - Historical aggregation route used by dashboard metrics.
- `dashboard/server/api/metrics.ts` - Savings KPI aggregation with fallback behavior.
- `dashboard/app/pages/control.vue` - Main control UI and current toast emission path.
- `dashboard/app/pages/index.vue` - Dashboard trend cards/charts with synthetic fallback logic.

### External References

- #file:../research/20260303-battery-auto-mode-monetization-notifications-research.md - Verified gap analysis and recommended architecture.
- #githubRepo:"nuxt/ui useToast deduplicated toasts id" - Toast dedupe pattern with stable IDs.
- #githubRepo:"vueuse/vueuse watchDebounced debounceFilter watchWithFilter" - Debounced watcher pattern for transition notification suppression.
- #fetch:https://ui.nuxt.com/components/toast - Nuxt UI toast behavior and requirements.
- #fetch:https://vueuse.org/shared/watchDebounced/ - Debounce watcher usage and options.
- #fetch:https://www.postgresql.org/docs/current/sql-insert.html - Upsert semantics for realized earnings writes.

### Standards References

- #file:../../AGENTS.md - Beads workflow, task tracking, and completion protocol.
- #file:../../dashboard/nuxt.config.ts - Active Nuxt app runtime layout.
- #file:../../dashboard/CODEX_MCP_GUIDE.md - Dashboard testing/runtime validation guidance.

## Implementation Checklist

### [x] Phase 1: Auto Mode Correctness and Control Reliability

- [x] Task 1.1: Unify auto mode state machine and recommendation-driven execution
  - Details: .copilot-tracking/details/20260303-battery-auto-mode-monetization-notifications-details.md (Lines 11-31)

- [x] Task 1.2: Fix python runner contract and remove dead execution dependencies
  - Details: .copilot-tracking/details/20260303-battery-auto-mode-monetization-notifications-details.md (Lines 33-54)

### [x] Phase 2: Realized Earnings as Historical Source of Truth

- [x] Task 2.1: Extend optimization history with realized earnings and transition metadata
  - Details: .copilot-tracking/details/20260303-battery-auto-mode-monetization-notifications-details.md (Lines 58-77)

- [x] Task 2.2: Align history and metrics APIs to realized ledger precedence
  - Details: .copilot-tracking/details/20260303-battery-auto-mode-monetization-notifications-details.md (Lines 79-97)

### [x] Phase 3: Corner Notifications and Reactive Dashboard Graphs

- [x] Task 3.1: Add deduped/debounced corner notifications for mode/action transitions
  - Details: .copilot-tracking/details/20260303-battery-auto-mode-monetization-notifications-details.md (Lines 101-120)

- [x] Task 3.2: Rewire dashboard charts to canonical transition/history data
  - Details: .copilot-tracking/details/20260303-battery-auto-mode-monetization-notifications-details.md (Lines 122-141)

## Dependencies

- Claimed Beads issue: `smart-energy-ai-e9x`.
- PostgreSQL migration/update access for `optimization_history` enhancements.
- Stable tenant context resolution and recommendation endpoints.
- Nuxt UI toast stack and polling loop behavior in control/dashboard views.

## Success Criteria

- Auto mode uses recommendation-backed execution policy (with explicit fallback source) and is consistent across widget + control page.
- Realized earnings are persisted per transition and surfaced as canonical values in history/metrics/dashboard cards.
- Corner notifications fire once per meaningful transition and honor user preference settings.
- Dashboard graphs react to canonical realized series instead of synthetic-only trend factors.
