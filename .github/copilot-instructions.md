<!-- desloppify-begin -->
<!-- desloppify-skill-version: 3 -->
---
name: desloppify
description: >
  Codebase health scanner and technical debt tracker. Use when the user asks
  about code quality, technical debt, dead code, large files, god classes,
  duplicate functions, code smells, naming issues, import cycles, or coupling
  problems. Also use when asked for a health score, what to fix next, or to
  create a cleanup plan. Supports 28 languages.
allowed-tools: Bash(desloppify *)
---

# Desloppify Copilot Overlay

This file is a narrow Copilot overlay for desloppify and code-health work.
Repo-wide workflow remains in `AGENTS.md` and stays authoritative for runtime
truth, Beads workflow, validation, landing, and branch lifecycle rules. If this
file and `AGENTS.md` overlap, follow `AGENTS.md` and keep this file limited to
desloppify-specific execution.

## Core Rules

- Follow `desloppify next` and the scan output instead of inventing a separate prioritization scheme.
- Apply the repo execution style from `AGENTS.md`: explicit assumptions, simplest viable fix, surgical edits, and immediate behavior-scoped validation.
- Keep cleanup work narrow. If a finding turns into broader architecture work, stop treating it as a queue-clearing slice.

## Minimal Workflow

### 1. Scan and Review

```bash
desloppify scan --path .
desloppify status
desloppify review --prepare
```

Run review only when the scan asks for it or when a stale subjective dimension
needs to be refreshed.

### 2. Plan the Queue

```bash
desloppify next
desloppify plan
desloppify plan triage --stage observe --report "themes and root causes..."
desloppify plan triage --stage reflect --report "comparison against completed work..."
desloppify plan triage --stage organize --report "summary of priorities..."
desloppify plan triage --complete --strategy "execution plan..."
```

Use plan shaping commands only when they clarify execution order:

```bash
desloppify plan cluster create <name>
desloppify plan focus <cluster>
desloppify plan resolve <pat>
```

### 3. Execute and Land

- Use the Beads, validation, and landing flow from `AGENTS.md`.
- Do not commit health work directly to `main`.
- Prefer small, related batches instead of unnecessary branch churn.
- Close or prune stale cleanup branches once the landing flow is complete.

```bash
desloppify config set commit_pr 42
```

```bash
desloppify plan commit-log record
```

After recording the cleanup batch, run the landing flow from `AGENTS.md` so
Beads status, branch history, and the PR all describe the same state.

## Useful Commands

```bash
desloppify next --count 5
desloppify next --cluster <name>
desloppify show <pattern>
desloppify show --status open
desloppify autofix <fixer> --dry-run
desloppify config show
desloppify plan commit-log
desloppify plan commit-log history
desloppify plan commit-log pr
```

## Review and Scoring Notes

- Prefer objective queue work first: orphaned code, dead writes, duplication, and narrow structural fixes.
- For subjective review prompts, keep findings evidence-based and avoid turning cleanup work into a broad rewrite.
- If a finding is valid but not worth the disruption, document the reason instead of forcing a cosmetic refactor.


## Copilot Review Agents

If you need context-isolated subjective reviews, define lightweight reviewer and
orchestrator agents in `.github/agents/` and split dimensions across reviewer
calls before importing the merged result.

## Escalation

If desloppify itself appears wrong or inconsistent:

1. Capture a minimal repro with command, path, expected, and actual behavior.
2. Open an issue in `peteromallet/desloppify`.
3. If the fix is safe and clear, open a linked PR.

## Prerequisite

`command -v desloppify >/dev/null 2>&1 && echo "desloppify: installed" || echo "NOT INSTALLED — run: pip install --upgrade git+https://github.com/peteromallet/desloppify.git"`


## .copilot-tracking Workflow

- Treat `.copilot-tracking/` as an authoritative working area when the user or a prompt explicitly references files there, even though the directory may be git-ignored.
- If a task starts from `.copilot-tracking/prompts/*.prompt.md`, read the referenced plan, details, and research files before implementation instead of treating the prompt as self-contained.
- When a `.copilot-tracking/changes/*.md` file is part of the task contract, create the parent `changes/` directory if needed and keep the change log updated as implementation progresses.
- Prefer `read_file`, `list_dir`, or searches that include ignored files when locating `.copilot-tracking` artifacts; do not assume normal file search will surface them.
- Do not promote `.copilot-tracking` artifacts into tracked docs by default. Only move or publish content from `.copilot-tracking/` into the main repository surface when the user explicitly asks for that promotion.
<!-- desloppify-overlay: copilot -->
<!-- desloppify-end -->

