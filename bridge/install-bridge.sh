#!/usr/bin/env bash
# Instala el puente de MiTallercito como servicio en Debian/Ubuntu/Raspberry Pi OS.
#   curl -fsSL https://raw.githubusercontent.com/Oda615/MiTallercito/main/bridge/install-bridge.sh | \
#     sudo bash -s -- --url https://tienda.midominio.com --token mtb_xxxxx
set -euo pipefail
REPO="Oda615/MiTallercito"
URL=""; TOKEN=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --url) URL="$2"; shift 2;; --token) TOKEN="$2"; shift 2;;
    *) echo "opción desconocida: $1"; exit 1;;
  esac
done
[[ $EUID -eq 0 ]] || { echo "Ejecuta como root (sudo)"; exit 1; }
[[ -n "$URL" && -n "$TOKEN" ]] || { echo "uso: install-bridge.sh --url https://tu-tienda --token mtb_…"; exit 1; }
command -v python3 >/dev/null || { apt-get update -q && apt-get install -y -q python3; }

id mitallercito-bridge &>/dev/null || useradd -r -s /usr/sbin/nologin -M mitallercito-bridge
SRC="$(cd "$(dirname "${BASH_SOURCE[0]:-.}")" 2>/dev/null && pwd || echo .)"
if [[ -f "$SRC/mitallercito-bridge.py" ]]; then
  install -m 755 "$SRC/mitallercito-bridge.py" /usr/local/bin/mitallercito-bridge
else
  curl -fsSL "https://raw.githubusercontent.com/$REPO/main/bridge/mitallercito-bridge.py" -o /usr/local/bin/mitallercito-bridge
  chmod 755 /usr/local/bin/mitallercito-bridge
fi
umask 077
cat >/etc/mitallercito-bridge.env <<EOF
MT_URL=$URL
BRIDGE_TOKEN=$TOKEN
EOF
chown root:mitallercito-bridge /etc/mitallercito-bridge.env; chmod 640 /etc/mitallercito-bridge.env
cat >/etc/systemd/system/mitallercito-bridge.service <<'EOF'
[Unit]
Description=MiTallercito - puente de impresoras
After=network-online.target
Wants=network-online.target

[Service]
User=mitallercito-bridge
ExecStart=/usr/bin/python3 /usr/local/bin/mitallercito-bridge
Restart=always
RestartSec=10
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable -q --now mitallercito-bridge
sleep 3
journalctl -u mitallercito-bridge -n 5 --no-pager || true
echo "Puente instalado. Logs: journalctl -u mitallercito-bridge -f"
