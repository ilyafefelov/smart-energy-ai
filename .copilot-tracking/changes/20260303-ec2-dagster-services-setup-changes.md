<!-- markdownlint-disable-file -->
# Release Changes: EC2 Dagster Services Setup

**Related Plan**: 20260303-ec2-dagster-services-setup-plan.instructions.md
**Implementation Date**: 2026-03-03

## Summary

Tracking implementation for issue `smart-energy-ai-c9i` to make Dagster webserver/daemon setup repeatable and reboot-safe on EC2 `t3.micro`.

## Changes

### Added

- `deploy/systemd/dagster-webserver.service` - Systemd template for Dagster webserver with restart policy and environment-file configuration.
- `deploy/systemd/dagster-daemon.service` - Systemd template for Dagster daemon with restart policy and environment-file configuration.
- `deploy/systemd/dagster.env.example` - Sample environment file defining Dagster module, commands, and runtime paths.
- `scripts/ec2/setup-dagster-services.sh` - Idempotent EC2 bootstrap script to install dependencies, create venv, render units, enable services, and validate health.
- `scripts/ec2/check-dagster-services.sh` - Health-check script validating systemd service activity and Dagster HTTP endpoint reachability.
- `docs/deployment/EC2_DAGSTER_T3_MICRO_RUNBOOK.md` - Fresh-instance deployment runbook with reboot verification, lifecycle commands, and troubleshooting.
- `.copilot-tracking/plans/20260303-ec2-dagster-services-setup-plan.instructions.md` - Task checklist for EC2 Dagster service setup.
- `.copilot-tracking/changes/20260303-ec2-dagster-services-setup-changes.md` - Change log for this implementation track.

### Modified

- `README.md` - Added explicit reference to the EC2 Dagster service runbook under the deployment architecture section.

### Removed

## Release Summary

**Total Files Affected**: 9

### Files Created (8)

- `deploy/systemd/dagster-webserver.service` - Systemd unit template for Dagster webserver.
- `deploy/systemd/dagster-daemon.service` - Systemd unit template for Dagster daemon.
- `deploy/systemd/dagster.env.example` - Environment variable template for Dagster services.
- `scripts/ec2/setup-dagster-services.sh` - Bootstrap script for EC2 dependency install, Python env setup, service installation, and health validation.
- `scripts/ec2/check-dagster-services.sh` - Runtime health-check script for service/process/endpoint validation.
- `docs/deployment/EC2_DAGSTER_T3_MICRO_RUNBOOK.md` - Fresh-instance operations runbook including reboot verification.
- `.copilot-tracking/plans/20260303-ec2-dagster-services-setup-plan.instructions.md` - Task checklist for issue implementation.
- `.copilot-tracking/details/20260303-ec2-dagster-services-setup-details.md` - Detailed implementation requirements by phase/task.

### Files Modified (1)

- `README.md` - Added runbook reference for EC2 Dagster service setup workflow.

### Files Removed (0)

- None.

### Dependencies & Infrastructure

- **New Dependencies**: None.
- **Updated Dependencies**: None.
- **Infrastructure Changes**: Added systemd-based Dagster service lifecycle templates for Linux EC2 hosts.
- **Configuration Updates**: Added environment-file contract for Dagster service runtime (`/etc/smart-energy-ai/dagster.env`).

### Deployment Notes

- Shell syntax validation passed for both EC2 scripts via `bash -n`.
- Service runtime behavior requires execution on Ubuntu EC2 host with `systemd` and `apt` available.
