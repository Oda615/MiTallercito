#!/usr/bin/env python3
"""MiTallercito · puente para impresoras en otra red.

Se ejecuta en un equipo de la red donde están las impresoras (Raspberry Pi, NAS,
mini PC…). Solo hace conexiones HACIA FUERA hacia tu MiTallercito, así que no hace
falta VPN ni abrir puertos en esa red.

  · Pide a la tienda la lista de impresoras asignadas a este puente (IP y API key
    se configuran en la web: Ajustes → Impresoras → Conexión «Puente»).
  · Cada 10 s lee su estado de Moonraker y lo manda a la tienda; cada minuto, el historial.
  · Recoge los G-code que mandéis desde un pedido y los sube a la impresora.

Solo usa la biblioteca estándar de Python 3.9+.

Configuración (variables de entorno o /etc/mitallercito-bridge.env):
  MT_URL     https://tienda.midominio.com
  BRIDGE_TOKEN   mtb_…  (se crea en Ajustes → Puentes; se enseña una vez)
"""
import json
import os
import secrets
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

VERSION = "1.0.0"


def env_file(path="/etc/mitallercito-bridge.env"):
    try:
        for line in open(path):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    except OSError:
        pass


def log(*a):
    print(time.strftime("%Y-%m-%d %H:%M:%S"), *a, flush=True)


class Fail(Exception):
    pass


def http(url, method="GET", body=None, headers=None, timeout=10, raw=False):
    req = urllib.request.Request(url, data=body, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ssl.create_default_context()) as r:
            data = r.read()
            return data if raw else json.loads(data.decode() or "{}")
    except urllib.error.HTTPError as e:
        raise Fail(f"HTTP {e.code} en {urllib.parse.urlsplit(url).path}") from None
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise Fail(f"no responde {urllib.parse.urlsplit(url).netloc} ({getattr(e, 'reason', e)})") from None
    except ValueError:
        raise Fail("respuesta no válida") from None


# ---------------------------------------------------------------- tienda
class Shop:
    def __init__(self, url, token):
        self.url, self.h = url.rstrip("/"), {"Authorization": f"Bearer {token}", "X-Bridge-Version": VERSION,
                                             "Content-Type": "application/json", "User-Agent": "mitallercito-bridge"}

    def get(self, path, raw=False, timeout=15):
        return http(self.url + path, headers=self.h, raw=raw, timeout=timeout)

    def post(self, path, data):
        return http(self.url + path, "POST", json.dumps(data).encode(), self.h)


# ---------------------------------------------------------------- Moonraker
def moon(p, path, method="GET", params=None, body=None, headers=None, timeout=6):
    host = p["host"] if ":" in p["host"].strip("[]") else p["host"] + ":7125"
    url = f"http://{host}{path}" + (("?" + urllib.parse.urlencode(params)) if params else "")
    h = {"Accept": "application/json", **(headers or {})}
    if p.get("api_key"):
        h["X-Api-Key"] = p["api_key"]
    return http(url, method, body, h, timeout).get("result", {})


def status(p):
    q = moon(p, "/printer/objects/query", params={"print_stats": "", "display_status": "", "virtual_sdcard": "",
                                                   "extruder": "temperature,target", "heater_bed": "temperature,target"})
    st = q.get("status", {})
    ps, ds, vs = st.get("print_stats", {}), st.get("display_status", {}), st.get("virtual_sdcard", {})
    progress = ds.get("progress") or vs.get("progress") or 0
    out = {"state": ps.get("state", "desconocido"), "filename": ps.get("filename", ""), "progress": round(progress * 100, 1),
           "print_duration": ps.get("print_duration", 0), "filament_mm": ps.get("filament_used", 0),
           "extruder": st.get("extruder", {}), "bed": st.get("heater_bed", {}), "eta": None}
    if out["state"] == "printing" and out["filename"]:
        est = None
        try:
            est = moon(p, "/server/files/metadata", params={"filename": out["filename"]}, timeout=4).get("estimated_time")
        except Fail:
            pass
        remaining = max(0, est - out["print_duration"]) if est else (
            out["print_duration"] / progress - out["print_duration"] if progress > 0.01 else None)
        if remaining is not None:
            out["remaining"] = round(remaining)
            out["eta"] = time.strftime("%Y-%m-%dT%H:%M", time.localtime(time.time() + remaining))
    return out


def history(p):
    jobs = moon(p, "/server/history/list", params={"limit": 25, "order": "desc"}).get("jobs", [])
    out = []
    for j in jobs:
        md = j.get("metadata") or {}
        out.append({"job_id": str(j.get("job_id")), "filename": j.get("filename"), "status": j.get("status"),
                    "start_time": j.get("start_time"), "end_time": j.get("end_time"),
                    "print_duration": j.get("print_duration"), "total_duration": j.get("total_duration"),
                    "filament_mm": j.get("filament_used"), "filament_g": md.get("filament_weight_total"),
                    "estimated_time": md.get("estimated_time")})
    return out


def upload(p, filename, data, start):
    boundary = "----t3dbridge" + secrets.token_hex(12)
    safe = "".join(c for c in filename if c.isalnum() or c in "._- ")[:120] or "pieza.gcode"
    parts = [f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
             for k, v in (("root", "gcodes"), ("print", "true" if start else "false"))]
    parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{safe}"\r\n'
                 f'Content-Type: application/octet-stream\r\n\r\n'.encode())
    body = b"".join(parts) + data + f"\r\n--{boundary}--\r\n".encode()
    moon(p, "/server/files/upload", "POST", body=body,
         headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}, timeout=300)
    return safe


# ---------------------------------------------------------------- bucle
def run_once(shop, state):
    cfg = shop.get("/api/bridge/config")
    printers = {p["id"]: p for p in cfg.get("printers", [])}
    if state.get("names") != sorted(p["name"] for p in printers.values()):
        state["names"] = sorted(p["name"] for p in printers.values())
        log(f"conectado a «{cfg.get('bridge')}»; impresoras: {', '.join(state['names']) or '(ninguna asignada todavía)'}")
    want_hist = time.time() - state.get("hist_t", 0) > cfg.get("history_every", 60)
    report = []
    for p in printers.values():
        item = {"id": p["id"]}
        try:
            item["status"] = status(p)
            if want_hist:
                item["history"] = history(p)
        except Fail as e:
            item["error"] = str(e)
        report.append(item)
    shop.post("/api/bridge/report", {"printers": report})
    if want_hist:
        state["hist_t"] = time.time()
    for c in shop.get("/api/bridge/commands"):
        p = printers.get(c["printer_id"])
        try:
            if not p:
                raise Fail("impresora no asignada a este puente")
            if c["kind"] != "send":
                raise Fail(f"orden desconocida {c['kind']}")
            data = shop.get(f"/api/bridge/files/{c['id']}", raw=True, timeout=120)
            name = upload(p, c.get("filename") or "pieza.gcode", data, bool(c.get("start")))
            msg = f"{name} {'subido y arrancado' if c.get('start') else 'subido'} en {p['name']}"
            shop.post(f"/api/bridge/commands/{c['id']}", {"ok": True, "message": msg})
            log(msg)
        except Fail as e:
            shop.post(f"/api/bridge/commands/{c['id']}", {"ok": False, "message": str(e)})
            log("error con orden", c["id"], e)
    return cfg.get("poll", 10)


def main():
    env_file(os.environ.get("BRIDGE_ENV", "/etc/mitallercito-bridge.env"))
    url, token = os.environ.get("MT_URL", ""), os.environ.get("BRIDGE_TOKEN", "")
    if not url or not token:
        print(__doc__)
        sys.exit("Faltan MT_URL y BRIDGE_TOKEN")
    if url.startswith("http://") and not os.environ.get("BRIDGE_ALLOW_HTTP"):
        log("AVISO: MT_URL es http://; el token viaja sin cifrar. Usa https:// (o BRIDGE_ALLOW_HTTP=1 en tu LAN).")
    shop, state, wait = Shop(url, token), {}, 10
    log(f"mitallercito-bridge {VERSION} → {url}")
    once = "--once" in sys.argv
    while True:
        try:
            wait = run_once(shop, state)
        except Fail as e:
            log("sin conexión con la tienda:", e)
            wait = 30
        if once:
            break
        time.sleep(max(5, int(wait)))


if __name__ == "__main__":
    main()
