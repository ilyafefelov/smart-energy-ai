---
description: "Use when drafting or refreshing a Stage 2 weekly report from recent commits, touched files, validation results, and linked literature sources. Helps build the report from concrete repo evidence instead of a blank template."
name: "Stage 2 Weekly Report From Commits"
argument-hint: "Week number or target report, commit window, focus, and whether to create or update"
agent: "agent"
model: "GPT-5 (copilot)"
---
Draft or refresh a Stage 2 weekly report starting from recent repository evidence.

Inputs from the user should include as many of these as available:

- week number or exact target report file
- commit window, date range, or branch slice to summarize
- weekly focus
- whether to create a new report or update an existing one
- any tests, docs, screenshots, or literature sources that must be included

Follow these repo rules and sources:

- Weekly reports live in [docs/Stage 2/weekly_reports/README.md](../../docs/Stage%202/weekly_reports/README.md).
- Use the template in [docs/Stage 2/weekly_reports/weekly_progress_report_template.md](../../docs/Stage%202/weekly_reports/weekly_progress_report_template.md).
- If the target week is not explicit, ask which week should be updated before editing weekly reports.
- Keep one report per calendar week and update the active week in place unless the user explicitly asked to start a new week.
- Use [docs/Stage 2/diploma_literature_tracker.md](../../docs/Stage%202/diploma_literature_tracker.md) and [docs/Stage 2/diploma_bibliography.bib](../../docs/Stage%202/diploma_bibliography.bib) for theory links when the report format requires them.
- Keep evidence artifacts in the matching `week-XX-artifacts/` folder.

Primary evidence sources to gather from the repo:

- recent commits from `git log --oneline --decorate -N` or a narrower date or branch window
- touched code and doc paths from the commits being summarized
- focused validation results such as `pytest`, Dagster materializations, API smokes, or Stage 2 evidence smokes
- related Stage 2 planning docs such as [docs/Stage 2/codebase_implementation_roadmap.md](../../docs/Stage%202/codebase_implementation_roadmap.md)
- Beads tasks when available; if Beads is unavailable locally, note the blocker and continue from git history and repo artifacts

Expected workflow:

1. Determine the target week or report file.
2. Determine the commit window to summarize. If missing, ask only for the minimum detail needed to avoid summarizing the wrong slice.
3. Gather recent commits, touched files, validation evidence, and linked docs that support the weekly slice.
4. Translate that evidence into the repo's weekly report structure: completed work, risks, next steps, artifacts, and literature linkage.
5. Keep the summary specific to what actually landed in the repo; do not invent tests, metrics, or literature usage that is not evidenced.
6. In the final response, list the report file and any artifact-folder files that were created or updated.

If the user wants a new weekly report generated from scratch, prefer the existing script `scripts/local/new-stage2-weekly-report.ps1` or follow its output structure before filling the content from commit history.