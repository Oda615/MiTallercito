#!/usr/bin/env bash
# Pone el nombre del repositorio de GitHub (usuario/repo) en todos los sitios.
#   bash tools/set-repo.sh miusuario/mitallercito
set -euo pipefail
cd "$(dirname "$0")/.."
R="${1:?uso: tools/set-repo.sh usuario/repo}"
[[ "$R" =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]] || { echo "formato: usuario/repo"; exit 1; }
OLD=$(cat REPO)
grep -rl --exclude-dir=.git --exclude-dir=dist -e "$OLD" . | xargs sed -i "s#$OLD#$R#g"
echo "$R" > REPO
echo "Repositorio: $R"
