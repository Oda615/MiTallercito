# Colaborar

¡Gracias por echar una mano! Issues, ideas y pull requests son bienvenidos.

## Montar el entorno
```bash
git clone https://github.com/Oda615/MiTallercito && cd mitallercito
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt pytest
MT_DATA_DIR=/tmp/mt python tools/demo_data.py   # datos de ejemplo (demo / demo1234)
MT_DATA_DIR=/tmp/mt python app.py               # http://127.0.0.1:8080
```

## Estructura
```
app.py                 backend Flask + SQLite (API, cálculos, migraciones de BD)
static/                interfaz (HTML + JS + CSS, sin build)
install.sh             instalación dentro del LXC/VM (systemd, aplicador, CLI)
updater/               aplicador de actualizaciones (root) y verificador de paquetes
ct/, install/          instalador para el host Proxmox con el motor de community-scripts
tools/mitallercito-lxc.sh  instalador clásico y autónomo (sin conexión, con --file)
bridge/                puente para impresoras en otra red
tools/                 publicar versiones, claves de firma, datos de ejemplo
tests/                 pytest
```

## Antes de abrir un PR
- `python -m pytest -q tests` en verde y `node --check static/app.js`.
- Cambios en la base de datos: añade la columna en `MIGRATIONS` (`app.py`), nunca borres columnas.
- Cambios en la calculadora: añade o ajusta tests en `tests/test_calc.py`.
- Textos de la interfaz en español; código y comentarios en español o inglés, como veas.

## Publicar una versión (mantenedores)
1. **Una vez**: `bash tools/keygen.sh`. La clave privada queda en `~/.config/mitallercito/signing.key`: guárdala con copia y **no la subas**. Haz commit de `signing.pub` y de `tools/mitallercito-lxc.sh` (lleva la clave pública incrustada). Añade la privada como secreto del repo `SIGNING_KEY` (Settings → Secrets and variables → Actions).
2. Sube el número en `VERSION` y añade la entrada en `CHANGELOG.md`.
3. `git tag vX.Y.Z && git push --tags`. GitHub Actions pasa los tests, construye `mitallercito-X.Y.Z.mtc` firmado, crea la versión y publica la imagen en `ghcr.io/oda615/mitallercito`.
