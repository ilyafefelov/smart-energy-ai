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
Repo-wide workflow remains in `AGENTS.md` and stays authoritative for Beads,
validation, landing, branch lifecycle, and local runtime guidance. If this file
and `AGENTS.md` overlap, follow `AGENTS.md` for repository workflow and use
this file only for desloppify-specific execution.

## Core Rules

- Maximise the strict score honestly.
- Follow `desloppify scan`, `desloppify next`, and review instructions instead
  of inventing a separate prioritization scheme when the tool already provides
  one.
- Prefer bounded batches that can be validated and landed cleanly.
- Do not rescan mid-queue unless blocked or the current queue is exhausted.

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
desloppify plan reorder <pat> top
desloppify plan cluster create <name>
desloppify plan focus <cluster>
desloppify plan resolve <pat>
```

### 3. Execute and Land

- Before starting a bounded cleanup task, create or claim a Beads task exactly
  as required by `AGENTS.md`.
- Use a dedicated `desloppify/<description>` branch for multi-commit health
  passes. Do not commit health work directly to `main`.
- If you are already on an active cleanup branch, continue there instead of
  creating unnecessary branch churn.
- Once a cleanup branch is merged or superseded, delete or prune it instead of
  leaving stale health branches behind.
- If a PR exists, link it:

```bash
desloppify config set commit_pr 42
```

- After each logical cleanup commit, record it:

```bash
desloppify plan commit-log record
```

- Keep Beads, git commits, and PR state synchronized. Before push or PR updates,
  run the landing flow from `AGENTS.md` so Beads status, branch history, and the
  PR all describe the same state.

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

- Overall score is `40%` mechanical and `60%` subjective.
- Strict score is the operating target; wontfix items still count against it.
- Review from evidence only. Do not anchor to prior scores or target thresholds.
- Import first, then fix, so review state and tracked findings stay correlated.

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

<!-- desloppify-overlay: copilot -->
<!-- desloppify-end -->

