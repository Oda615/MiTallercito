#!/usr/bin/env bash
# MiTallercito – aplicador de actualizaciones (root, lanzado por systemd: mitallercito-update.path).
#
# La web (usuario mitallercito, sin privilegios) solo deja el paquete y una petición en
#   /var/lib/mitallercito/updates/{pending.tar.gz,request.json}
# Este script:
#   1. valida el paquete con /usr/local/lib/mitallercito/verify.py (firma Ed25519 si hay clave
#      pública en /etc/mitallercito/signing.pub; formato; rutas; sin enlaces);
#   2. copia la BD;
#   3. copia SOLO ficheros de la app (nunca ejecuta nada del paquete como root);
#   4. instala dependencias como el usuario mitallercito;
#   5. reinicia y comprueba que arranca; si no, vuelve a la versión anterior.
# Ni este script ni verify.py ni la clave pública se actualizan desde la web.
set -uo pipefail

APP=${MT_APP:-/opt/mitallercito}
PREV=${MT_PREV:-/opt/mitallercito.prev}
DATA=${MT_DATA:-/var/lib/mitallercito}
LIB=${MT_LIB:-/usr/local/lib/mitallercito}
PUBKEY=${MT_PUBKEY:-/etc/mitallercito/signing.pub}
UNIT=${MT_UNIT:-/etc/systemd/system/mitallercito.service}
UPD=$DATA/updates
STATUS=$UPD/status.json
LOG=$UPD/history.log
PORT=$(grep -oP '(?<=-b 0\.0\.0\.0:)\d+' "$UNIT" 2>/dev/null || echo 8080)
FILES=(app.py static requirements.txt VERSION COMMIT REPO README.md LICENSE CHANGELOG.md)
[[ -f /etc/default/mitallercito ]] && ALLOW_UNSIGNED=$(grep -oP '(?<=^MT_ALLOW_UNSIGNED=)\S+' /etc/default/mitallercito || true)
export MT_ALLOW_UNSIGNED=${ALLOW_UNSIGNED:-0}

exec 9>"${MT_LOCK:-/run/mitallercito-update.lock}"
flock -n 9 || exit 0
sleep 2   # deja que la petición HTTP que lo ha lanzado termine

ver(){ cat "$1/VERSION" 2>/dev/null || echo "desconocida"; }
# Desde la 0.6.0 hay avisos por Telegram con su temporizador. Las instalaciones anteriores no lo
# tienen, así que se crea aquí (contenido fijo, no sale del paquete).
ensure_notify_timer(){
  [[ -d /run/systemd/system ]] || return 0
  [[ -f /etc/systemd/system/mitallercito-notify.timer ]] && return 0
  cat >/etc/systemd/system/mitallercito-notify.service <<EOF
[Unit]
Description=MiTallercito - avisos (Telegram)

[Service]
Type=oneshot
User=mitallercito
EnvironmentFile=/etc/default/mitallercito
WorkingDirectory=$APP
ExecStart=$APP/venv/bin/python app.py notify
EOF
  cat >/etc/systemd/system/mitallercito-notify.timer <<'EOF'
[Unit]
Description=MiTallercito - avisos cada 10 minutos

[Timer]
OnBootSec=3min
OnUnitActiveSec=10min

[Install]
WantedBy=timers.target
EOF
  systemctl daemon-reload && systemctl enable -q --now mitallercito-notify.timer
}
status(){ # estado mensaje
  python3 - "$STATUS" "$1" "$2" <<'PY'
import json, sys, datetime
p, st, msg = sys.argv[1:4]
json.dump({"state": st, "message": msg, "time": datetime.datetime.now().isoformat(timespec="seconds")},
          open(p, "w"), ensure_ascii=False)
PY
  chown mitallercito:mitallercito "$STATUS"
  echo "$(date '+%F %T') [$1] $2" >> "$LOG"; chown mitallercito:mitallercito "$LOG"
}
healthy(){
  for _ in $(seq 1 15); do
    python3 -c "import urllib.request,sys;sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:$PORT/api/brand',timeout=3).status==200 else 1)" 2>/dev/null && return 0
    sleep 2
  done
  return 1
}
deps(){ runuser -u mitallercito -- "$APP/venv/bin/pip" install -q -r "$APP/requirements.txt"; }
restore_prev(){ for f in "${FILES[@]}"; do rm -rf "${APP:?}/$f"; [[ -e "$PREV/$f" ]] && cp -a "$PREV/$f" "$APP/"; done; }

REQ=$(cat "$UPD/request.json" 2>/dev/null || echo '{}')
ACTION=$(python3 -c "import json,sys;print(json.loads(sys.argv[1]).get('action',''))" "$REQ" 2>/dev/null)
WHO=$(python3 -c "import json,sys;print(json.loads(sys.argv[1]).get('user','?'))" "$REQ" 2>/dev/null)
rm -f "$UPD/request.json"

# ---------------------------------------------------------------- volver a la anterior
if [[ "$ACTION" == "rollback" ]]; then
  [[ -f "$PREV/app.py" ]] || { status error "No hay versión anterior guardada"; exit 1; }
  status running "Volviendo a la versión $(ver "$PREV") (pedido por $WHO)"
  TMP=$(mktemp -d)
  for f in "${FILES[@]}"; do [[ -e "$APP/$f" ]] && cp -a "$APP/$f" "$TMP/"; done
  restore_prev
  rm -rf "$PREV"; mkdir -p "$PREV"; cp -a "$TMP/." "$PREV/"; rm -rf "$TMP"
  deps; systemctl restart mitallercito
  if healthy; then status ok "Versión $(ver "$APP") restaurada (por $WHO)"; else status error "La versión restaurada no arranca: journalctl -u mitallercito"; fi
  exit 0
fi

[[ "$ACTION" == "update" && -f "$UPD/pending.tar.gz" ]] || exit 0

# ---------------------------------------------------------------- validar
WORK=$(mktemp -d); trap 'rm -rf "$WORK"' EXIT
install -m 600 "$UPD/pending.tar.gz" "$WORK/pkg"     # copia propia: el original no se puede cambiar a mitad
rm -f "$UPD/pending.tar.gz"
SHA=$(sha256sum "$WORK/pkg" | cut -c1-16)
status running "Validando paquete (sha256 $SHA…) de $WHO"

OUT=$(python3 "$LIB/verify.py" "$WORK/pkg" "$WORK" "$PUBKEY")
if [[ $? -ne 0 ]]; then
  MSG=$(python3 -c "import json,sys;print(json.loads(sys.argv[1]).get('error','formato no válido'))" "$OUT" 2>/dev/null || echo "formato no válido")
  status error "Paquete rechazado: $MSG"; exit 1
fi
NEW=$(python3 -c "import json,sys;print(json.loads(sys.argv[1])['dir'])" "$OUT")
SIGNED=$(python3 -c "import json,sys;print('firmado ✓' if json.loads(sys.argv[1])['signed'] else 'SIN FIRMA')" "$OUT")
NEWV=$(ver "$NEW"); OLDV=$(ver "$APP")

# ---------------------------------------------------------------- copia + aplicar
mkdir -p "$DATA/backups"
DBB="$DATA/backups/antes-de-$NEWV-$(date +%F-%H%M%S).db"
python3 -c "import sqlite3,sys;s=sqlite3.connect(sys.argv[1]);d=sqlite3.connect(sys.argv[2]);s.backup(d);d.close()" \
  "$DATA/mitallercito.db" "$DBB" && chown mitallercito:mitallercito "$DBB"
status running "Instalando $NEWV ($SIGNED; antes $OLDV); copia de la BD en $(basename "$DBB")"

rm -rf "$PREV"; mkdir -p "$PREV"
for f in "${FILES[@]}"; do [[ -e "$APP/$f" ]] && cp -a "$APP/$f" "$PREV/"; done
rm -f "$APP/COMMIT"   # solo lo traen los paquetes hechos desde la rama main
for f in "${FILES[@]}"; do
  [[ -e "$NEW/$f" ]] || continue
  rm -rf "${APP:?}/$f"; cp -a "$NEW/$f" "$APP/"
done
chown -R root:root "$APP/static" "$APP/app.py" "$APP/requirements.txt" "$APP/VERSION" 2>/dev/null

if ! deps; then
  status error "Fallo instalando dependencias; vuelvo a $OLDV"
  restore_prev; systemctl restart mitallercito; exit 1
fi
systemctl restart mitallercito

if healthy; then
  ensure_notify_timer || true
  status ok "Actualizado de $OLDV a $NEWV ($SIGNED, por $WHO)"
else
  restore_prev; deps; systemctl restart mitallercito
  status error "La versión $NEWV no arrancaba; se ha vuelto a $OLDV automáticamente. Logs: journalctl -u mitallercito"
fi
