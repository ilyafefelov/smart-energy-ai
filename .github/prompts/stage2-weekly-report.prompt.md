---
description: "Use when creating, refreshing, or extending a Stage 2 weekly report for diploma progress. Helps scaffold the weekly report, collect evidence sources, and keep report artifacts aligned with the repo workflow."
name: "Stage 2 Weekly Report"
argument-hint: "Week number, date range, focus, and whether to create or update"
agent: "agent"
model: "GPT-5 (copilot)"
---
Prepare a Stage 2 weekly report using the repo's existing workflow.

Inputs from the user should include as many of these as available:

- week number
- start date and end date
- weekly focus
- whether this is a new report or an update to an existing one
- any specific commits, tests, docs, screenshots, or literature sources to include

Follow these repo rules and sources:

- Weekly reports live in [docs/Stage 2/weekly_reports/README.md](../../docs/Stage%202/weekly_reports/README.md).
- Use the template in [docs/Stage 2/weekly_reports/weekly_progress_report_template.md](../../docs/Stage%202/weekly_reports/weekly_progress_report_template.md).
- If the target week is not explicit, ask which week should be updated before editing weekly reports.
- Keep one report per calendar week and update the active week in place unless the user explicitly asked to start a new week.
- Use [docs/Stage 2/diploma_literature_tracker.md](../../docs/Stage%202/diploma_literature_tracker.md) for literature links and theory mapping.
- Keep evidence artifacts in the matching `week-XX-artifacts/` folder.

Expected workflow:

1. Determine whether the task is to create a new weekly report or update an existing one.
2. If creating a new week, prefer the existing script `scripts/local/new-stage2-weekly-report.ps1` or follow its output structure.
3. Fill the report from real repo evidence: recent commits, touched files, tests, Dagster materializations, smoke checks, and generated artifacts.
4. Keep risks, blockers, and next steps concrete.
5. Tie the weekly slice to relevant literature sources when the report format requires it.
6. In the final response, list the report file and any artifact-folder files that were created or updated.

If the user only gives a partial request, ask only for the missing details that block choosing the correct week or creating the report file.