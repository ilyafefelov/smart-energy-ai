<!-- markdownlint-disable-file -->

# Task Details: EC2 Dagster Services Setup

## Phase 1: Service Templates and Setup Scripts

### Task 1.1: Add systemd unit templates and env template

- Files:
  - `deploy/systemd/dagster-webserver.service`
  - `deploy/systemd/dagster-daemon.service`
  - `deploy/systemd/dagster.env.example`
- Success:
  - Unit templates define restart semantics and environment-file based configuration.
  - Placeholders can be rendered to concrete values by setup script.

### Task 1.2: Add EC2 bootstrap script

- Files:
  - `scripts/ec2/setup-dagster-services.sh`
- Success:
  - Script installs dependencies, creates venv, installs Python packages, renders units, enables/restarts services, and verifies health.
  - Script can be re-run safely on the same host.

### Task 1.3: Add health-check script

- Files:
  - `scripts/ec2/check-dagster-services.sh`
- Success:
  - Script returns non-zero when either service is inactive or HTTP health endpoint fails.

## Phase 2: Documentation and Validation

### Task 2.1: Add EC2 runbook

- Files:
  - `docs/deployment/EC2_DAGSTER_T3_MICRO_RUNBOOK.md`
- Success:
  - Includes fresh-instance setup, lifecycle commands, logs, and reboot validation.

### Task 2.2: Validate scripts and add references

- Files:
  - `README.md`
- Success:
  - README references runbook path.
  - Shell scripts pass `bash -n` syntax checks.
