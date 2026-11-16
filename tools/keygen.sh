#!/usr/bin/env bash
# Genera la clave de firma del proyecto (Ed25519). Ejecútalo UNA vez, en tu equipo.
#  - La privada queda en ~/.config/mitallercito/signing.key  → NO la subas al repo. Guárdala con copia.
#    Para firmar desde GitHub Actions, pégala como secreto SIGNING_KEY del repositorio.
#  - La pública se escribe en signing.pub y se incrusta en tools/mitallercito-lxc.sh  → sí va al repo.
set -euo pipefail
cd "$(dirname "$0")/.."
KEY=${MT_SIGNING_KEY:-$HOME/.config/mitallercito/signing.key}
if [[ -f "$KEY" ]]; then echo "Ya existe $KEY (no la sobrescribo)"; else
  mkdir -p "$(dirname "$KEY")"; umask 077
  openssl genpkey -algorithm ed25519 -out "$KEY"
  echo "Clave privada: $KEY"
fi
openssl pkey -in "$KEY" -pubout -out signing.pub
python3 - <<'PY'
import re
pub = open("signing.pub").read().strip()
p = "tools/mitallercito-lxc.sh"; s = open(p).read()
s = re.sub(r"(# >>> SIGNING_PUB\n).*?(\n# <<< SIGNING_PUB)", lambda m: m.group(1) + "SIGNING_PUB='" + pub + "'" + m.group(2), s, flags=re.S)
open(p, "w").write(s)
PY
echo "Clave pública escrita en signing.pub y en tools/mitallercito-lxc.sh. Haz commit de ambos."
