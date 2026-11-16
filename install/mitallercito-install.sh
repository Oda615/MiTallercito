#!/usr/bin/env bash

# Copyright (c) 2021-2026 community-scripts ORG
# Author: Oda615
# License: MIT | https://github.com/community-scripts/ProxmoxVE/raw/main/LICENSE
# Source: https://github.com/Oda615/MiTallercito

source /dev/stdin <<<"$FUNCTIONS_FILE_PATH"
color
verb_ip6
catch_errors
setting_up_container
network_check
update_os

msg_info "Installing Dependencies"
$STD apt install -y python3 python3-venv sqlite3 openssl cron
msg_ok "Installed Dependencies"

fetch_and_deploy_gh_release "mitallercito" "Oda615/MiTallercito" "tarball" "latest" "/opt/mitallercito-src"

msg_info "Installing MiTallercito"
$STD bash /opt/mitallercito-src/install.sh
rm -rf /opt/mitallercito-src
msg_ok "Installed MiTallercito"

motd_ssh
customize
cleanup_lxc
