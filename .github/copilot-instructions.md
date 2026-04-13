# Copilot Instructions

This file is a narrow overlay for Copilot-specific behavior in this repository.
`AGENTS.md` remains the source of truth for runtime guidance, Beads workflow,
validation, landing, and execution style.

## Core Rules

- Default to normal repo work first: implementation, debugging, tests, and runtime validation should follow `AGENTS.md` without any special code-health workflow.
- Use `desloppify` only when the task is explicitly about code health, technical debt, dead code, large files, duplication, coupling, or cleanup planning.
- When a task is not explicitly code-health work, do not let `desloppify` drive prioritization or scope.

## Desloppify Tasks

When the task is explicitly code-health work:

- Follow `desloppify next` and the scan output instead of inventing a separate prioritization scheme.
- Apply the repo execution style from `AGENTS.md`: explicit assumptions, simplest viable fix, surgical edits, and immediate behavior-scoped validation.
- Keep cleanup work narrow. If a finding turns into broader architecture work, stop treating it as a queue-clearing slice.

Useful commands:

```bash
desloppify scan --path .
desloppify status
desloppify next
desloppify review --prepare
desloppify plan
desloppify plan cluster create <name>
desloppify plan focus <cluster>
desloppify plan resolve <pat>
desloppify config set commit_pr 42
desloppify plan commit-log record
```

## Review and Scoring Notes

- Prefer objective queue work first: orphaned code, dead writes, duplication, and narrow structural fixes.
- For subjective review prompts, keep findings evidence-based and avoid turning cleanup work into a broad rewrite.
- If a finding is valid but not worth the disruption, document the reason instead of forcing a cosmetic refactor.


## .copilot-tracking Workflow

- Treat `.copilot-tracking/` as an authoritative working area when the user or a prompt explicitly references files there, even though the directory may be git-ignored.
- If a task starts from `.copilot-tracking/prompts/*.prompt.md`, read the referenced plan, details, and research files before implementation instead of treating the prompt as self-contained.
- When a `.copilot-tracking/changes/*.md` file is part of the task contract, create the parent `changes/` directory if needed and keep the change log updated as implementation progresses.
- Prefer `read_file`, `list_dir`, or searches that include ignored files when locating `.copilot-tracking` artifacts; do not assume normal file search will surface them.
- Do not promote `.copilot-tracking` artifacts into tracked docs by default. Only move or publish content from `.copilot-tracking/` into the main repository surface when the user explicitly asks for that promotion.

