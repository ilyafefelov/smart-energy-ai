# Cline ↔ Beads Sync Guide

## Overview

This project uses **Beads (`bd`)** as the source of truth for task tracking, but you can also use Cline's Kanban board with automatic sync.

## Setup

### 1. Create Sync Script
The sync script is already created at:
```
scripts/local/cline-beads-sync.ps1
```

### 2. Create Cline Rules
The workflow is documented in:
```
.clinerules
```

## Usage

### Quick Start

```powershell
# 1. See what tasks are available
.\scripts\local\cline-beads-sync.ps1 -Action Status

# 2. Export Beads tasks for Cline
.\scripts\local\cline-beads-sync.ps1 -Action Export

# 3. Claim a task in Beads
.\scripts\local\cline-beads-sync.ps1 -Action Claim -TaskId "smart-energy-ai-XXXX"

# 4. Do your work...

# 5. Close the task when done
.\scripts\local\cline-beads-sync.ps1 -Action Close -TaskId "smart-energy-ai-XXXX" -Reason "Completed"
```

### Available Commands

| Command | Description |
|---------|-------------|
| `-Action Export` | Export Beads tasks to `.cline/beads-tasks.json` |
| `-Action Import` | Import new Cline tasks to Beads |
| `-Action Status` | Show sync status between Cline and Beads |
| `-Action Create -Title "..." -Description "..."` | Create a new Beads task |
| `-Action Claim -TaskId "..."` | Claim a task in Beads |
| `-Action Close -TaskId "..." -Reason "..."` | Close a task in Beads |

## Sync Files

- `.cline/beads-tasks.json` - Exported Beads tasks (read by Cline)
- `.cline/cline-tasks.json` - Cline tasks with Beads ID references

## Key Principles

1. **Beads is the source of truth** - Always sync back to Beads after completing work
2. **One task per coherent cluster** - Don't create tasks for tiny changes
3. **Validate before closing** - Run tests before marking complete
4. **Keep git clean** - Use `bd-dolt-sync-safe.ps1` before pushing

## Example Workflow

1. **Check available tasks:**
   ```powershell
   .\scripts\local\cline-beads-sync.ps1 -Action Status
   ```

2. **Export tasks for Cline:**
   ```powershell
   .\scripts\local\cline-beads-sync.ps1 -Action Export
   ```

3. **Claim a task:**
   ```powershell
   .\scripts\local\cline-beads-sync.ps1 -Action Claim -TaskId "smart-energy-ai-3lcq"
   ```

4. **After completing work:**
   ```powershell
   .\scripts\local\cline-beads-sync.ps1 -Action Close -TaskId "smart-energy-ai-3lcq" -Reason "Refactored backend entrypoints"
   pytest tests/ -v
   pwsh ./scripts/local/bd-dolt-sync-safe.ps1
   git push
   ```

## Current Tasks

The sync script shows 4 open tasks in Beads:
- `[E005] Backend Modular Monolith Refactor` (priority 1)
- `Type tenant request store fetches` (priority 2)
- `[P3][T017] Implement AWS Lambda workers with 15-min partitioning` (priority 2)
- `[E004] AWS Free Tier Deployment` (priority 2)

## Troubleshooting

**If Beads is not available:**
- The script will fall back to scoped changes with validation
- Do not invent an alternate tracker

**If sync fails:**
- Check that `bd` is installed and working
- Verify you're in the project root
- Check file permissions on `.cline/` directory