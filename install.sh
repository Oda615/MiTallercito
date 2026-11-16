#!/usr/bin/env bash
# Instala o actualiza MiTallercito dentro de un LXC/VM Debian 12+ o Ubuntu 22.04+.
# Normalmente lo lanza install/mitallercito-install.sh (o tools/mitallercito-lxc.sh) desde el host Proxmox. A mano (como root,
# desde la carpeta descomprimida):   bash install.sh
set -euo pipefail

APP_DIR=/opt/mitallercito
DATA_DIR=/var/lib/mitallercito
LIB_DIR=/usr/local/lib/mitallercito
PORT="${PORT:-8080}"
SRC="$(cd "$(dirname "$0")" && pwd)"

msg(){ echo -e "\e[1;33m[mitallercito]\e[0m $*"; }
err(){ echo -e "\e[1;31m[mitallercito] ERROR\e[0m $*" >&2; }
trap 'err "falló en la línea $LINENO: $BASH_COMMAND"' ERR
[[ $EUID -eq 0 ]] || { err "Ejecuta como root"; exit 1; }

# ---- migración desde el nombre antiguo («Tienda 3D», rutas tienda3d)
if [[ -d /opt/tienda3d && ! -d /opt/mitallercito ]]; then
  msg "Migrando instalación anterior: Tienda 3D → MiTallercito (datos y usuarios se conservan)"
  systemctl disable --now tienda3d tienda3d-update.path 2>/dev/null || true
  [[ -f /var/lib/tienda3d/tienda3d.db ]] && sqlite3 /var/lib/tienda3d/tienda3d.db ".backup '/root/tienda3d-antes-de-migrar-$(date +%F-%H%M).db'" 2>/dev/null || true
  mv /opt/tienda3d /opt/mitallercito && rm -rf /opt/mitallercito/venv /opt/tienda3d.prev
  if [[ -d /var/lib/tienda3d ]]; then
    mv /var/lib/tienda3d /var/lib/mitallercito
    [[ -f /var/lib/mitallercito/tienda3d.db ]] && mv /var/lib/mitallercito/tienda3d.db /var/lib/mitallercito/mitallercito.db
  fi
  if id tienda3d &>/dev/null; then
    usermod -l mitallercito -d /var/lib/mitallercito tienda3d
    getent group tienda3d >/dev/null && groupmod -n mitallercito tienda3d
  fi
  if [[ -f /etc/default/tienda3d ]]; then
    sed -e 's/^TIENDA_/MT_/' -e 's#/var/lib/tienda3d#/var/lib/mitallercito#g' /etc/default/tienda3d > /etc/default/mitallercito
    chmod 600 /etc/default/mitallercito && rm -f /etc/default/tienda3d
  fi
  [[ -d /etc/tienda3d ]] && mv /etc/tienda3d /etc/mitallercito
  rm -f /etc/systemd/system/tienda3d.service /etc/systemd/system/tienda3d-update.path /etc/systemd/system/tienda3d-update.service \
        /usr/local/bin/tienda3d /usr/bin/tienda3d /usr/local/sbin/tienda3d-updater /etc/cron.daily/tienda3d-backup /etc/profile.d/00-tienda3d.sh
  rm -rf /usr/local/lib/tienda3d
  systemctl daemon-reload
fi

msg "Comprobando red"
for i in $(seq 1 30); do
  getent hosts deb.debian.org >/dev/null 2>&1 && break
  [[ $i -eq 30 ]] && { err "sin DNS/Internet (revisa red/gateway/DNS)"; exit 1; }
  sleep 2
done

msg "Instalando dependencias del sistema"
apt-get update -q
DEBIAN_FRONTEND=noninteractive apt-get install -y -q python3 python3-venv sqlite3 openssl cron

msg "Copiando la app a $APP_DIR"
id mitallercito &>/dev/null || useradd -r -s /usr/sbin/nologin -d "$DATA_DIR" mitallercito
mkdir -p "$APP_DIR" "$DATA_DIR" "$LIB_DIR"
rm -rf "$APP_DIR/static"
rm -f "$APP_DIR/COMMIT"
for f in app.py static requirements.txt VERSION COMMIT REPO README.md LICENSE CHANGELOG.md; do
  [[ -e "$SRC/$f" ]] && cp -r "$SRC/$f" "$APP_DIR/"
done
chown -R root:root "$APP_DIR/app.py" "$APP_DIR/static"
[[ -x "$APP_DIR/venv/bin/pip" ]] || python3 -m venv "$APP_DIR/venv"
# el venv es del usuario mitallercito: así las actualizaciones web instalan dependencias sin root
chown -R mitallercito:mitallercito "$APP_DIR/venv"
msg "Instalando Flask y gunicorn"
runuser -u mitallercito -- "$APP_DIR/venv/bin/pip" install -q --upgrade pip
runuser -u mitallercito -- "$APP_DIR/venv/bin/pip" install -q -r "$APP_DIR/requirements.txt"
mkdir -p "$DATA_DIR/updates" "$DATA_DIR/backups"
chown -R mitallercito:mitallercito "$DATA_DIR"

if [[ ! -f /etc/default/mitallercito ]]; then
cat >/etc/default/mitallercito <<EOF
MT_DATA_DIR=$DATA_DIR
MT_SECRET=$(python3 -c 'import secrets;print(secrets.token_hex(32))')
EOF
chmod 600 /etc/default/mitallercito
fi
grep -q '^MT_PROXY_HOPS=' /etc/default/mitallercito || echo 'MT_PROXY_HOPS=1' >> /etc/default/mitallercito

# ---- aplicador de actualizaciones (root) + verificador + clave pública del proyecto
msg "Instalando el aplicador de actualizaciones"
install -m 755 "$SRC/updater/updater.sh" /usr/local/sbin/mitallercito-updater
install -m 644 "$SRC/updater/verify.py" "$LIB_DIR/verify.py"
if [[ -f "$SRC/signing.pub" ]]; then
  install -d -m 755 /etc/mitallercito
  install -m 644 "$SRC/signing.pub" /etc/mitallercito/signing.pub
  msg "Clave pública instalada: solo se aceptarán actualizaciones firmadas"
fi

cat >/etc/systemd/system/mitallercito.service <<EOF
[Unit]
Description=MiTallercito
After=network.target

[Service]
User=mitallercito
EnvironmentFile=/etc/default/mitallercito
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/venv/bin/gunicorn -w 2 -b 0.0.0.0:$PORT app:app
Restart=on-failure
NoNewPrivileges=true
ProtectSystem=full
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF
# ---- avisos (Telegram): cada 10 minutos, como el usuario sin privilegios
cat >/etc/systemd/system/mitallercito-notify.service <<EOF
[Unit]
Description=MiTallercito - avisos (Telegram)

[Service]
Type=oneshot
User=mitallercito
EnvironmentFile=/etc/default/mitallercito
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/venv/bin/python app.py notify
EOF
cat >/etc/systemd/system/mitallercito-notify.timer <<EOF
[Unit]
Description=MiTallercito - avisos cada 10 minutos

[Timer]
OnBootSec=3min
OnUnitActiveSec=10min

[Install]
WantedBy=timers.target
EOF
cat >/etc/systemd/system/mitallercito-update.path <<EOF
[Unit]
Description=MiTallercito - vigila peticiones de actualización desde la web

[Path]
PathChanged=$DATA_DIR/updates/request.json
Unit=mitallercito-update.service

[Install]
WantedBy=multi-user.target
EOF
cat >/etc/systemd/system/mitallercito-update.service <<EOF
[Unit]
Description=MiTallercito - aplicar actualización subida desde la web

[Service]
Type=oneshot
ExecStart=/usr/local/sbin/mitallercito-updater
EOF

# ---- comando de gestión
cat >/usr/local/bin/mitallercito <<'EOF'
#!/usr/bin/env bash
set -e
set -a; source /etc/default/mitallercito; set +a
case "${1:-}" in
  backup) f="/root/mitallercito-$(date +%F-%H%M).db"; sqlite3 "$MT_DATA_DIR/mitallercito.db" ".backup '$f'"; echo "$f";;
  status) systemctl --no-pager status mitallercito;;
  logs)   journalctl -u mitallercito -f;;
  restart) systemctl restart mitallercito && echo ok;;
  version) cat /opt/mitallercito/VERSION;;
  notify) cd /opt/mitallercito && runuser -u mitallercito -- ./venv/bin/python app.py notify;;
  adduser|passwd|deluser|users|role|setup-token)
          cd /opt/mitallercito && runuser -u mitallercito -- ./venv/bin/python app.py "$@";;   # hereda el entorno exportado
  *) echo "uso: mitallercito adduser <usuario> [--admin] | passwd <usuario> | deluser <usuario> | role <usuario> admin|user"
     echo "             users | setup-token | backup | status | logs | restart | version";;
esac
EOF
chmod +x /usr/local/bin/mitallercito
ln -sf /usr/local/bin/mitallercito /usr/bin/mitallercito
ln -sf /usr/local/bin/mitallercito /usr/local/bin/tienda3d   # alias del nombre antiguo

# ---- backup diario (guarda 30)
mkdir -p /etc/cron.daily
cat >/etc/cron.daily/mitallercito-backup <<EOF
#!/bin/sh
mkdir -p $DATA_DIR/backups
sqlite3 $DATA_DIR/mitallercito.db ".backup '$DATA_DIR/backups/mitallercito-\$(date +%F).db'"
ls -1t $DATA_DIR/backups/mitallercito-*.db | tail -n +31 | xargs -r rm -f
EOF
chmod +x /etc/cron.daily/mitallercito-backup

# ---- estilo community-scripts: autologin en la consola del LXC + MOTD con la URL
if [[ "$(systemd-detect-virt -c 2>/dev/null || true)" == "lxc" ]]; then
  OVR=/etc/systemd/system/container-getty@1.service.d/override.conf
  mkdir -p "$(dirname "$OVR")"
  cat >"$OVR" <<'EOF'
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin root --noclear --keep-baud tty%I 115200,38400,9600 $TERM
EOF
  systemctl daemon-reload
  systemctl restart container-getty@1.service || true
fi
cat >/etc/profile.d/00-mitallercito.sh <<EOF
echo -e "\n  \e[1;33mMiTallercito \$(cat /opt/mitallercito/VERSION 2>/dev/null)\e[0m  →  http://\$(hostname -I | awk '{print \$1}'):$PORT"
echo -e "  Gestión: mitallercito adduser|passwd|users|setup-token|backup|status|logs\n"
EOF
: > /etc/motd

systemctl daemon-reload
systemctl enable -q --now mitallercito mitallercito-update.path mitallercito-notify.timer
systemctl restart mitallercito
sleep 3
systemctl is-active -q mitallercito || { err "el servicio no arranca, mira: journalctl -u mitallercito -n 50"; exit 1; }

IP=$(hostname -I | awk '{print $1}')
TOKEN=$(/usr/local/bin/mitallercito setup-token 2>/dev/null || true)
if [[ -n "$TOKEN" && "$TOKEN" != La* ]]; then
  msg "Listo. Abre esto para configurar tu tienda (primer arranque):"
  echo -e "\n    \e[1;36mhttp://$IP:$PORT/#setup=$TOKEN\e[0m\n"
else
  msg "Listo → http://$IP:$PORT"
fi
