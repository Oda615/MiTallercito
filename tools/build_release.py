#!/usr/bin/env python3
"""Construye el paquete de una versión: dist/mitallercito-<versión>.mtc

  .mtc = tar con payload.tar.gz (la app, en mitallercito/) + payload.sig (firma Ed25519).

La firma se hace con la clave privada indicada en MT_SIGNING_KEY (ruta a un PEM)
o en ~/.config/mitallercito/signing.key. Sin clave, el paquete sale SIN firmar (sirve para
pruebas o para quien no use firmas). La clave privada nunca va al repositorio.

Uso:  python3 tools/build_release.py [--unsigned]
"""
import io
import os
import subprocess
import sys
import tarfile
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILES = ["app.py", "static", "requirements.txt", "VERSION", "REPO", "README.md", "LICENSE",
         "CHANGELOG.md", "install.sh", "updater", "signing.pub"]


def _filter(ti):
    ti.uid = ti.gid = 0
    ti.uname = ti.gname = "root"
    ti.mtime = 0
    if "__pycache__" in ti.name or ti.name.endswith(".pyc"):
        return None
    return ti


def build_payload():
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as t:
        for f in FILES:
            p = os.path.join(ROOT, f)
            if os.path.exists(p):
                t.add(p, arcname=f"mitallercito/{f}", filter=_filter)
    return buf.getvalue()


def sign(data, key):
    with tempfile.TemporaryDirectory() as d:
        src, sig = os.path.join(d, "p"), os.path.join(d, "s")
        open(src, "wb").write(data)
        subprocess.run(["openssl", "pkeyutl", "-sign", "-inkey", key, "-rawin", "-in", src, "-out", sig], check=True)
        return open(sig, "rb").read()


def main():
    version = open(os.path.join(ROOT, "VERSION")).read().strip()
    key = os.environ.get("MT_SIGNING_KEY") or os.path.expanduser("~/.config/mitallercito/signing.key")
    unsigned = "--unsigned" in sys.argv or not os.path.exists(key)
    payload = build_payload()
    os.makedirs(os.path.join(ROOT, "dist"), exist_ok=True)
    out = os.path.join(ROOT, "dist", f"mitallercito-{version}.mtc")
    with tarfile.open(out, "w") as t:
        for name, data in [("payload.tar.gz", payload)] + ([] if unsigned else [("payload.sig", sign(payload, key))]):
            ti = tarfile.TarInfo(name)
            ti.size, ti.mode = len(data), 0o644
            t.addfile(ti, io.BytesIO(data))
    print(out, "(SIN FIRMAR)" if unsigned else "(firmado)")


if __name__ == "__main__":
    main()
