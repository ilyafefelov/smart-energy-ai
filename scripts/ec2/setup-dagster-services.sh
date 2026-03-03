#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-/opt/smart-energy-ai}"
SERVICE_USER="${SERVICE_USER:-ubuntu}"
SERVICE_GROUP="${SERVICE_GROUP:-${SERVICE_USER}}"
VENV_PATH="${VENV_PATH:-${REPO_ROOT}/.venv}"
DAGSTER_HOME="${DAGSTER_HOME:-/var/lib/smart-energy-ai/dagster_home}"
ENV_DIR="/etc/smart-energy-ai"
ENV_FILE="${ENV_DIR}/dagster.env"
SYSTEMD_DIR="/etc/systemd/system"

info() {
  echo "[INFO] $*"
}

error() {
  echo "[ERROR] $*" >&2
  exit 1
}

require_root() {
  if [[ "${EUID}" -ne 0 ]]; then
    error "Run as root (sudo)."
  fi
}

require_repo() {
  [[ -d "${REPO_ROOT}" ]] || error "Repository path not found: ${REPO_ROOT}"
  [[ -f "${REPO_ROOT}/requirements.txt" ]] || error "Missing requirements.txt under ${REPO_ROOT}"
  [[ -f "${REPO_ROOT}/deploy/systemd/dagster-webserver.service" ]] || error "Missing deploy/systemd templates in repository"
}

require_user() {
  id -u "${SERVICE_USER}" >/dev/null 2>&1 || error "Service user not found: ${SERVICE_USER}"
}

install_os_packages() {
  info "Installing OS dependencies (apt)..."
  apt-get update
  DEBIAN_FRONTEND=noninteractive apt-get install -y python3 python3-venv python3-pip curl jq
}

bootstrap_python_env() {
  info "Bootstrapping Python virtual environment at ${VENV_PATH}"
  if [[ ! -x "${VENV_PATH}/bin/python" ]]; then
    sudo -u "${SERVICE_USER}" python3 -m venv "${VENV_PATH}"
  fi

  sudo -u "${SERVICE_USER}" "${VENV_PATH}/bin/python" -m pip install --upgrade pip wheel
  sudo -u "${SERVICE_USER}" "${VENV_PATH}/bin/python" -m pip install -r "${REPO_ROOT}/requirements.txt"
  sudo -u "${SERVICE_USER}" "${VENV_PATH}/bin/python" -m pip install dagster-webserver
}

prepare_directories() {
  info "Preparing Dagster directories"
  mkdir -p "${DAGSTER_HOME}" "${ENV_DIR}"
  chown -R "${SERVICE_USER}:${SERVICE_GROUP}" "${DAGSTER_HOME}"
}

write_env_file() {
  info "Writing ${ENV_FILE}"
  cat > "${ENV_FILE}" <<EOF
DAGSTER_HOME=${DAGSTER_HOME}
DAGSTER_MODULE=src.definitions
DAGSTER_PORT=3000
DAGSTER_WEBSERVER_CMD=${VENV_PATH}/bin/dagster-webserver
DAGSTER_DAEMON_CMD=${VENV_PATH}/bin/dagster-daemon
PYTHONPATH=${REPO_ROOT}
DAGSTER_LOG_LEVEL=INFO
EOF
  chmod 640 "${ENV_FILE}"
}

render_unit() {
  local src="$1"
  local dst="$2"

  sed \
    -e "s|__REPO_ROOT__|${REPO_ROOT}|g" \
    -e "s|__SERVICE_USER__|${SERVICE_USER}|g" \
    -e "s|__SERVICE_GROUP__|${SERVICE_GROUP}|g" \
    "${src}" > "${dst}"
}

install_systemd_units() {
  info "Installing systemd service units"
  render_unit "${REPO_ROOT}/deploy/systemd/dagster-webserver.service" "${SYSTEMD_DIR}/dagster-webserver.service"
  render_unit "${REPO_ROOT}/deploy/systemd/dagster-daemon.service" "${SYSTEMD_DIR}/dagster-daemon.service"

  systemctl daemon-reload
  systemctl enable dagster-webserver.service dagster-daemon.service
}

start_services() {
  info "Restarting Dagster services"
  systemctl restart dagster-webserver.service
  systemctl restart dagster-daemon.service
}

validate_services() {
  # shellcheck disable=SC1090
  source "${ENV_FILE}"

  info "Validating service health"
  systemctl is-active --quiet dagster-webserver.service || error "dagster-webserver is not active"
  systemctl is-active --quiet dagster-daemon.service || error "dagster-daemon is not active"
  curl --fail --silent "http://127.0.0.1:${DAGSTER_PORT}/server_info" >/dev/null || error "Dagster webserver health check failed"

  info "Dagster webserver and daemon are healthy"
}

print_next_steps() {
  cat <<EOF

Setup complete.

Useful commands:
  sudo systemctl status dagster-webserver.service
  sudo systemctl status dagster-daemon.service
  sudo journalctl -u dagster-webserver.service -f
  sudo journalctl -u dagster-daemon.service -f
  bash ${REPO_ROOT}/scripts/ec2/check-dagster-services.sh

After reboot, verify:
  sudo systemctl is-active dagster-webserver.service
  sudo systemctl is-active dagster-daemon.service
EOF
}

main() {
  require_root
  require_repo
  require_user
  install_os_packages
  bootstrap_python_env
  prepare_directories
  write_env_file
  install_systemd_units
  start_services
  validate_services
  print_next_steps
}

main "$@"
