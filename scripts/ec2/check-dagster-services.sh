#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="${ENV_FILE:-/etc/smart-energy-ai/dagster.env}"

if [[ -f "${ENV_FILE}" ]]; then
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
else
  DAGSTER_PORT="${DAGSTER_PORT:-3000}"
fi

WEB_OK=0
DAEMON_OK=0
HTTP_OK=0

if systemctl is-active --quiet dagster-webserver.service; then
  WEB_OK=1
fi

if systemctl is-active --quiet dagster-daemon.service; then
  DAEMON_OK=1
fi

if curl --fail --silent "http://127.0.0.1:${DAGSTER_PORT:-3000}/server_info" >/dev/null; then
  HTTP_OK=1
fi

echo "dagster-webserver.service active: ${WEB_OK}"
echo "dagster-daemon.service active: ${DAEMON_OK}"
echo "dagster web health endpoint reachable: ${HTTP_OK}"

if [[ "${WEB_OK}" -eq 1 && "${DAEMON_OK}" -eq 1 && "${HTTP_OK}" -eq 1 ]]; then
  echo "Dagster service health check passed"
  exit 0
fi

echo "Dagster service health check failed"
echo "Recent logs:"
sudo journalctl -u dagster-webserver.service -n 20 --no-pager || true
sudo journalctl -u dagster-daemon.service -n 20 --no-pager || true
exit 1
