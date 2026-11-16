#!/usr/bin/env python3
"""Valida y desempaqueta un paquete de actualización de MiTallercito.

Lo usa el aplicador (root). Se instala en /usr/local/lib/mitallercito/ y NUNCA se
actualiza desde la web: solo con el instalador del host. Así un paquete subido
no puede cambiar las reglas con las que se le valida.

Formatos:
  .mtc     tar con  payload.tar.gz  +  payload.sig  (firma Ed25519 de payload.tar.gz)
  .tar(.gz) con  mitallercito/...  (sin firma; solo se acepta si no hay clave pública instalada
            o si MT_ALLOW_UNSIGNED=1)

Uso:  verify.py PAQUETE DIR_TRABAJO [CLAVE_PUBLICA]
Sale con código 0 e imprime JSON {"version", "signed", "dir"} si todo va bien.
"""
import json
import os
import subprocess
import sys
import tarfile

MAX_FILES = 500
MAX_BYTES = 20 * 1024 * 1024
ALLOWED_TOP = {"app.py", "static", "requirements.txt", "VERSION", "REPO", "README.md", "README.es.md",
               "LICENSE", "CHANGELOG.md", "install.sh", "updater", "signing.pub", "COMMIT"}
REQUIRED = ("mitallercito/app.py", "mitallercito/static/index.html", "mitallercito/requirements.txt", "mitallercito/VERSION")


class Reject(Exception):
    pass


def verify_signature(data_path, sig_path, pubkey):
    r = subprocess.run(["openssl", "pkeyutl", "-verify", "-pubin", "-inkey", pubkey, "-rawin",
                        "-in", data_path, "-sigfile", sig_path], capture_output=True, text=True)
    return r.returncode == 0 and "Success" in (r.stdout + r.stderr)


def unwrap(pkg, work, pubkey=None, allow_unsigned=False):
    """Devuelve (ruta_payload_tar_gz, firmado)."""
    require_sig = bool(pubkey and os.path.exists(pubkey)) and not allow_unsigned
    with tarfile.open(pkg, "r:*") as t:
        names = t.getnames()
        if "payload.tar.gz" in names:
            if set(names) - {"payload.tar.gz", "payload.sig"}:
                raise Reject("el paquete .mtc contiene ficheros no esperados")
            for n in ("payload.tar.gz", "payload.sig"):
                if n not in names:
                    continue
                m = t.getmember(n)
                if not m.isfile() or m.size > MAX_BYTES:
                    raise Reject(f"{n} no válido")
                with t.extractfile(m) as src, open(os.path.join(work, n), "wb") as dst:
                    dst.write(src.read())
            payload, sig = os.path.join(work, "payload.tar.gz"), os.path.join(work, "payload.sig")
            if os.path.exists(sig) and pubkey and os.path.exists(pubkey):
                if not verify_signature(payload, sig, pubkey):
                    raise Reject("FIRMA NO VÁLIDA: el paquete no es del proyecto o está manipulado")
                return payload, True
            if require_sig:
                raise Reject("el paquete no está firmado y esta instalación solo acepta paquetes firmados")
            return payload, False
    if require_sig:
        raise Reject("el paquete no está firmado (usa el .mtc de la página de versiones)")
    return pkg, False


def check_and_extract(payload, dst):
    with tarfile.open(payload, "r:*") as t:
        members = t.getmembers()
        if len(members) > MAX_FILES:
            raise Reject("demasiados ficheros")
        total = 0
        for m in members:
            n = m.name
            parts = n.split("/")
            if n.startswith("/") or ".." in parts or parts[0] != "mitallercito":
                raise Reject(f"ruta no permitida: {n}")
            if not (m.isfile() or m.isdir()):
                raise Reject(f"tipo de fichero no permitido (enlaces, dispositivos…): {n}")
            if len(parts) > 1 and parts[1] and parts[1] not in ALLOWED_TOP:
                raise Reject(f"fichero no esperado: {n}")
            total += m.size
        if total > MAX_BYTES:
            raise Reject("paquete demasiado grande")
        names = {m.name for m in members}
        for req in REQUIRED:
            if req not in names:
                raise Reject(f"falta {req}")
        os.makedirs(dst)
        for m in members:
            m.mode = 0o755 if m.isdir() else 0o644
            m.uid = m.gid = 0
            m.uname = m.gname = "root"
        if hasattr(tarfile, "data_filter"):
            t.extractall(dst, members=members, filter="data")
        else:
            t.extractall(dst, members=members)
    root = os.path.join(dst, "mitallercito")
    try:
        compile(open(os.path.join(root, "app.py"), encoding="utf-8").read(), "app.py", "exec")
    except SyntaxError as e:
        raise Reject(f"app.py tiene errores de sintaxis (línea {e.lineno})") from None
    version = open(os.path.join(root, "VERSION")).read().strip()
    if not version or len(version) > 30:
        raise Reject("VERSION no válida")
    return root, version


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2
    pkg, work = argv[1], argv[2]
    pubkey = argv[3] if len(argv) > 3 else None
    allow = os.environ.get("MT_ALLOW_UNSIGNED") == "1"
    try:
        payload, signed = unwrap(pkg, work, pubkey, allow)
        root, version = check_and_extract(payload, os.path.join(work, "x"))
    except (Reject, tarfile.TarError, OSError, UnicodeDecodeError) as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False))
        return 1
    print(json.dumps({"version": version, "signed": signed, "dir": root}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
