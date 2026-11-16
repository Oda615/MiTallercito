#!/usr/bin/env bash
# =====================================================================
#  MiTallercito – crea un LXC en Proxmox con la web de pedidos, precios y
#  contabilidad para tiendas de impresión 3D.
#  https://github.com/Oda615/MiTallercito
#
#  Instalador clásico y autónomo (no depende de community-scripts). El recomendado es ct/mitallercito.sh;
#  este sirve para instalar sin conexión con un paquete .mtc o para automatizar sin menús.
#
#  En el HOST Proxmox:
#    bash -c "$(curl -fsSL https://raw.githubusercontent.com/Oda615/MiTallercito/main/tools/mitallercito-lxc.sh)"
#    bash mitallercito-lxc.sh --file mitallercito-x.y.z.mtc        (el script viene en cada versión publicada)
#
#  Actualizar un CT existente:
#    bash -c "$(curl -fsSL https://raw.githubusercontent.com/Oda615/MiTallercito/main/tools/mitallercito-lxc.sh)" -- update <CTID>
#
#  Con un paquete local en vez de descargarlo:   ... -- --file mitallercito-x.y.z.mtc [update <CTID>]
#  Lo último de la rama main (sin firma):         ... -- --main [update <CTID>]
#  (si el repo aún no tiene versiones publicadas y no hay clave de firma, se usa main automáticamente)
#  Variables opcionales (para no responder preguntas):
#    CTID HOSTNAME_CT STORAGE TPL_STORAGE BRIDGE IPCFG VLAN CORES RAM DISK TZ_CT DEBIAN MT_VERSION
#    IPCFG = dhcp | 192.168.1.50/24,gw=192.168.1.1     DEBIAN = 13 (por defecto) | 12
#    MT_NONINTERACTIVE=1 no pregunta nada · MT_KEEP=1 no borra el CT si la instalación falla
# =====================================================================
set -euo pipefail

REPO="Oda615/MiTallercito"
# Clave pública del proyecto (la escribe tools/keygen.sh). Si está, los paquetes deben ir firmados.
# >>> SIGNING_PUB
SIGNING_PUB=''
# <<< SIGNING_PUB

YW="\e[1;33m"; GN="\e[1;32m"; RD="\e[1;31m"; BL="\e[1;36m"; CL="\e[0m"
msg(){ echo -e "${YW}[mitallercito]${CL} $*"; }
ok(){ echo -e "${GN}  ✓${CL} $*"; }
die(){ echo -e "${RD}[mitallercito] ERROR${CL} $*" >&2; exit 1; }
trap 'die "falló en la línea $LINENO: $BASH_COMMAND"' ERR
ask(){ local q="$1" def="$2" var; read -rp "$(echo -e "  ${BL}${q}${CL} [${def}]: ")" var </dev/tty; echo "${var:-$def}"; }

command -v pct >/dev/null || die "esto se ejecuta en el host Proxmox"
[[ $EUID -eq 0 ]] || die "ejecuta como root"

PKG_FILE=""; MODE="create"; CT_UPDATE=""; USE_MAIN=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --file) PKG_FILE="$(realpath "$2")"; shift 2;;
    --main) USE_MAIN=1; shift;;
    -h|--help) sed -n '2,24p' "$0" 2>/dev/null | sed 's/^# \{0,1\}//' || echo "Ayuda: https://github.com/$REPO#install"; exit 0;;
    update) MODE="update"; CT_UPDATE="${2:-}"; shift 2 || shift;;
    --) shift;;
    *) die "opción desconocida: $1";;
  esac
done

WORK=$(mktemp -d); trap 'rm -rf "$WORK"' EXIT

# ------------------------------------------------------------- obtener y verificar el paquete
# Descarga un commit de main y lo reempaqueta como paquete de la app (mitallercito/…)
get_main(){
  [[ -z "$SIGNING_PUB" ]] || die "este instalador exige paquetes firmados; la rama main no va firmada"
  msg "Descargando lo último de la rama main de $REPO"
  local sha
  sha=$(curl -fsSL -H "Accept: application/vnd.github+json" "https://api.github.com/repos/$REPO/commits/main" \
        | python3 -c 'import json,sys;print(json.load(sys.stdin)["sha"])') || die "no se pudo consultar GitHub"
  curl -fsSL -o "$WORK/main.tgz" "https://codeload.github.com/$REPO/tar.gz/$sha" || die "no se pudo descargar main"
  mkdir -p "$WORK/u"
  python3 - "$WORK/main.tgz" "$WORK/u/payload.tar.gz" "$sha" <<'REPACK'
import io, sys, tarfile
src, dst, sha = sys.argv[1:4]
keep = ("app.py", "static", "requirements.txt", "VERSION", "REPO", "README.md", "LICENSE", "CHANGELOG.md",
        "install.sh", "updater", "signing.pub")
with tarfile.open(src, "r:gz") as s, tarfile.open(dst, "w:gz") as o:
    for m in s.getmembers():
        parts = m.name.split("/", 1)
        if len(parts) < 2 or not parts[1] or parts[1].split("/")[0] not in keep or not (m.isfile() or m.isdir()):
            continue
        f = s.extractfile(m) if m.isfile() else None
        m.name = "mitallercito/" + parts[1]
        o.addfile(m, f)
    ti = tarfile.TarInfo("mitallercito/COMMIT"); ti.size = len(sha); o.addfile(ti, io.BytesIO(sha.encode()))
REPACK
  ok "main@${sha:0:7} (versión $(tar xzOf "$WORK/u/payload.tar.gz" mitallercito/VERSION))"
  PAYLOAD="$WORK/u/payload.tar.gz"
}

get_package(){
  local pkg="$WORK/pkg.mtc"
  if [[ $USE_MAIN -eq 1 ]]; then get_main; return; fi
  if [[ -n "$PKG_FILE" ]]; then
    [[ -f "$PKG_FILE" ]] || die "no existe $PKG_FILE"
    cp "$PKG_FILE" "$pkg"; msg "Usando paquete local $(basename "$PKG_FILE")"
  else
    [[ "$REPO" != __* ]] || die "este script no tiene repositorio configurado; usa --file paquete.mtc"
    local api="https://api.github.com/repos/$REPO/releases/latest"
    [[ -n "${MT_VERSION:-}" ]] && api="https://api.github.com/repos/$REPO/releases/tags/v${MT_VERSION#v}"
    msg "Buscando la versión en GitHub ($REPO)"
    local url
    url=$(curl -fsSL -H "Accept: application/vnd.github+json" "$api" 2>/dev/null | python3 -c '
import json,sys
r=json.load(sys.stdin); a=[x for x in r.get("assets",[]) if x["name"].endswith(".mtc")]
print(a[0]["browser_download_url"] if a else "")' 2>/dev/null || true)
    if [[ -z "$url" ]]; then
      if [[ -z "$SIGNING_PUB" && -z "${MT_VERSION:-}" ]]; then
        msg "El repo aún no tiene versiones publicadas: uso la rama main"; get_main; return
      fi
      die "no encuentro una versión publicada con paquete .mtc"
    fi
    curl -fsSL -o "$pkg" "$url" || die "no se pudo descargar $url"
    ok "Descargado $(basename "$url")"
  fi
  mkdir -p "$WORK/u"
  # (listas a fichero: con pipefail, «tar | grep -q» falla por SIGPIPE)
  tar tf "$pkg" > "$WORK/outer.lst" 2>/dev/null || true
  if grep -qx 'payload.tar.gz' "$WORK/outer.lst"; then
    tar xf "$pkg" -C "$WORK/u" payload.tar.gz $(grep -x 'payload.sig' "$WORK/outer.lst" || true)
  else
    cp "$pkg" "$WORK/u/payload.tar.gz"   # paquete .tar.gz sin envoltorio
  fi
  if [[ -n "$SIGNING_PUB" ]]; then
    [[ -f "$WORK/u/payload.sig" ]] || die "el paquete NO está firmado y este instalador exige firma"
    printf '%s\n' "$SIGNING_PUB" > "$WORK/pub.pem"
    openssl pkeyutl -verify -pubin -inkey "$WORK/pub.pem" -rawin -in "$WORK/u/payload.tar.gz" -sigfile "$WORK/u/payload.sig" >/dev/null 2>&1 \
      || die "FIRMA NO VÁLIDA: el paquete está manipulado o no es del proyecto"
    ok "Firma verificada"
  else
    msg "Aviso: este instalador no tiene clave pública; no se comprueba la firma"
  fi
  tar tzf "$WORK/u/payload.tar.gz" > "$WORK/inner.lst" 2>/dev/null || die "el paquete está dañado"
  grep -qx 'mitallercito/app.py' "$WORK/inner.lst" || die "el paquete no es de MiTallercito"
  PAYLOAD="$WORK/u/payload.tar.gz"
}

push_and_install(){
  local ct="$1"
  pct push "$ct" "$PAYLOAD" /root/mitallercito.tar.gz
  pct exec "$ct" -- bash -c "cd /root && rm -rf mitallercito && tar xzf mitallercito.tar.gz && bash mitallercito/install.sh </dev/null"
}

# ------------------------------------------------------------- actualizar
if [[ "$MODE" == "update" ]]; then
  [[ -n "$CT_UPDATE" ]] || die "uso: ... update <CTID>"
  pct status "$CT_UPDATE" >/dev/null 2>&1 || die "no existe el CT $CT_UPDATE"
  # admite también instalaciones antiguas con el nombre «Tienda 3D» (install.sh las migra)
  pct exec "$CT_UPDATE" -- bash -c "test -f /etc/default/mitallercito || test -f /etc/default/tienda3d" \
    || die "el CT $CT_UPDATE no tiene MiTallercito instalada"
  get_package
  msg "Copia de la base de datos antes de actualizar"
  pct exec "$CT_UPDATE" -- bash -c "/usr/local/bin/mitallercito backup 2>/dev/null || /usr/local/bin/tienda3d backup" || true
  msg "Actualizando CT $CT_UPDATE"
  push_and_install "$CT_UPDATE"
  ok "Actualizado. Datos, usuarios y configuración se conservan."
  exit 0
fi

# ------------------------------------------------------------- crear
clear || true
echo -e "${YW}
  ╔══════════════════════════════════════╗
  ║   MiTallercito · instalador para LXC    ║
  ╚══════════════════════════════════════╝${CL}"

NEXT=$(pvesh get /cluster/nextid)
DEF_STORAGE=$(pvesm status -content rootdir 2>/dev/null | awk 'NR>1 && $3=="active"{print $1; exit}')
pvesm status -content rootdir 2>/dev/null | awk '$1=="local-lvm" && $3=="active"' | grep . >/dev/null && DEF_STORAGE=local-lvm
DEF_TPL=$(pvesm status -content vztmpl 2>/dev/null | awk 'NR>1 && $3=="active"{print $1; exit}')
DEF_TZ=$(timedatectl show -p Timezone --value 2>/dev/null || cat /etc/timezone 2>/dev/null || echo Europe/Madrid)
[[ "$DEF_TZ" =~ ^(Etc/)?UTC$ ]] && DEF_TZ=Europe/Madrid
INTERACTIVE=0; [[ -r /dev/tty ]] && [[ -z "${MT_NONINTERACTIVE:-}" ]] && INTERACTIVE=1

echo -e "\n  Almacenamientos para CT: $(pvesm status -content rootdir | awk 'NR>1{printf "%s ", $1}')"
BRS=""; for b in /sys/class/net/vmbr*; do [[ -e "$b" ]] && BRS+="${b##*/} "; done
echo -e "  Bridges: ${BRS}\n"

if [[ $INTERACTIVE -eq 1 ]]; then
  CTID=${CTID:-$(ask "ID del contenedor" "$NEXT")}
  HOSTNAME_CT=${HOSTNAME_CT:-$(ask "Hostname" "mitallercito")}
  STORAGE=${STORAGE:-$(ask "Almacenamiento del disco" "${DEF_STORAGE:-local-lvm}")}
  BRIDGE=${BRIDGE:-$(ask "Bridge de red" "vmbr0")}
  IPCFG=${IPCFG:-$(ask "IP (dhcp o 192.168.1.50/24,gw=192.168.1.1)" "dhcp")}
  VLAN=${VLAN:-$(ask "VLAN (vacío = ninguna)" "")}
  CORES=${CORES:-$(ask "Núcleos" "1")}
  RAM=${RAM:-$(ask "RAM (MB)" "512")}
  DISK=${DISK:-$(ask "Disco (GB)" "4")}
  TZ_CT=${TZ_CT:-$(ask "Zona horaria" "$DEF_TZ")}
fi
CTID=${CTID:-$NEXT}; HOSTNAME_CT=${HOSTNAME_CT:-mitallercito}; STORAGE=${STORAGE:-${DEF_STORAGE:-local-lvm}}
TPL_STORAGE=${TPL_STORAGE:-${DEF_TPL:-local}}; BRIDGE=${BRIDGE:-vmbr0}; IPCFG=${IPCFG:-dhcp}
CORES=${CORES:-1}; RAM=${RAM:-512}; DISK=${DISK:-4}; TZ_CT=${TZ_CT:-$DEF_TZ}; VLAN=${VLAN:-}; DEBIAN=${DEBIAN:-13}

pct status "$CTID" >/dev/null 2>&1 && die "el ID $CTID ya está en uso"
pvesm status -content rootdir | awk 'NR>1{print $1}' | grep -x "$STORAGE" >/dev/null || die "el almacenamiento '$STORAGE' no admite discos de CT"
[[ -d /sys/class/net/$BRIDGE ]] || die "no existe el bridge $BRIDGE"
[[ -f /usr/share/zoneinfo/$TZ_CT ]] || die "zona horaria no válida: $TZ_CT"
[[ "$IPCFG" == dhcp || "$IPCFG" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}/[0-9]{1,2}(,gw=([0-9]{1,3}\.){3}[0-9]{1,3})?$ ]] \
  || die "IP no válida: $IPCFG (usa dhcp o 192.168.1.50/24,gw=192.168.1.1)"
[[ -z "$VLAN" || "$VLAN" =~ ^[0-9]{1,4}$ ]] || die "VLAN no válida: $VLAN"
[[ "$CORES" =~ ^[0-9]+$ && "$RAM" =~ ^[0-9]+$ && "$DISK" =~ ^[0-9]+$ ]] || die "núcleos, RAM y disco tienen que ser números"
(( RAM >= 384 )) || die "con menos de 384 MB de RAM la instalación de dependencias puede fallar"

echo -e "\n  CT ${GN}$CTID${CL} · $HOSTNAME_CT · ${CORES} CPU · ${RAM} MB · ${DISK} GB en $STORAGE · $BRIDGE${VLAN:+ (VLAN $VLAN)} ($IPCFG) · Debian $DEBIAN · $TZ_CT"
if [[ $INTERACTIVE -eq 1 ]]; then read -rp "  ¿Crear? [S/n] " R </dev/tty; [[ "${R,,}" =~ ^(n|no)$ ]] && exit 0; fi

get_package

msg "Buscando plantilla Debian $DEBIAN"
pveam update >/dev/null 2>&1 || true
TPL=$(pveam available --section system | awk -v d="debian-${DEBIAN}-standard" '$2 ~ d {print $2}' | sort -V | tail -1)
if [[ -z "$TPL" && "$DEBIAN" == 13 ]]; then
  msg "Este Proxmox no ofrece Debian 13 (¿PVE 8 sin actualizar?): uso Debian 12"; DEBIAN=12
  TPL=$(pveam available --section system | awk '$2 ~ /debian-12-standard/ {print $2}' | sort -V | tail -1)
fi
[[ -n "$TPL" ]] || die "no encuentro la plantilla debian-${DEBIAN}-standard (¿hay Internet en el host?)"
if ! pveam list "$TPL_STORAGE" | grep "$TPL" >/dev/null; then
  msg "Descargando $TPL en $TPL_STORAGE"; pveam download "$TPL_STORAGE" "$TPL" >/dev/null
fi
ok "Plantilla $TPL"

if [[ "$IPCFG" == dhcp ]]; then NET="name=eth0,bridge=$BRIDGE,ip=dhcp"
else NET="name=eth0,bridge=$BRIDGE,ip=${IPCFG%%,*}"; [[ "$IPCFG" == *gw=* ]] && NET+=",gw=${IPCFG##*gw=}"; fi
[[ -n "$VLAN" ]] && NET+=",tag=$VLAN"

msg "Creando CT $CTID"
pct create "$CTID" "$TPL_STORAGE:vztmpl/$TPL" \
  --hostname "$HOSTNAME_CT" --cores "$CORES" --memory "$RAM" --swap 256 \
  --rootfs "$STORAGE:$DISK" --net0 "$NET" --unprivileged 1 --features nesting=1 \
  --onboot 1 --tags mitallercito --timezone "$TZ_CT" \
  --description "MiTallercito – https://github.com/$REPO" >/dev/null
# si algo falla a partir de aquí, no dejamos un CT a medias (salvo MT_KEEP=1 para investigarlo)
trap 'rc=$?; if [[ $rc -ne 0 && -z "${MT_KEEP:-}" ]]; then echo -e "${RD}  La instalación ha fallado: borro el CT $CTID (MT_KEEP=1 para conservarlo)${CL}"; pct stop "$CTID" >/dev/null 2>&1 || true; pct destroy "$CTID" --purge >/dev/null 2>&1 || true; fi; rm -rf "$WORK"' EXIT
pct start "$CTID"
ok "CT $CTID creado y arrancado"

msg "Esperando red en el contenedor"
for i in $(seq 1 45); do
  pct exec "$CTID" -- getent hosts deb.debian.org >/dev/null 2>&1 && break
  [[ $i -eq 45 ]] && die "el CT no tiene red/DNS. Revisa: pct config $CTID"
  sleep 2
done
ok "Red OK"

msg "Instalando la app (1-2 min)"
push_and_install "$CTID"

msg "Comprobando que la web responde"
for i in $(seq 1 20); do
  pct exec "$CTID" -- python3 -c 'import urllib.request;urllib.request.urlopen("http://127.0.0.1:8080/",timeout=3)' >/dev/null 2>&1 && break
  [[ $i -eq 20 ]] && die "la web no responde. Mira: pct exec $CTID -- journalctl -u mitallercito -n 50"
  sleep 2
done
ok "Web en marcha"

IP=$(pct exec "$CTID" -- hostname -I | awk '{print $1}')
TOKEN=$(pct exec "$CTID" -- /usr/local/bin/mitallercito setup-token 2>/dev/null || true)
echo -e "\n${GN}  ✔ MiTallercito lista${CL}"
echo -e "    Configúrala aquí (primer arranque):  ${BL}http://$IP:8080/#setup=$TOKEN${CL}"
echo    "    CT $CTID · consola con autologin · backups diarios en /var/lib/mitallercito/backups"
echo    "    Actualizaciones: desde la web (Sistema → subir el paquete .mtc o instalar la última versión)"
echo
