#!/bin/sh
# Genera la clave de sesión la primera vez y avisa del enlace de primer arranque.
set -e
if [ -z "$MT_SECRET" ]; then
  [ -f /data/.secret ] || python -c "import secrets;print(secrets.token_hex(32))" > /data/.secret
  export MT_SECRET="$(cat /data/.secret)"
fi
TOKEN=$(python app.py setup-token 2>/dev/null || true)
case "$TOKEN" in
  ""|La*) ;;
  *) echo "=================================================================="
     echo " MiTallercito: primer arranque. Abre  http://<IP>:${PORT:-8080}/#setup=$TOKEN"
     echo "==================================================================";;
esac
# avisos (Telegram) cada 10 minutos
( while sleep 600; do python app.py notify >/dev/null 2>&1 || true; done ) &
exec gunicorn -w 2 -b 0.0.0.0:${PORT:-8080} --access-logfile - app:app
