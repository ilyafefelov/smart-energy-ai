---
applyTo: '.copilot-tracking/changes/20260303-ec2-dagster-services-setup-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: EC2 Dagster Services Setup

## Overview

Configure a fresh EC2 `t3.micro` instance to run Dagster webserver and daemon as resilient systemd services with documented boot, logging, and health-check lifecycle.

## Objectives

- Provide an idempotent setup path for Ubuntu-based EC2 hosts.
- Ensure Dagster services are enabled at boot and recover automatically.
- Document lifecycle and verification commands for operations handoff.

## Implementation Checklist

### [x] Phase 1: Service Templates and Setup Scripts

- [x] Task 1.1: Add systemd unit templates and env template
- [x] Task 1.2: Add EC2 bootstrap script for dependency install, venv setup, and unit installation
- [x] Task 1.3: Add health-check script for service and endpoint validation

### [x] Phase 2: Documentation and Validation

- [x] Task 2.1: Add EC2 runbook with fresh-instance setup and reboot validation steps
- [x] Task 2.2: Validate script syntax and update references in top-level docs

## Dependencies

- Beads issue: `smart-energy-ai-c9i`
- Ubuntu package manager availability (`apt-get`)
- Repo checkout on instance host path (default `/opt/smart-energy-ai`)

## Success Criteria

- A fresh EC2 instance can be configured by following the runbook.
- Both Dagster services are managed by systemd and auto-start on reboot.
- Health checks and log commands are explicit and operational.
