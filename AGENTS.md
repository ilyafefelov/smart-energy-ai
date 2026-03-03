# Smart Energy AI - Agent Instructions

This project uses **bd** (beads) for issue tracking. Run `bd onboard` to get started.

## Mandatory Beads-First Protocol (All Agents)

Before writing code, editing docs, or running cleanup actions, agents MUST:

1. Run `bd ready --json` and select an unblocked issue.
2. If no issue exists for the requested work, create one with `bd create ... --json`.
3. Claim work with `bd update <id> --claim --json` (or set `--status in_progress`).
4. Record discovered follow-up work using linked issues (`--deps discovered-from:<id>`).
5. Only close work with `bd close <id> --reason "..." --json` after validation.

Non-compliant behavior:
- Starting implementation without a Beads issue
- Tracking work in markdown TODO lists instead of Beads
- Ending a session with completed work but open/untouched Beads status

## Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --status in_progress  # Claim work
bd close <id>         # Complete work
bd dolt remote list   # Check Dolt remotes
bd dolt pull          # Pull Beads data when remote is configured
bd dolt push          # Push Beads data when remote is configured
```

## Project Overview

The Smart Energy AI system is a comprehensive platform designed to optimize energy storage and consumption for commercial and industrial clients using reinforcement learning (RL) and machine learning (ML) techniques. The system integrates real-time data from electricity markets, weather APIs, and client-specific configurations to provide intelligent energy management solutions.

## Project Structure

```
smart-energy-ai/
├── src/                          # Main source code
│   ├── rl_environment.py        # RL environment with battery physics
│   ├── rl_training.py           # PPO algorithm implementation
│   ├── weather_fetcher.py       # Weather data from Open-Meteo
│   ├── real_price_data.py       # Real price data from European sources
│   ├── oree_*.py                # OREE price scrapers (Playwright, Selenium)
│   ├── data_pipeline/           # Data ingestion and validation
│   │   ├── ingest_weather.py
│   │   ├── ingest_prices.py
│   │   └── validate.py
│   └── assets/core/             # Dagster assets (data definitions)
│       ├── market.py
│       ├── weather.py
│       └── client_state.py
├── dashboard/                    # Streamlit web interface
├── config/                       # Configuration files
├── data/                        # Data storage
│   ├── raw/
│   └── processed/
├── docker/                      # Docker configuration
├── checkpoints/                 # Model checkpoints
├── docs/                        # Documentation
└── tests/                       # Test suite
```

## Key Technologies

- **Programming Languages**: Python, JavaScript
- **Frameworks**: PyTorch, Scikit-learn, Streamlit, Dagster
- **Data Storage**: PostgreSQL
- **Orchestration**: Docker, Kubernetes, AWS ECS
- **APIs**: Open-Meteo, OREE (Ukraine)
- **Tools**: MLflow, Playwright, Selenium

## Development Guidelines

### Getting Started

1. **Set up environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   .\venv\Scripts\Activate.ps1  # Windows
   pip install -r requirements.txt
   pip install -r requirements-test.txt
   ```

2. **Run tests**:
   ```bash
   pytest tests/ -v
   ```

3. **Run the dashboard**:
   ```bash
   streamlit run app.py
   ```

4. **Run data pipeline**:
   ```bash
   python -m src.data_pipeline.ingest_weather
   python -m src.data_pipeline.ingest_prices
   ```

### Working with Docker

1. **Build image**:
   ```bash
   docker build -t smart-energy-ai .
   ```

2. **Run container**:
   ```bash
   docker run -p 8501:8501 --env-file .env smart-energy-ai
   ```

3. **Local development with Docker Compose**:
   ```bash
   cd docker
   docker-compose up -d
   ```

### Data Pipeline

1. **Weather Data**: Fetches data from Open-Meteo API for solar irradiance and temperature forecasts
2. **Price Data**: Scrapes OREE Ukrainian electricity prices using Playwright or Selenium
3. **Data Validation**: Uses Pydantic models to ensure data quality and consistency

### RL Training

1. **Training**: Run `rl_training.py` to train the PPO algorithm
2. **Checkpoints**: Trained models are saved in `checkpoints/` directory
3. **Inference**: Use trained models for real-time decision-making

### Dashboard

- **Streamlit Dashboard**: Real-time monitoring of energy usage, savings, and system performance
- **Visualizations**: Cost reduction calculations, battery health monitoring, and optimization results

## Issue Tracking

The project uses **bd** (beads) for issue tracking. All issues are stored in `.beads/issues.jsonl`.

### Common Tasks

1. **View all open issues**:
   ```bash
   bd ready
   ```

2. **View issue details**:
   ```bash
   bd show <issue-id>
   ```

3. **Claim an issue**:
   ```bash
   bd update <issue-id> --status in_progress
   ```

4. **Complete an issue**:
   ```bash
   bd close <issue-id>
   ```

## Resources

- **Project Schematic**: `PROJECT_SCHEMATIC.md` - Comprehensive architecture overview
- **API Documentation**: `docs/API_DOCUMENTATION_IMPORT_EXPORT.md`
- **ML Pipeline**: `ML_PIPELINE_PLAN.md`
- **Testing Guide**: `TEST_PIPELINE_GUIDE.md`
- **Nuxt MCP Guide**: `https://nuxt.com/docs/4.x/guide/ai/mcp`
- **Archived Legacy Reports**: `docs/archive/root-cleanup-20260302/`

<!-- BEGIN BEADS INTEGRATION -->
## Issue Tracking with bd (beads)

**IMPORTANT**: This project uses **bd (beads)** for ALL issue tracking. Do NOT use markdown TODOs, task lists, or other tracking methods.

### Why bd?

- Dependency-aware: Track blockers and relationships between issues
- Git-friendly: Dolt-powered version control with native sync
- Agent-optimized: JSON output, ready work detection, discovered-from links
- Prevents duplicate tracking systems and confusion

### Quick Start

**Check for ready work:**

```bash
bd ready --json
```

**Create new issues:**

```bash
bd create "Issue title" --description="Detailed context" -t bug|feature|task -p 0-4 --json
bd create "Issue title" --description="What this issue is about" -p 1 --deps discovered-from:bd-123 --json
```

**Claim and update:**

```bash
bd update <id> --claim --json
bd update bd-42 --priority 1 --json
```

**Complete work:**

```bash
bd close bd-42 --reason "Completed" --json
```

### Issue Types

- `bug` - Something broken
- `feature` - New functionality
- `task` - Work item (tests, docs, refactoring)
- `epic` - Large feature with subtasks
- `chore` - Maintenance (dependencies, tooling)

### Priorities

- `0` - Critical (security, data loss, broken builds)
- `1` - High (major features, important bugs)
- `2` - Medium (default, nice-to-have)
- `3` - Low (polish, optimization)
- `4` - Backlog (future ideas)

### Workflow for AI Agents

1. **Check ready work**: `bd ready` shows unblocked issues
2. **Claim your task atomically**: `bd update <id> --claim`
3. **Work on it**: Implement, test, document
4. **Discover new work?** Create linked issue:
   - `bd create "Found bug" --description="Details about what was found" -p 1 --deps discovered-from:<parent-id>`
5. **Complete**: `bd close <id> --reason "Done"`

### Auto-Sync

bd automatically syncs via Dolt:

- Each write auto-commits to Dolt history
- Use `bd dolt push`/`bd dolt pull` for remote sync when a Dolt remote is configured
- If no Dolt remote is configured, use `pwsh ./scripts/local/bd-dolt-sync-safe.ps1` to safely skip remote sync without failing landing checks
- No manual export/import needed!

### Important Rules

- ✅ Use bd for ALL task tracking
- ✅ Always use `--json` flag for programmatic use
- ✅ Link discovered work with `discovered-from` dependencies
- ✅ Check `bd ready` before asking "what should I work on?"
- ❌ Do NOT create markdown TODO lists
- ❌ Do NOT use external issue trackers
- ❌ Do NOT duplicate tracking systems

For more details, see README.md and docs/QUICKSTART.md.

<!-- END BEADS INTEGRATION -->

## Landing the Plane (Session Completion)

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   pwsh ./scripts/local/bd-dolt-sync-safe.ps1
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds
