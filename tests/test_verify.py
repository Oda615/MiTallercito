"""El verificador de paquetes corre como root: tiene que rechazar todo lo raro."""
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "updater"))
import verify  # noqa: E402

needs_openssl = pytest.mark.skipif(not shutil.which("openssl"), reason="openssl no disponible")


def payload(tmp, extra=None, version="9.9.9"):
    files = {"mitallercito/app.py": b"print('hola')\n", "mitallercito/static/index.html": b"<html>",
             "mitallercito/requirements.txt": b"flask\n", "mitallercito/VERSION": version.encode()}
    files.update(extra or {})
    p = os.path.join(tmp, "payload.tar.gz")
    with tarfile.open(p, "w:gz") as t:
        for name, data in files.items():
            ti = tarfile.TarInfo(name)
            ti.size = len(data)
            t.addfile(ti, io.BytesIO(data))
    return p


def keypair(tmp):
    key, pub = os.path.join(tmp, "k.pem"), os.path.join(tmp, "pub.pem")
    subprocess.run(["openssl", "genpkey", "-algorithm", "ed25519", "-out", key], check=True, capture_output=True)
    subprocess.run(["openssl", "pkey", "-in", key, "-pubout", "-out", pub], check=True, capture_output=True)
    return key, pub


def t3d(tmp, pl, key=None, tamper=False):
    data = open(pl, "rb").read()
    out = os.path.join(tmp, "pkg.mtc")
    members = [("payload.tar.gz", data)]
    if key:
        sig = os.path.join(tmp, "sig")
        subprocess.run(["openssl", "pkeyutl", "-sign", "-inkey", key, "-rawin", "-in", pl, "-out", sig], check=True)
        members.append(("payload.sig", open(sig, "rb").read()))
    if tamper:
        members[0] = ("payload.tar.gz", data[:-10] + b"0123456789")
    with tarfile.open(out, "w") as t:
        for n, d in members:
            ti = tarfile.TarInfo(n)
            ti.size = len(d)
            t.addfile(ti, io.BytesIO(d))
    return out


def run(pkg, work, pub=None, allow=False):
    os.makedirs(work, exist_ok=True)
    try:
        pl, signed = verify.unwrap(pkg, work, pub, allow)
        _, v = verify.check_and_extract(pl, os.path.join(work, "x"))
        return True, v, signed
    except (verify.Reject, tarfile.TarError) as e:
        return False, str(e), None


@needs_openssl
def test_signed_ok_and_tampered_rejected(tmp_path):
    key, pub = keypair(str(tmp_path))
    ok, v, signed = run(t3d(str(tmp_path), payload(str(tmp_path)), key), str(tmp_path / "w1"), pub)
    assert ok and v == "9.9.9" and signed
    ok, msg, _ = run(t3d(str(tmp_path), payload(str(tmp_path)), key, tamper=True), str(tmp_path / "w2"), pub)
    assert not ok and "FIRMA" in msg


@needs_openssl
def test_other_key_rejected(tmp_path):
    key, _ = keypair(str(tmp_path))
    os.makedirs(tmp_path / "otra")
    _, pub2 = keypair(str(tmp_path / "otra"))
    ok, msg, _ = run(t3d(str(tmp_path), payload(str(tmp_path)), key), str(tmp_path / "w"), pub2)
    assert not ok and "FIRMA" in msg


@needs_openssl
def test_unsigned_rejected_when_key_installed(tmp_path):
    _, pub = keypair(str(tmp_path))
    ok, msg, _ = run(t3d(str(tmp_path), payload(str(tmp_path))), str(tmp_path / "w"), pub)
    assert not ok and "firmad" in msg
    ok, msg, _ = run(payload(str(tmp_path)), str(tmp_path / "w2"), pub)
    assert not ok


def test_unsigned_ok_without_key(tmp_path):
    ok, v, signed = run(payload(str(tmp_path)), str(tmp_path / "w"))
    assert ok and signed is False


@pytest.mark.parametrize("bad", [
    {"etc/cron.d/x": b"pwn"},                     # fuera de mitallercito/
    {"mitallercito/../../etc/x": b"pwn"},             # path traversal
    {"mitallercito/hook.sh": b"rm -rf /"},            # fichero no esperado
    {"mitallercito/app.py": b"def (:\n"},             # sintaxis rota
])
def test_bad_payloads(tmp_path, bad):
    ok, msg, _ = run(payload(str(tmp_path), bad), str(tmp_path / "w"))
    assert not ok, msg


def test_symlink_rejected(tmp_path):
    p = payload(str(tmp_path))
    with tarfile.open(p, "r:gz") as t:
        members = [(m, t.extractfile(m).read() if m.isfile() else None) for m in t.getmembers()]
    out = str(tmp_path / "link.tar.gz")
    with tarfile.open(out, "w:gz") as t:
        for m, d in members:
            t.addfile(m, io.BytesIO(d))
        ti = tarfile.TarInfo("mitallercito/static/x")
        ti.type, ti.linkname = tarfile.SYMTYPE, "/etc/shadow"
        t.addfile(ti)
    ok, msg, _ = run(out, str(tmp_path / "w"))
    assert not ok and "enlaces" in msg


def test_cli_json(tmp_path):
    r = subprocess.run([sys.executable, os.path.join(ROOT, "updater", "verify.py"), payload(str(tmp_path)), str(tmp_path / "w")],
                       capture_output=True, text=True)
    os.makedirs(tmp_path / "w", exist_ok=True)
    assert r.returncode in (0, 1)
    json.loads(r.stdout)
