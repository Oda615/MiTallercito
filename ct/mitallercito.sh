#!/usr/bin/env bash
# MiTallercito: hasta que el script esté en community-scripts se sirve desde este repo con su mismo motor.
# (Al enviarlo a community-scripts/DevScripts se quitan este bloque y la línea de COMMUNITY_SCRIPTS_URL.)
if [[ "${1:-}" =~ ^(update|--file|--main)$ ]]; then   # órdenes del instalador clásico: siguen funcionando
  bash -c "$(curl -fsSL https://raw.githubusercontent.com/Oda615/MiTallercito/main/tools/mitallercito-lxc.sh)" -- "$@"
  exit $?
fi
export COMMUNITY_SCRIPTS_URL="${COMMUNITY_SCRIPTS_URL:-https://raw.githubusercontent.com/Oda615/MiTallercito/main}"
_cs_boot="${COMMUNITY_SCRIPTS_CORE_DIR:-$(dirname "${BASH_SOURCE[0]}")/../../core}/core/build.func"
source "$_cs_boot" 2>/dev/null || source <(curl -fsSL "${COMMUNITY_SCRIPTS_CORE_URL:-https://raw.githubusercontent.com/community-scripts/core/main}/core/build.func")
# Copyright (c) 2021-2026 community-scripts ORG
# Author: Oda615
# License: MIT | https://github.com/community-scripts/ProxmoxVE/raw/main/LICENSE
# Source: https://github.com/Oda615/MiTallercito

APP="MiTallercito"
var_tags="${var_tags:-3d-printing;business}"
var_cpu="${var_cpu:-1}"
var_ram="${var_ram:-512}"
var_disk="${var_disk:-4}"
var_os="${var_os:-debian}"
var_version="${var_version:-13}"
var_arm64="${var_arm64:-yes}"
var_unprivileged="${var_unprivileged:-1}"

header_info "$APP"
variables
color
catch_errors

function update_script() {
  header_info
  check_container_storage
  check_container_resources

  if [[ ! -d /opt/mitallercito ]]; then
    msg_error "No ${APP} Installation Found!"
    exit
  fi

  if check_for_gh_release "mitallercito" "Oda615/MiTallercito"; then
    msg_info "Backing up Database"
    $STD /usr/local/bin/mitallercito backup
    msg_ok "Backed up Database"

    CLEAN_INSTALL=1 fetch_and_deploy_gh_release "mitallercito" "Oda615/MiTallercito" "tarball" "latest" "/opt/mitallercito-src"

    msg_info "Updating ${APP}"
    $STD bash /opt/mitallercito-src/install.sh
    rm -rf /opt/mitallercito-src
    msg_ok "Updated ${APP}"
    msg_ok "Updated successfully!"
  fi
  exit
}

start
build_container
description

SETUP_TOKEN="$(pct exec "$CTID" -- /usr/local/bin/mitallercito setup-token 2>/dev/null || true)"
msg_ok "Completed Successfully!\n"
echo -e "${CREATING}${GN}${APP} setup has been successfully initialized!${CL}"
echo -e "${INFO}${YW}Open this link to create the first user (first start only):${CL}"
echo -e "${GATEWAY}${BGN}http://${IP}:8080/#setup=${SETUP_TOKEN}${CL}"
