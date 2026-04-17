# Weekly Capstone Reports

Active workspace for recurring diploma weekly progress reports.

Use this folder when you need to prepare the text report, attach screenshots, or collect a video link for submission to the supervisor.

## Files In This Folder

- `weekly_progress_report_template.md` — reusable markdown template for each reporting week.
- `week-01-progress-report.md` — current Week 1 draft based on the active Stage 2 forecast and optimization work.
- `week-02-progress-report.md` — generated stub for the next reporting week.
- `week-02-artifacts/README.md` — placeholder folder for screenshots and optional video links for Week 2.

## Recommended Weekly Workflow

1. Generate the new report from the template with `pwsh .\scripts\local\new-stage2-weekly-report.ps1 -WeekNumber <N> -StartDate <YYYY-MM-DD> -EndDate <YYYY-MM-DD> -Focus "<weekly focus>"`.
2. Fill the completed work section from recent commits, closed Beads tasks, and touched repo artifacts.
3. Fill the risk section with concrete blockers, why they matter, and the exact mitigation plan.
4. Add the plan for the next week as a short implementation checklist.
5. Add links to code, docs, tests, screenshots, and an optional video.
6. Include at least 5 theory sources from `../diploma_literature_tracker.md` and explain how they relate to the current slice of work.

## Bootstrap Example

```powershell
pwsh .\scripts\local\new-stage2-weekly-report.ps1 `
	-WeekNumber 2 `
	-StartDate 2026-04-20 `
	-EndDate 2026-04-26 `
	-Focus "Відновити dashboard validation surface та вивести Dagster provenance у UI"
```

This creates:

- `week-02-progress-report.md`
- `week-02-artifacts/README.md`

## Submission Checklist

- Text report link or attached text document is ready.
- Optional screencast link is added if you record a video.
- Code links point to the exact files or commits discussed.
- Risks and next steps are specific, not generic.
- At least 5 literature sources are tied to the implemented or analyzed slice.
- The report is ready before Sunday 23:59.

## Good Evidence Sources In This Repo

- `git log --oneline --decorate -N` for recent completed slices.
- `.beads/issues.jsonl` for claimed and closed weekly work.
- `../codebase_implementation_roadmap.md` for Phase and next-step alignment.
- `../diploma_literature_tracker.md` and `../diploma_bibliography.bib` for theory references.
- Focused validation results from `pytest`, Dagster materializations, and API smoke checks.

## Notes

- The cybersecurity subsection in the template is conditional; keep it only when it is relevant to the current weekly work.
- If you use screenshots, keep them next to the report or link to the artifact location explicitly in the report.