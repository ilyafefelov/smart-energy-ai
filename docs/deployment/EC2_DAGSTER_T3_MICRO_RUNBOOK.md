# EC2 t3.micro Dagster Service Runbook

This runbook configures Dagster webserver and daemon as systemd services on a fresh Ubuntu EC2 `t3.micro` instance.

## Scope

- Host: EC2 `t3.micro` (Ubuntu 22.04 LTS recommended)
- Services: `dagster-webserver` and `dagster-daemon`
- Reliability: automatic restart and reboot persistence via systemd
- Health checks: service state + HTTP endpoint verification

## Prerequisites

1. Launch EC2 instance and allow inbound TCP `3000` from trusted CIDR.
2. SSH into the host as a user with sudo access.
3. Clone repository to `/opt/smart-energy-ai` (or set `REPO_ROOT` when running script).

Example:

```bash
sudo mkdir -p /opt
sudo chown "$USER":"$USER" /opt
cd /opt
git clone https://github.com/ilyafefelov/smart-energy-ai.git
cd smart-energy-ai
```

## One-Command Setup

Run the setup script as root:

```bash
cd /opt/smart-energy-ai
sudo REPO_ROOT=/opt/smart-energy-ai SERVICE_USER=ubuntu bash scripts/ec2/setup-dagster-services.sh
```

What it does:

- installs required OS packages (`python3`, `python3-venv`, `pip`, `curl`, `jq`)
- creates and populates `.venv`
- installs Dagster dependencies and `dagster-webserver`
- writes `/etc/smart-energy-ai/dagster.env`
- renders and installs systemd units from `deploy/systemd/`
- enables services at boot and starts both services
- validates health via `/server_info`

## Service Configuration Files

- Env file: `/etc/smart-energy-ai/dagster.env`
- Unit files:
  - `/etc/systemd/system/dagster-webserver.service`
  - `/etc/systemd/system/dagster-daemon.service`
- Source templates in repo:
  - `deploy/systemd/dagster-webserver.service`
  - `deploy/systemd/dagster-daemon.service`
  - `deploy/systemd/dagster.env.example`

## Lifecycle Commands

```bash
sudo systemctl status dagster-webserver.service
sudo systemctl status dagster-daemon.service

sudo systemctl restart dagster-webserver.service
sudo systemctl restart dagster-daemon.service

sudo journalctl -u dagster-webserver.service -f
sudo journalctl -u dagster-daemon.service -f
```

## Health Checks

Run:

```bash
bash scripts/ec2/check-dagster-services.sh
```

Expected output:

- `dagster-webserver.service active: 1`
- `dagster-daemon.service active: 1`
- `dagster web health endpoint reachable: 1`

## Reboot Validation

```bash
sudo reboot
# reconnect after reboot
sudo systemctl is-active dagster-webserver.service
sudo systemctl is-active dagster-daemon.service
bash /opt/smart-energy-ai/scripts/ec2/check-dagster-services.sh
```

Both services must report `active` and health check must pass.

## Troubleshooting

1. Missing package `dagster-webserver`:

```bash
sudo -u ubuntu /opt/smart-energy-ai/.venv/bin/python -m pip install dagster-webserver
```

2. Wrong module path:

- Update `DAGSTER_MODULE` in `/etc/smart-energy-ai/dagster.env`
- Reload and restart:

```bash
sudo systemctl daemon-reload
sudo systemctl restart dagster-webserver.service dagster-daemon.service
```

3. Port conflicts on `3000`:

```bash
sudo ss -ltnp | grep 3000
```

Then update `DAGSTER_PORT` in env file if needed.

## Security Notes

- Do not expose `3000` to `0.0.0.0/0` in production.
- Place Dagster behind reverse proxy or private network access where possible.
- Store credentials outside repo and inject through `/etc/smart-energy-ai/dagster.env`.
