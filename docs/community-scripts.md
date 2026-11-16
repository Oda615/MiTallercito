# MiTallercito en community-scripts (Proxmox VE Helper-Scripts)

## Dónde estamos

`ct/mitallercito.sh` e `install/mitallercito-install.sh` ya siguen el formato de community-scripts y usan su motor
(`community-scripts/core`). Mientras no estemos en su catálogo, `ct/mitallercito.sh` le dice al motor que coja los
scripts de este repo (`COMMUNITY_SCRIPTS_URL`). Para el usuario es idéntico a un Helper-Script oficial: modo por
defecto o avanzado, almacenamiento, red, IPv6, SSH, comando `update` dentro del contenedor…

## Requisitos para que acepten una app nueva

Del formulario de PR de su repositorio de pruebas (DevScripts, antes ProxmoxVED):

- [ ] La app tiene **al menos 6 meses**.
- [ ] Se **mantiene activamente**.
- [ ] Tiene **600+ estrellas** en GitHub.
- [x] Publica **tarballs oficiales** de cada versión (las Releases de GitHub con su tag).
- Aun cumpliéndolo todo, pueden no aceptarla.

Además: las apps nuevas **solo** entran por DevScripts; los PR con apps nuevas en ProxmoxVE se cierran sin revisar.

## Cuando cumplamos los requisitos

1. Haz fork de `community-scripts/DevScripts` y crea una rama `feat/mitallercito`.
2. Copia `ct/mitallercito.sh` y `install/mitallercito-install.sh`.
3. En `ct/mitallercito.sh`, **borra** las líneas propias de este repo (antes del `_cs_boot=`):
   - el bloque `if [[ "${1:-}" =~ ^(update|--file|--main)$ ]]; then … fi`
   - `export COMMUNITY_SCRIPTS_URL=…`
   - la función `get_header` con el rótulo (su generador crea el de cada app)
4. Pruébalo en un Proxmox real desde tu fork, con depuración:
   `dev_mode="trace,keep" bash -c "$(curl -fsSL https://raw.githubusercontent.com/<tu-usuario>/DevScripts/feat/mitallercito/ct/mitallercito.sh)"`
   Prueba instalación por defecto, avanzada (IP fija, VLAN) y `update` dentro del contenedor.
5. Abre el PR en DevScripts solo con esos dos archivos. Nombre, descripción, logo, categoría y puerto se piden
   después en su web (enlace «Report Issue» de la ficha), no van en el repo.

### Borrador del PR

> **New script: MiTallercito**
>
> Self-hosted web app to run a small 3D-printing shop: price calculator (material per colour, electricity,
> machine wear, labour, failure risk, VAT, marketplace fees), orders, customers, market-stall POS, spool stock
> room with filament forecast, printer status and maintenance (Moonraker, OctoPrint, PrusaLink), bookkeeping
> and Telegram alerts. Flask + SQLite, ~60 MB RAM idle.
>
> - Source: https://github.com/Oda615/MiTallercito
> - Port 8080 · first-run link printed at the end (no default credentials)
> - Debian 13, unprivileged, 1 CPU / 512 MB / 4 GB, arm64 OK
> - Updates via `check_for_gh_release` + release tarball; the DB is backed up first

## Mientras tanto: darse a conocer

Lo que más estrellas trae para una app así:

- Un post con capturas en r/selfhosted, r/3Dprinting y r/Proxmox (en inglés), y en foros y grupos de impresión 3D en español.
- Abrir una petición en *Discussions → Request script* del repo ProxmoxVE: los votos ayudan a que la acepten.
- Proponerla en listas como awesome-selfhosted cuando tenga unos meses de vida.
- Mantener Releases con notas claras y capturas actualizadas en el README.
