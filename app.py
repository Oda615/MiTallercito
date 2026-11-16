"""MiTallercito - pedidos, calculadora de precios y contabilidad para tiendas de impresión 3D.
https://github.com/Oda615/MiTallercito  ·  Licencia MIT

App Flask + SQLite pensada para correr en un LXC. Todo el estado vive en
DATA_DIR/mitallercito.db (haz backup de ese fichero y listo).
"""
import csv
import io
import json
import math
import os
import secrets
import sqlite3
import sys
from datetime import date, datetime, timedelta
from functools import wraps

from flask import Flask, g, jsonify, request, send_from_directory, session, Response
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.environ.get("MT_DATA_DIR", os.path.join(BASE_DIR, "data"))
DB_PATH = os.path.join(DATA_DIR, "mitallercito.db")
# instalaciones anteriores (nombre «Tienda 3D»): renombrar la base de datos
if not os.path.exists(DB_PATH) and os.path.exists(os.path.join(DATA_DIR, "tienda3d.db")):
    try:
        os.rename(os.path.join(DATA_DIR, "tienda3d.db"), DB_PATH)
    except OSError:
        pass

app = Flask(__name__, static_folder="static", static_url_path="/static")


def _secret_key():
    env = os.environ.get("MT_SECRET")
    if env:
        return env
    os.makedirs(DATA_DIR, exist_ok=True)
    p = os.path.join(DATA_DIR, ".secret")
    if not os.path.exists(p):
        with open(p, "w") as f:
            f.write(secrets.token_hex(32))
        os.chmod(p, 0o600)
    return open(p).read().strip()


app.secret_key = _secret_key()
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax",
                  PERMANENT_SESSION_LIFETIME=60 * 60 * 24 * 30)

# Detrás de Nginx Proxy Manager: confiar en X-Forwarded-* de N saltos de proxy.
# 1 = solo NPM (nube gris en Cloudflare). 2 = Cloudflare proxied (nube naranja) + NPM.
from werkzeug.middleware.proxy_fix import ProxyFix  # noqa: E402
_hops = int(os.environ.get("MT_PROXY_HOPS", "1"))
if _hops > 0:
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=_hops, x_proto=_hops, x_host=_hops)
# Cookie "Secure" solo cuando se entra por HTTPS (sigue funcionando por http://IP:8080 en la LAN)
app.session_interface.get_cookie_secure = lambda _app: request.is_secure

LOGIN_MAX_FAILS = int(os.environ.get("MT_LOGIN_MAX_FAILS", "5"))
LOGIN_WINDOW_MIN = int(os.environ.get("MT_LOGIN_WINDOW_MIN", "15"))


@app.after_request
def security_headers(resp):
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("X-Frame-Options", "DENY")
    resp.headers.setdefault("Referrer-Policy", "same-origin")
    if request.is_secure:
        resp.headers.setdefault("Strict-Transport-Security", "max-age=31536000")
    return resp

ORDER_STATUSES = ["presupuesto", "recibido", "programado", "imprimiendo", "postprocesado", "listo", "entregado", "cancelado"]
OPEN_STATUSES = ("recibido", "programado", "imprimiendo", "postprocesado", "listo")
# horas máximas razonables en cada estado antes de avisar por Telegram (editable en Ajustes)
DEFAULT_LIMITS = {"presupuesto": 168, "recibido": 24, "programado": 72, "imprimiendo": 48, "postprocesado": 48, "listo": 72}

DEFAULT_SETTINGS = {
    "kwh_price": 0.18,          # €/kWh
    "prep_rate": 15.0,          # €/h preparación (laminar, montar placa...)
    "post_rate": 15.0,          # €/h postprocesado (soportes, lijado, pintura)
    "waste_pct": 10.0,          # % merma de material (purgas, fallos)
    "fail_pct": 5.0,            # % recargo por riesgo de impresión fallida
    "margin_pct": 30.0,         # % beneficio sobre coste
    "vat_pct": 21.0,
    "sale_type": "B2C",         # B2C: precio con IVA incluido / B2B: IVA aparte
    "apply_vat": True,
    "min_price": 3.0,           # precio mínimo por pedido/línea
    "rounding": "0.50",         # none | 0.99 | 0.50 | 1.00
    "commission_pct": 0.0,      # comisión plataforma (%)
    "commission_fixed": 0.0,    # comisión fija (€)
    "people": [],               # se rellena en el asistente de primer arranque
    "channels": ["Directo", "Wallapop", "Instagram", "Etsy", "Feria"],
    "expense_categories": ["Filamento", "Resina", "Repuestos", "Embalaje", "Envíos",
                           "Electricidad", "Herramientas", "Impresoras", "Comisiones", "Otros"],
    # --- Marca / personalización
    "shop_name": "MiTallercito",
    "shop_tagline": "Impresión 3D a medida",
    "accent_color": "#3fae6a",
    "logo": "",                 # fichero en DATA_DIR/media
    "favicon": "",
    "business_name": "", "business_nif": "", "business_address": "",
    "business_email": "", "business_phone": "", "business_web": "",
    "doc_footer": "Gracias por tu compra.",
    "quote_validity_days": 15,
    # --- Tienda online (futuro)
    "store_enabled": False,
    # --- Actualizaciones: "releases" (versiones publicadas y firmadas) | "main" (último commit de la rama main)
    "update_channel": "releases",
    "language": "es",           # es | en
    # --- Telegram
    "telegram_enabled": False, "telegram_token": "", "telegram_chat_id": "",
    "status_limits_h": DEFAULT_LIMITS, "remind_hours": 24, "notify_new": True, "notify_due": True,
    "notify_low_stock": True, "notify_maint": True, "public_url": "",
    "manyfold_url": "", "manyfold_client_id": "", "manyfold_client_secret": "",
    "forecast_lead_days": 7, "forecast_window_days": 60, "forecast_quotes": False,
}
SECRET_SETTINGS = ("telegram_token", "manyfold_client_secret")
PUBLIC_SETTINGS = ["shop_name", "shop_tagline", "accent_color", "logo", "favicon", "language"]
MEDIA_DIR = os.path.join(DATA_DIR, "media")
ALLOWED_IMG = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
               "webp": "image/webp", "ico": "image/x-icon", "gif": "image/gif"}
ORDER_SOURCES = ["interno", "web", "puesto", "stock"]
ANON_CLIENT = "Venta anónima"
STOCK_CLIENT = "Para stock"
PAY_METHODS = ["efectivo", "tarjeta", "bizum", "transferencia", "otro"]
PRINTER_CONNS = ("", "moonraker", "bridge", "octoprint", "prusalink")

SCHEMA = """
CREATE TABLE IF NOT EXISTS users(
  id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL, pw_hash TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS printers(
  id INTEGER PRIMARY KEY, name TEXT NOT NULL, watts REAL DEFAULT 150,
  cost REAL DEFAULT 0, hours_day REAL DEFAULT 8, amort_months REAL DEFAULT 24,
  maint_month REAL DEFAULT 5, active INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS materials(
  id INTEGER PRIMARY KEY, name TEXT NOT NULL, kind TEXT DEFAULT 'PLA', color TEXT DEFAULT '',
  price REAL DEFAULT 20, qty REAL DEFAULT 1000, unit TEXT DEFAULT 'g',
  stock REAL DEFAULT 0, active INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS orders(
  id INTEGER PRIMARY KEY, created TEXT NOT NULL, client TEXT NOT NULL, contact TEXT DEFAULT '',
  channel TEXT DEFAULT '', status TEXT DEFAULT 'recibido', due_date TEXT DEFAULT '',
  assigned TEXT DEFAULT '', notes TEXT DEFAULT '', paid INTEGER DEFAULT 0,
  paid_to TEXT DEFAULT '', paid_date TEXT DEFAULT '', shipping REAL DEFAULT 0,
  discount REAL DEFAULT 0);
CREATE TABLE IF NOT EXISTS order_items(
  id INTEGER PRIMARY KEY, order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  description TEXT NOT NULL, qty INTEGER DEFAULT 1, unit_price REAL DEFAULT 0,
  unit_cost REAL DEFAULT 0, calc_json TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS movements(
  id INTEGER PRIMARY KEY, date TEXT NOT NULL, kind TEXT NOT NULL CHECK(kind IN ('ingreso','gasto')),
  category TEXT DEFAULT '', concept TEXT DEFAULT '', amount REAL NOT NULL,
  person TEXT DEFAULT '', order_id INTEGER REFERENCES orders(id) ON DELETE SET NULL);
CREATE TABLE IF NOT EXISTS login_fails(ip TEXT NOT NULL, ts REAL NOT NULL);
CREATE TABLE IF NOT EXISTS spools(
  id INTEGER PRIMARY KEY, material_id INTEGER REFERENCES materials(id) ON DELETE SET NULL,
  brand TEXT DEFAULT '', color_name TEXT DEFAULT '', color_hex TEXT DEFAULT '', net_g REAL DEFAULT 1000,
  tare_g REAL, price REAL, location TEXT DEFAULT '', status TEXT DEFAULT 'cerrada', notes TEXT DEFAULT '',
  created TEXT NOT NULL, finished TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS spool_tares(
  id INTEGER PRIMARY KEY, brand TEXT NOT NULL, kind TEXT NOT NULL, tare_g REAL NOT NULL, samples INTEGER DEFAULT 1,
  updated TEXT, UNIQUE(brand, kind));
CREATE TABLE IF NOT EXISTS order_status_log(
  id INTEGER PRIMARY KEY, order_id INTEGER REFERENCES orders(id) ON DELETE CASCADE, status TEXT, at TEXT, user TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS notifications(key TEXT PRIMARY KEY, sent_at REAL, count INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS print_failures(
  id INTEGER PRIMARY KEY, order_id INTEGER REFERENCES orders(id) ON DELETE CASCADE, description TEXT, pct REAL,
  hours REAL, kwh REAL, grams_json TEXT, material_cost REAL, other_cost REAL, cost REAL, cause TEXT DEFAULT '',
  printer TEXT DEFAULT '', created TEXT, user TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS kit_items(
  id INTEGER PRIMARY KEY, kit_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
  product_id INTEGER REFERENCES products(id) ON DELETE CASCADE, qty INTEGER DEFAULT 1, notes TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS kit_parts(
  id INTEGER PRIMARY KEY, kit_id INTEGER REFERENCES products(id) ON DELETE CASCADE, name TEXT NOT NULL,
  qty REAL DEFAULT 1, unit_cost REAL DEFAULT 0, notes TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS bridges(
  id INTEGER PRIMARY KEY, name TEXT NOT NULL, token_hash TEXT NOT NULL UNIQUE, created TEXT NOT NULL,
  last_seen REAL, last_ip TEXT DEFAULT '', version TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS printer_cache(
  printer_id INTEGER PRIMARY KEY REFERENCES printers(id) ON DELETE CASCADE,
  status_json TEXT, error TEXT, history_json TEXT, updated REAL);
CREATE TABLE IF NOT EXISTS bridge_cmds(
  id INTEGER PRIMARY KEY, bridge_id INTEGER NOT NULL REFERENCES bridges(id) ON DELETE CASCADE,
  printer_id INTEGER NOT NULL, kind TEXT NOT NULL, file_id INTEGER, start INTEGER DEFAULT 0, order_id INTEGER,
  state TEXT DEFAULT 'pending', result TEXT DEFAULT '', created REAL, updated REAL, requested_by TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS print_jobs(
  id INTEGER PRIMARY KEY, printer_id INTEGER REFERENCES printers(id) ON DELETE SET NULL,
  order_id INTEGER REFERENCES orders(id) ON DELETE CASCADE, job_id TEXT NOT NULL, filename TEXT DEFAULT '',
  status TEXT DEFAULT '', start_time REAL, end_time REAL, print_duration REAL DEFAULT 0, total_duration REAL DEFAULT 0,
  filament_mm REAL DEFAULT 0, filament_g REAL, estimated_time REAL, UNIQUE(printer_id, job_id));
CREATE TABLE IF NOT EXISTS files(
  id INTEGER PRIMARY KEY, order_id INTEGER REFERENCES orders(id) ON DELETE SET NULL,
  product_id INTEGER REFERENCES products(id) ON DELETE SET NULL,
  stored TEXT NOT NULL, name TEXT NOT NULL, size INTEGER DEFAULT 0, sha256 TEXT DEFAULT '',
  uploaded TEXT NOT NULL, uploaded_by TEXT DEFAULT '', note TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS stock_moves(
  id INTEGER PRIMARY KEY, date TEXT NOT NULL, material_id INTEGER NOT NULL REFERENCES materials(id) ON DELETE CASCADE,
  delta REAL NOT NULL, reason TEXT NOT NULL, note TEXT DEFAULT '', person TEXT DEFAULT '',
  order_id INTEGER REFERENCES orders(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS maint_tasks(
  id INTEGER PRIMARY KEY, printer_id INTEGER NOT NULL REFERENCES printers(id) ON DELETE CASCADE, name TEXT NOT NULL,
  every_h REAL, every_prints INTEGER, every_days INTEGER, notes TEXT DEFAULT '', source TEXT DEFAULT '',
  last_done TEXT, sort INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS maint_log(
  id INTEGER PRIMARY KEY, printer_id INTEGER REFERENCES printers(id) ON DELETE CASCADE, task_id INTEGER,
  task_name TEXT DEFAULT '', kind TEXT NOT NULL, at TEXT NOT NULL, hours REAL DEFAULT 0, prints INTEGER DEFAULT 0,
  note TEXT DEFAULT '', user TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS printer_jobs(
  printer_id INTEGER NOT NULL REFERENCES printers(id) ON DELETE CASCADE, job_id TEXT NOT NULL, end_time REAL,
  hours REAL DEFAULT 0, prints INTEGER DEFAULT 1, status TEXT DEFAULT '', PRIMARY KEY(printer_id, job_id));
CREATE TABLE IF NOT EXISTS clients(
  id INTEGER PRIMARY KEY, name TEXT NOT NULL, phone TEXT DEFAULT '', email TEXT DEFAULT '', address TEXT DEFAULT '',
  notes TEXT DEFAULT '', created TEXT);
CREATE TABLE IF NOT EXISTS events(
  id INTEGER PRIMARY KEY, name TEXT NOT NULL, date TEXT, place TEXT DEFAULT '', stand_cost REAL DEFAULT 0,
  cash_start REAL DEFAULT 0, cash_end REAL, status TEXT DEFAULT 'abierto', notes TEXT DEFAULT '', created TEXT);
CREATE TABLE IF NOT EXISTS event_stock(
  event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE, product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  qty INTEGER DEFAULT 0, PRIMARY KEY(event_id, product_id));
CREATE TABLE IF NOT EXISTS product_variants(
  id INTEGER PRIMARY KEY, product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE, name TEXT NOT NULL,
  color_hex TEXT DEFAULT '', price REAL, stock INTEGER, material_id INTEGER REFERENCES materials(id) ON DELETE SET NULL,
  sort INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS offers(
  id INTEGER PRIMARY KEY, name TEXT NOT NULL, kind TEXT NOT NULL DEFAULT 'pack', qty INTEGER DEFAULT 2, price REAL,
  pct REAL, product_id INTEGER REFERENCES products(id) ON DELETE CASCADE, category TEXT DEFAULT '',
  applies TEXT DEFAULT 'todo', active INTEGER DEFAULT 1, created TEXT);
CREATE TABLE IF NOT EXISTS material_prices(
  id INTEGER PRIMARY KEY, material_id INTEGER NOT NULL REFERENCES materials(id) ON DELETE CASCADE, date TEXT NOT NULL,
  supplier TEXT DEFAULT '', brand TEXT DEFAULT '', units REAL DEFAULT 1, unit_qty REAL DEFAULT 1000, total REAL NOT NULL,
  per_kg REAL, source TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS shopping(
  id INTEGER PRIMARY KEY, material_id INTEGER REFERENCES materials(id) ON DELETE CASCADE, text TEXT DEFAULT '',
  units REAL DEFAULT 1, supplier TEXT DEFAULT '', est_price REAL, note TEXT DEFAULT '', status TEXT DEFAULT 'pendiente',
  created TEXT, bought_at TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS recurring(
  id INTEGER PRIMARY KEY, concept TEXT NOT NULL, category TEXT DEFAULT '', amount REAL NOT NULL, person TEXT DEFAULT '',
  every TEXT DEFAULT 'mensual', day INTEGER DEFAULT 1, start TEXT NOT NULL, until TEXT DEFAULT '', active INTEGER DEFAULT 1,
  created TEXT);
CREATE TABLE IF NOT EXISTS locations(
  id INTEGER PRIMARY KEY, name TEXT NOT NULL, parent_id INTEGER REFERENCES locations(id) ON DELETE SET NULL,
  kind TEXT DEFAULT 'caja', notes TEXT DEFAULT '', created TEXT);
CREATE TABLE IF NOT EXISTS components(
  id INTEGER PRIMARY KEY, name TEXT NOT NULL, category TEXT DEFAULT '', unit TEXT DEFAULT 'ud', pack_qty REAL DEFAULT 1,
  pack_price REAL, unit_cost REAL DEFAULT 0, min_stock REAL DEFAULT 0, location_id INTEGER REFERENCES locations(id) ON DELETE SET NULL,
  supplier TEXT DEFAULT '', url TEXT DEFAULT '', notes TEXT DEFAULT '', active INTEGER DEFAULT 1, created TEXT);
CREATE TABLE IF NOT EXISTS component_moves(
  id INTEGER PRIMARY KEY, component_id INTEGER NOT NULL REFERENCES components(id) ON DELETE CASCADE, date TEXT NOT NULL,
  delta REAL NOT NULL, reason TEXT NOT NULL, note TEXT DEFAULT '', person TEXT DEFAULT '',
  order_id INTEGER REFERENCES orders(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS products(
  id INTEGER PRIMARY KEY, name TEXT NOT NULL, calc_json TEXT NOT NULL,
  unit_price REAL DEFAULT 0, unit_cost REAL DEFAULT 0, notes TEXT DEFAULT '');
"""


# ---------------------------------------------------------------- DB helpers
def get_db():
    if "db" not in g:
        os.makedirs(DATA_DIR, exist_ok=True)
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys=ON")
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


MIGRATIONS = [
    ("order_items", "calc_result", "TEXT DEFAULT ''"),
    ("order_items", "product_id", "INTEGER"),
    ("orders", "source", "TEXT DEFAULT 'interno'"),
    ("orders", "email", "TEXT DEFAULT ''"),
    ("orders", "address", "TEXT DEFAULT ''"),
    ("orders", "public_token", "TEXT DEFAULT ''"),
    ("products", "sku", "TEXT DEFAULT ''"),
    ("products", "category", "TEXT DEFAULT ''"),
    ("products", "description", "TEXT DEFAULT ''"),
    ("products", "image", "TEXT DEFAULT ''"),
    ("products", "public", "INTEGER DEFAULT 0"),
    ("products", "public_price", "REAL"),
    ("products", "stock", "INTEGER"),          # NULL = bajo pedido
    ("products", "lead_days", "INTEGER DEFAULT 3"),
    ("users", "role", "TEXT DEFAULT 'user'"),
    ("order_items", "print_info", "TEXT DEFAULT ''"),
    ("products", "print_info", "TEXT DEFAULT ''"),
    ("printers", "conn", "TEXT DEFAULT ''"),        # '' = sin conexión | 'moonraker'
    ("printers", "host", "TEXT DEFAULT ''"),        # IP o nombre[:puerto], p.ej. 192.168.1.40 o u1.local:7125
    ("printers", "api_key", "TEXT DEFAULT ''"),
    ("printers", "bridge_id", "INTEGER"),
    ("orders", "status_since", "TEXT"),
    ("stock_moves", "spool_id", "INTEGER"),
    ("stock_moves", "fail_id", "INTEGER"),
    ("products", "kind", "TEXT DEFAULT 'pieza'"),     # pieza | conjunto
    ("products", "instructions", "TEXT DEFAULT ''"),
    ("materials", "track_stock", "INTEGER DEFAULT 0"),
    ("materials", "low_stock", "REAL DEFAULT 200"),
    ("printers", "model", "TEXT DEFAULT ''"),             # perfil de mantenimiento
    ("printers", "hours_source", "TEXT DEFAULT 'auto'"),  # auto | app
    ("print_failures", "printer_id", "INTEGER"),
    ("orders", "client_id", "INTEGER"),
    ("orders", "event_id", "INTEGER"),
    ("orders", "pay_method", "TEXT DEFAULT ''"),
    ("orders", "stock_done", "INTEGER DEFAULT 0"),
    ("movements", "event_id", "INTEGER"),
    ("order_items", "variant_id", "INTEGER"),
    ("order_items", "offer_id", "INTEGER"),
    ("products", "manyfold_id", "TEXT DEFAULT ''"),
    ("spools", "supplier", "TEXT DEFAULT ''"),
    ("spools", "location_id", "INTEGER"),
    ("products", "location_id", "INTEGER"),
    ("products", "min_stock", "INTEGER DEFAULT 0"),
    ("kit_parts", "component_id", "INTEGER"),
    ("shopping", "component_id", "INTEGER"),
    ("movements", "recurring_id", "INTEGER"),
    ("movements", "period", "TEXT DEFAULT ''"),
]


def migrate(db):
    for table, col, decl in MIGRATIONS:
        cols = [r[1] for r in db.execute(f"PRAGMA table_info({table})")]
        if col not in cols:
            db.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")


def init_db():
    db = get_db()
    db.executescript(SCHEMA)
    migrate(db)
    os.makedirs(MEDIA_DIR, exist_ok=True)
    db.execute("UPDATE OR IGNORE users SET username=lower(trim(username))")
    db.execute("UPDATE orders SET status='recibido' WHERE status='pendiente'")          # estado antiguo
    db.execute("UPDATE orders SET status_since=created WHERE status_since IS NULL OR status_since=''")
    # Al estrenar roles: si nadie es admin, los usuarios que ya existían son los dueños → admin
    if not db.execute("SELECT 1 FROM users WHERE role='admin'").fetchone():
        db.execute("UPDATE users SET role='admin'")
    for k, v in DEFAULT_SETTINGS.items():
        db.execute("INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)", (k, json.dumps(v)))
    # 0.7.0: fichas de cliente a partir de los nombres de los pedidos que ya había
    if not db.execute("SELECT 1 FROM settings WHERE key='clients_migrated'").fetchone():
        ids = {}
        for r in db.execute("SELECT id, client, contact, email, address, created FROM orders ORDER BY id").fetchall():
            name = (r["client"] or "").strip()
            if not name or name in (ANON_CLIENT, STOCK_CLIENT):
                continue
            k = name.lower()
            if k not in ids:
                ids[k] = db.execute("INSERT INTO clients(name,phone,email,address,created) VALUES(?,?,?,?,?)",
                                    (name, r["contact"] or "", r["email"] or "", r["address"] or "", r["created"])).lastrowid
            db.execute("UPDATE orders SET client_id=? WHERE id=?", (ids[k], r["id"]))
        db.execute("INSERT INTO settings(key,value) VALUES('clients_migrated','true')")
    # 0.6.0: el color por defecto pasa de naranja a verde (solo si nadie lo había cambiado)
    db.execute("UPDATE settings SET value=? WHERE key='accent_color' AND value=?", (json.dumps("#3fae6a"), json.dumps("#e8572a")))
    db.commit()
    if not db.execute("SELECT 1 FROM users").fetchone():
        tok = setup_token(create=True)
        app.logger.warning("Primer arranque: abre /#setup=%s para configurar la tienda", tok)


def rows(q, args=()):
    return [dict(r) for r in get_db().execute(q, args).fetchall()]


def one(q, args=()):
    r = get_db().execute(q, args).fetchone()
    return dict(r) if r else None


def load_settings():
    return {r["key"]: json.loads(r["value"]) for r in get_db().execute("SELECT * FROM settings")}


def public_settings():
    """Ajustes para el navegador: los secretos van enmascarados."""
    st = load_settings()
    for k in SECRET_SETTINGS:
        st[k] = KEY_MASK if st.get(k) else ""
    return st


def num(v, default=0.0):
    try:
        if v in (None, ""):
            return default
        return float(str(v).replace(",", "."))
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------- auth
def current_user():
    """Se lee de la BD en cada petición: si borras o degradas a alguien, efecto inmediato."""
    if not session.get("user"):
        return None
    return one("SELECT id, username, role FROM users WHERE username=?", (session["user"],))


def login_required(fn):
    @wraps(fn)
    def wrapper(*a, **kw):
        if not current_user():
            session.clear()
            return jsonify(error="no autenticado"), 401
        return fn(*a, **kw)
    return wrapper


def is_admin():
    u = current_user()
    return bool(u and u["role"] == "admin")


def admin_required(fn):
    @wraps(fn)
    def wrapper(*a, **kw):
        u = current_user()
        if not u:
            session.clear()
            return jsonify(error="no autenticado"), 401
        if u["role"] != "admin":
            return jsonify(error="solo un administrador puede hacer esto"), 403
        return fn(*a, **kw)
    return wrapper


@app.post("/api/login")
def login():
    import time
    db, ip, now = get_db(), request.remote_addr or "?", time.time()
    db.execute("DELETE FROM login_fails WHERE ts<?", (now - LOGIN_WINDOW_MIN * 60,))
    fails = db.execute("SELECT COUNT(*) FROM login_fails WHERE ip=?", (ip,)).fetchone()[0]
    if fails >= LOGIN_MAX_FAILS:
        db.commit()
        app.logger.warning("login bloqueado para %s", ip)
        return jsonify(error=f"demasiados intentos, espera {LOGIN_WINDOW_MIN} min"), 429
    d = request.get_json(force=True, silent=True) or {}
    uname = str(d.get("username", "")).strip().lower()
    u = one("SELECT * FROM users WHERE username=?", (uname,))
    if not u or not check_password_hash(u["pw_hash"], d.get("password", "")):
        db.execute("INSERT INTO login_fails(ip,ts) VALUES(?,?)", (ip, now))
        db.commit()
        app.logger.warning("login fallido para %r desde %s", d.get("username"), ip)
        return jsonify(error="usuario o contraseña incorrectos"), 401
    db.execute("DELETE FROM login_fails WHERE ip=?", (ip,))
    db.commit()
    session.clear()
    session.permanent = True
    session["user"] = u["username"]
    return jsonify(user=u["username"], role=u["role"])


@app.post("/api/logout")
def logout():
    session.clear()
    return jsonify(ok=True)


@app.get("/api/me")
def me():
    u = current_user()
    return jsonify(user=u["username"] if u else None, role=u["role"] if u else None)


MIN_PW = 8


@app.post("/api/me/password")
@login_required
def change_my_password():
    d = request.get_json(force=True) or {}
    u = one("SELECT * FROM users WHERE username=?", (session["user"],))
    if not check_password_hash(u["pw_hash"], d.get("current", "")):
        return jsonify(error="la contraseña actual no es correcta"), 403
    if len(d.get("new", "")) < MIN_PW:
        return jsonify(error=f"mínimo {MIN_PW} caracteres"), 400
    get_db().execute("UPDATE users SET pw_hash=? WHERE id=?", (generate_password_hash(d["new"]), u["id"]))
    get_db().commit()
    return jsonify(ok=True)


@app.get("/api/users")
@admin_required
def list_users():
    return jsonify(rows("SELECT username, role FROM users ORDER BY username"))


@app.post("/api/users")
@admin_required
def create_user():
    d = request.get_json(force=True) or {}
    name = str(d.get("username", "")).strip().lower()
    if not name or not name.replace(".", "").replace("-", "").replace("_", "").isalnum():
        return jsonify(error="nombre no válido (letras, números, . - _)"), 400
    if len(d.get("password", "")) < MIN_PW:
        return jsonify(error=f"contraseña de mínimo {MIN_PW} caracteres"), 400
    if one("SELECT 1 AS x FROM users WHERE username=?", (name,)):
        return jsonify(error="ya existe"), 400
    role = "admin" if d.get("role") == "admin" else "user"
    get_db().execute("INSERT INTO users(username,pw_hash,role) VALUES(?,?,?)",
                     (name, generate_password_hash(d["password"]), role))
    get_db().commit()
    return jsonify(username=name, role=role), 201


def _admins():
    return one("SELECT COUNT(*) AS n FROM users WHERE role='admin'")["n"]


@app.put("/api/users/<name>")
@admin_required
def update_user(name):
    d = request.get_json(force=True) or {}
    u = one("SELECT * FROM users WHERE username=?", (name,))
    if not u:
        return jsonify(error="no existe"), 404
    db = get_db()
    if d.get("password"):
        if len(d["password"]) < MIN_PW:
            return jsonify(error=f"contraseña de mínimo {MIN_PW} caracteres"), 400
        db.execute("UPDATE users SET pw_hash=? WHERE id=?", (generate_password_hash(d["password"]), u["id"]))
    if d.get("role") in ("admin", "user") and d["role"] != u["role"]:
        if u["role"] == "admin" and _admins() <= 1:
            return jsonify(error="tiene que quedar al menos un administrador"), 400
        db.execute("UPDATE users SET role=? WHERE id=?", (d["role"], u["id"]))
    db.commit()
    return jsonify(ok=True)


@app.delete("/api/users/<name>")
@admin_required
def delete_user(name):
    if name == session.get("user"):
        return jsonify(error="no puedes borrarte a ti mismo"), 400
    u = one("SELECT * FROM users WHERE username=?", (name,))
    if not u:
        return jsonify(error="no existe"), 404
    if u["role"] == "admin" and _admins() <= 1:
        return jsonify(error="tiene que quedar al menos un administrador"), 400
    get_db().execute("DELETE FROM users WHERE id=?", (u["id"],))
    get_db().commit()
    return jsonify(ok=True)


# ---------------------------------------------------------------- primer arranque
SETUP_FILE = os.path.join(DATA_DIR, "setup_token")


def setup_token(create=False):
    """Token de un solo uso para el asistente. Solo existe mientras no haya usuarios.
    Evita que cualquiera en la red se adelante y se haga admin de una instalación recién hecha."""
    try:
        return open(SETUP_FILE).read().strip()
    except OSError:
        if not create:
            return None
    tok = secrets.token_urlsafe(18)
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(SETUP_FILE, "w") as f:
        f.write(tok)
    os.chmod(SETUP_FILE, 0o600)
    return tok


def setup_needed():
    return not one("SELECT 1 AS x FROM users")


@app.get("/api/setup")
def setup_status():
    return jsonify(needed=setup_needed())


@app.post("/api/setup")
def do_setup():
    if not setup_needed():
        return jsonify(error="la tienda ya está configurada"), 409
    d = request.get_json(force=True) or {}
    tok = setup_token()
    if not tok or not secrets.compare_digest(str(d.get("token", "")), tok):
        return jsonify(error="código de instalación no válido (míralo en la salida del instalador o con «mitallercito setup-token»)"), 403
    adm = d.get("admin") or {}
    name = str(adm.get("username", "")).strip().lower()
    if not name or not name.replace(".", "").replace("-", "").replace("_", "").isalnum():
        return jsonify(error="nombre de usuario no válido"), 400
    if len(adm.get("password", "")) < MIN_PW:
        return jsonify(error=f"contraseña de mínimo {MIN_PW} caracteres"), 400
    db = get_db()
    db.execute("INSERT INTO users(username,pw_hash,role) VALUES(?,?,?)",
               (name, generate_password_hash(adm["password"]), "admin"))
    st = {}
    if str(d.get("shop_name", "")).strip():
        st["shop_name"] = str(d["shop_name"]).strip()[:80]
    people = [str(p).strip()[:40] for p in (d.get("people") or []) if str(p).strip()]
    st["people"] = people or [name]
    for k in ("kwh_price", "margin_pct", "vat_pct", "prep_rate", "post_rate", "min_price"):
        if d.get(k) not in (None, ""):
            st[k] = num(d[k])
    if d.get("sale_type") in ("B2C", "B2B"):
        st["sale_type"] = d["sale_type"]
    if d.get("language") in ("es", "en"):
        st["language"] = d["language"]
    if "apply_vat" in d:
        st["apply_vat"] = bool(d["apply_vat"])
    for k, v in st.items():
        db.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)", (k, json.dumps(v)))
    for p in (d.get("printers") or [])[:20]:
        if str(p.get("name", "")).strip():
            db.execute("INSERT INTO printers(name,watts,cost,hours_day,amort_months,maint_month) VALUES(?,?,?,?,?,?)",
                       (str(p["name"]).strip()[:60], num(p.get("watts"), 150), num(p.get("cost")),
                        num(p.get("hours_day"), 8), num(p.get("amort_months"), 24), num(p.get("maint_month"), 5)))
    for m in (d.get("materials") or [])[:50]:
        if str(m.get("name", "")).strip():
            db.execute("INSERT INTO materials(name,kind,color,price,qty,unit) VALUES(?,?,?,?,?,?)",
                       (str(m["name"]).strip()[:60], str(m.get("kind", ""))[:20], str(m.get("color", ""))[:30],
                        num(m.get("price"), 20), num(m.get("qty"), 1000), "ml" if m.get("unit") == "ml" else "g"))
    db.commit()
    try:
        os.remove(SETUP_FILE)
    except OSError:
        pass
    session.clear()
    session.permanent = True
    session["user"] = name
    app.logger.warning("tienda configurada; administrador: %s", name)
    return jsonify(ok=True, user=name, role="admin")


# ---------------------------------------------------------------- calculadora
def round_price(p, mode):
    if mode == "0.99":
        return math.ceil(p) - 0.01 if p > 0 else 0
    if mode == "0.50":
        return math.ceil(p * 2) / 2
    if mode == "1.00":
        return float(math.ceil(p))
    return round(p, 2)


def calculate(d, s=None):
    """Calcula coste y PVP de una placa/trabajo.

    d = {
      printer_id, hours, minutes, units (piezas que salen del trabajo),
      materials: [{material_id, amount}] (g o ml según material),
      prep_min, post_min, extras: [{concept, amount}],
      overrides opcionales: margin_pct, waste_pct, fail_pct, commission_pct,
        commission_fixed, sale_type, apply_vat, rounding, min_price,
      include_electricity, include_labor, include_machine (bool, por defecto True)
    }
    """
    s = dict(s or load_settings())
    for k in ("margin_pct", "waste_pct", "fail_pct", "commission_pct", "commission_fixed",
              "min_price", "vat_pct"):
        if d.get(k) not in (None, ""):
            s[k] = num(d[k])
    for k in ("sale_type", "rounding"):
        if d.get(k):
            s[k] = d[k]
    if "apply_vat" in d:
        s["apply_vat"] = bool(d["apply_vat"])

    inc_el = d.get("include_electricity", True)
    inc_lab = d.get("include_labor", True)
    inc_mac = d.get("include_machine", True)

    hours = num(d.get("hours")) + num(d.get("minutes")) / 60.0
    units = max(1, int(num(d.get("units"), 1)))

    printer = one("SELECT * FROM printers WHERE id=?", (d.get("printer_id"),)) if d.get("printer_id") else None

    # Material
    mat_lines, mat_cost = [], 0.0
    for m in d.get("materials", []) or []:
        mm = one("SELECT * FROM materials WHERE id=?", (m.get("material_id"),))
        amt = num(m.get("amount"))
        if not mm or amt <= 0:
            continue
        per_unit = mm["price"] / mm["qty"] if mm["qty"] else 0
        c = amt * per_unit
        mat_cost += c
        line = {"material_id": mm["id"], "name": mm["name"], "amount": amt, "unit": mm["unit"], "cost": round(c, 4)}
        if str(m.get("spool_id") or "").isdigit():
            line["spool_id"] = int(m["spool_id"])
        mat_lines.append(line)
    # Modo "laminador": el coste de material viene directo del slicer (€),
    # que ya incluye purgas/torre de limpieza → no se aplica merma.
    if d.get("material_mode") == "direct":
        direct = num(d.get("material_cost"))
        if mat_lines:   # hay gramos (p.ej. importados del G-code): se reparte el coste del laminador
            tot_amt = sum(m["amount"] for m in mat_lines) or 1
            for m in mat_lines:
                m["cost"] = round(direct * m["amount"] / tot_amt, 4)
        else:
            mat_lines = [{"name": "Coste del laminador", "amount": None, "unit": "€", "cost": round(direct, 4)}]
        mat_cost = direct
        waste = 0.0
    else:
        waste = mat_cost * s["waste_pct"] / 100.0

    # Electricidad
    elec = (printer["watts"] / 1000.0) * hours * s["kwh_price"] if (printer and inc_el) else 0.0

    # Amortización + mantenimiento (por hora de máquina)
    amort = maint = 0.0
    if printer and inc_mac:
        hd = printer["hours_day"] or 1
        life_h = (printer["amort_months"] or 1) * 30 * hd
        amort = printer["cost"] / life_h * hours if life_h else 0
        maint = printer["maint_month"] / (30 * hd) * hours

    # Mano de obra
    prep = num(d.get("prep_min")) / 60.0 * s["prep_rate"] if inc_lab else 0.0
    post = num(d.get("post_min")) / 60.0 * s["post_rate"] if inc_lab else 0.0

    extras = [{"concept": e.get("concept", ""), "amount": num(e.get("amount"))}
              for e in (d.get("extras") or []) if num(e.get("amount"))]
    extras_total = sum(e["amount"] for e in extras)

    base_cost = mat_cost + waste + elec + amort + maint + prep + post + extras_total
    fail = (mat_cost + waste + elec + amort + maint) * s["fail_pct"] / 100.0
    cost = base_cost + fail

    margin = cost * s["margin_pct"] / 100.0
    net = cost + margin  # lo que queremos que nos quede (sin IVA)

    # Comisión plataforma: subimos el precio para que tras la comisión quede "net"
    cp = s["commission_pct"] / 100.0
    pre_vat = (net + s["commission_fixed"]) / (1 - cp) if cp < 1 else net
    commission = pre_vat - net

    vat_rate = s["vat_pct"] / 100.0 if s.get("apply_vat") else 0.0

    def finalize(total_pre_vat):
        # "raw" = precio que sale de coste + margen + comisión (+ IVA), antes de mínimo y redondeo,
        # para poder avisar cuando el mínimo o el redondeo "tapan" un cambio de margen.
        if s["sale_type"] == "B2C":
            raw = total_pre_vat * (1 + vat_rate)
            gross = round_price(max(raw, s["min_price"]), s["rounding"])
            return {"price": gross, "price_ex_vat": round(gross / (1 + vat_rate), 2),
                    "vat": round(gross - gross / (1 + vat_rate), 2), "raw": round(raw, 2),
                    "min_applied": raw < s["min_price"], "min_price": s["min_price"]}
        p = round_price(max(total_pre_vat, s["min_price"]), s["rounding"])
        return {"price": p, "price_ex_vat": p, "vat": round(p * vat_rate, 2),
                "price_inc_vat": round(p * (1 + vat_rate), 2), "raw": round(total_pre_vat, 2),
                "min_applied": total_pre_vat < s["min_price"], "min_price": s["min_price"]}

    unit_pre_vat = pre_vat / units
    per_unit = finalize(unit_pre_vat)
    batch = finalize(pre_vat)

    r4 = lambda x: round(x, 4)
    breakdown = {
        "material": r4(mat_cost), "merma": r4(waste), "electricidad": r4(elec),
        "amortizacion": r4(amort), "mantenimiento": r4(maint), "preparacion": r4(prep),
        "postprocesado": r4(post), "extras": r4(extras_total), "riesgo_fallo": r4(fail),
    }
    return {
        "hours": round(hours, 3), "units": units,
        "printer": printer["name"] if printer else None,
        "materials": mat_lines, "extras": extras, "breakdown": breakdown,
        "cost": round(cost, 2), "cost_unit": round(cost / units, 2),
        "margin": round(margin, 2), "commission": round(commission, 2),
        "sale_type": s["sale_type"], "vat_pct": s["vat_pct"] if s.get("apply_vat") else 0,
        "unit": per_unit, "batch": batch,
        "kwh": round((printer["watts"] / 1000.0) * hours, 4) if printer else 0,
        "printer_id": printer["id"] if printer else None,
        "prep_min": num(d.get("prep_min")) if inc_lab else 0,
        "post_min": num(d.get("post_min")) if inc_lab else 0,
        "material_mode": d.get("material_mode") or "grams",
        "commission_fixed": s["commission_fixed"], "commission_pct": s["commission_pct"],
        # Beneficio real por unidad con el precio ya redondeado
        "profit_unit": round(per_unit["price_ex_vat"] * (1 - cp) - s["commission_fixed"] / units - cost / units, 2),
    }


@app.post("/api/calc")
@login_required
def api_calc():
    return jsonify(calculate(request.get_json(force=True) or {}))


# ---------------------------------------------------------------- settings / catálogos
@app.get("/api/settings")
@login_required
def get_settings():
    return jsonify(public_settings())


@app.put("/api/settings")
@admin_required
def put_settings():
    d = request.get_json(force=True) or {}
    db = get_db()
    for k, v in d.items():
        if k in SECRET_SETTINGS and v == KEY_MASK:
            continue
        if k in DEFAULT_SETTINGS and k not in ("logo", "favicon"):
            db.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)", (k, json.dumps(v)))
    db.commit()
    return jsonify(public_settings())


CRUD = {
    "printers": ["name", "watts", "cost", "hours_day", "amort_months", "maint_month", "active", "conn", "host", "api_key",
                 "bridge_id", "model", "hours_source"],
    "materials": ["name", "kind", "color", "price", "qty", "unit", "active", "track_stock", "low_stock"],
    "products": ["name", "calc_json", "unit_price", "unit_cost", "notes", "sku", "category",
                 "description", "image", "public", "public_price", "stock", "lead_days", "print_info", "kind",
                 "instructions", "manyfold_id", "min_stock", "location_id"],
}


ADMIN_TABLES = {"printers", "materials"}


KEY_MASK = "••••••••"


def _clean(table, d):
    out = {}
    if table == "printers":
        if d.get("api_key") == KEY_MASK:
            d = {k: v for k, v in d.items() if k != "api_key"}
        if "host" in d:
            d["host"] = _norm_host(d["host"])
        if "conn" in d and d["conn"] not in PRINTER_CONNS:
            d["conn"] = ""
        if "bridge_id" in d:
            d["bridge_id"] = int(d["bridge_id"]) if str(d["bridge_id"] or "").isdigit() else None
    for f in CRUD[table]:
        if f in d:
            v = d[f]
            if f in ("calc_json", "print_info") and not isinstance(v, str):
                v = json.dumps(v)
            out[f] = v
    return out


@app.get("/api/<table>")
@login_required
def list_table(table):
    if table not in CRUD:
        return jsonify(error="no existe"), 404
    if table == "materials":
        return jsonify(materials_with_stock())
    if table == "printers":
        ps = rows("SELECT * FROM printers ORDER BY name")
        for p in ps:
            p["api_key"] = KEY_MASK if p.get("api_key") else ""
        return jsonify(ps)
    out = rows(f"SELECT * FROM {table} ORDER BY name")
    if table == "products":
        var = {}
        for v in rows("SELECT * FROM product_variants ORDER BY sort, id"):
            var.setdefault(v["product_id"], []).append(v)
        for pr in out:
            pr["variants"] = var.get(pr["id"], [])
    return jsonify(out)


@app.post("/api/products/recalculate")
@login_required
def recalc_products():
    out, db = [], get_db()
    for p in rows("SELECT * FROM products"):
        try:
            if p.get("kind") == "conjunto":
                continue
            r = calc_product(p)
        except (ValueError, TypeError):
            continue
        if not r["hours"] and not r["materials"]:
            continue
        db.execute("UPDATE products SET unit_price=?, unit_cost=? WHERE id=?", (r["unit"]["price"], r["cost_unit"], p["id"]))
        out.append({"id": p["id"], "name": p["name"], "old_price": p["unit_price"], "new_price": r["unit"]["price"]})
    db.commit()
    return jsonify(out)


@app.post("/api/<table>")
@login_required
def create_row(table):
    if table not in CRUD:
        return jsonify(error="no existe"), 404
    if table in ADMIN_TABLES and not is_admin():
        return jsonify(error="solo un administrador puede hacer esto"), 403
    d = _clean(table, request.get_json(force=True) or {})
    if not d.get("name"):
        return jsonify(error="falta el nombre"), 400
    cols = ",".join(d)
    cur = get_db().execute(f"INSERT INTO {table}({cols}) VALUES({','.join('?' * len(d))})", list(d.values()))
    get_db().commit()
    return jsonify(one(f"SELECT * FROM {table} WHERE id=?", (cur.lastrowid,))), 201


@app.put("/api/<table>/<int:rid>")
@login_required
def update_row(table, rid):
    if table not in CRUD:
        return jsonify(error="no existe"), 404
    if table in ADMIN_TABLES and not is_admin():
        return jsonify(error="solo un administrador puede hacer esto"), 403
    d = _clean(table, request.get_json(force=True) or {})
    if d:
        get_db().execute(f"UPDATE {table} SET {','.join(k + '=?' for k in d)} WHERE id=?", [*d.values(), rid])
        get_db().commit()
    return jsonify(one(f"SELECT * FROM {table} WHERE id=?", (rid,)))


@app.delete("/api/<table>/<int:rid>")
@login_required
def delete_row(table, rid):
    if table not in CRUD:
        return jsonify(error="no existe"), 404
    if table in ADMIN_TABLES and not is_admin():
        return jsonify(error="solo un administrador puede hacer esto"), 403
    get_db().execute(f"DELETE FROM {table} WHERE id=?", (rid,))
    get_db().commit()
    return jsonify(ok=True)


# ---------------------------------------------------------------- pedidos
ORDER_FIELDS = ["client", "contact", "channel", "status", "due_date", "assigned", "notes",
                "shipping", "discount", "source", "email", "address", "client_id", "event_id", "pay_method"]


def _resolve_client(vals, create=True):
    """Enlaza el pedido con su ficha de cliente (la crea si es nuevo). Las ventas anónimas no llevan ficha."""
    name = (vals.get("client") or "").strip()
    cid = vals.get("client_id")
    if cid not in (None, ""):
        c = one("SELECT * FROM clients WHERE id=?", (cid,))
        if c:
            vals["client_id"], vals["client"] = c["id"], c["name"]
            return vals
    vals["client_id"] = None
    if not name or name in (ANON_CLIENT, STOCK_CLIENT):
        return vals
    c = one("SELECT * FROM clients WHERE lower(trim(name))=lower(?)", (name,))
    if c:
        vals["client_id"] = c["id"]
        db = get_db()
        for f_o, f_c in (("contact", "phone"), ("email", "email"), ("address", "address")):
            if vals.get(f_o) and not c[f_c]:
                db.execute(f"UPDATE clients SET {f_c}=? WHERE id=?", (vals[f_o], c["id"]))
    elif create:
        vals["client_id"] = get_db().execute(
            "INSERT INTO clients(name,phone,email,address,created) VALUES(?,?,?,?,?)",
            (name, vals.get("contact") or "", vals.get("email") or "", vals.get("address") or "",
             datetime.now().isoformat(timespec="seconds"))).lastrowid
    return vals


def order_full(oid):
    o = one("SELECT * FROM orders WHERE id=?", (oid,))
    if not o:
        return None
    o["items"] = rows("SELECT * FROM order_items WHERE order_id=? ORDER BY id", (oid,))
    o["files"] = rows("SELECT id,name,size,uploaded,uploaded_by,note FROM files WHERE order_id=? ORDER BY id", (oid,))
    o["failures"] = rows("SELECT * FROM print_failures WHERE order_id=? ORDER BY id", (oid,))
    o["status_log"] = rows("SELECT status, at, user FROM order_status_log WHERE order_id=? ORDER BY id", (oid,))
    if o.get("status_since"):
        try:
            o["hours_in_status"] = round((datetime.now() - datetime.fromisoformat(o["status_since"])).total_seconds() / 3600, 1)
        except ValueError:
            o["hours_in_status"] = None
    sub = sum(i["qty"] * i["unit_price"] for i in o["items"])
    cost = sum(i["qty"] * i["unit_cost"] for i in o["items"])
    o["subtotal"] = round(sub, 2)
    o["total"] = round(sub + (o["shipping"] or 0) - (o["discount"] or 0), 2)
    o["cost"] = round(cost, 2)
    o["failure_cost"] = round(sum(f["cost"] or 0 for f in o["failures"]), 2)
    o["profit"] = round(o["total"] - (o["shipping"] or 0) - cost - o["failure_cost"], 2)
    return o


STOCK_STATES = ("imprimiendo", "postprocesado", "listo", "entregado")


def _sync_stock(oid):
    """Descuenta del stock el material de un pedido mientras esté imprimiéndose o hecho.
    Se recalcula entero cada vez: si editas líneas o lo cancelas, el stock se corrige solo."""
    db = get_db()
    _sync_components(oid)
    db.execute("DELETE FROM stock_moves WHERE order_id=? AND reason='pedido'", (oid,))
    o = one("SELECT status FROM orders WHERE id=?", (oid,))
    if not o or o["status"] not in STOCK_STATES:
        return
    by_name = {m["name"]: m["id"] for m in rows("SELECT id,name FROM materials")}
    used = {}
    for it in rows("SELECT qty, calc_result FROM order_items WHERE order_id=?", (oid,)):
        try:
            cr = json.loads(it["calc_result"]) if it["calc_result"] else None
        except ValueError:
            cr = None
        if not cr:
            continue
        f = (it["qty"] or 0) / (cr.get("units") or 1)
        for ml in cr.get("materials", []):
            mid = ml.get("material_id") or by_name.get(ml.get("name"))
            if mid and ml.get("amount"):
                key = (mid, ml.get("spool_id"))
                used[key] = used.get(key, 0) + ml["amount"] * f
    today = date.today().isoformat()
    for (mid, sid), amt in used.items():
        sid = sid or pick_spool(mid)
        db.execute("INSERT INTO stock_moves(date,material_id,delta,reason,note,order_id,spool_id) VALUES(?,?,?,?,?,?,?)",
                   (today, mid, -round(amt, 2), "pedido", f"Pedido #{oid}", oid, sid))


def spool_remaining(sid):
    sp = one("SELECT net_g FROM spools WHERE id=?", (sid,))
    if not sp:
        return 0
    d = one("SELECT COALESCE(SUM(delta),0) AS d FROM stock_moves WHERE spool_id=?", (sid,))["d"]
    return round((sp["net_g"] or 0) + d, 1)


def pick_spool(mid):
    """Bobina de la que sale el material si no se eligió una: la abierta más antigua; si no hay, la cerrada más antigua."""
    if not mid:
        return None
    sp = one("""SELECT id FROM spools WHERE material_id=? AND status!='gastada'
                ORDER BY CASE status WHEN 'abierta' THEN 0 ELSE 1 END, id LIMIT 1""", (mid,))
    if not sp:
        return None
    get_db().execute("UPDATE spools SET status='abierta' WHERE id=? AND status='cerrada'", (sp["id"],))
    return sp["id"]


def materials_with_stock():
    ms = rows("SELECT * FROM materials ORDER BY name")
    lvl = {r["material_id"]: r["s"] for r in rows(
        "SELECT material_id, SUM(delta) AS s FROM stock_moves WHERE spool_id IS NULL GROUP BY material_id")}
    by_spools = {}
    for sp in rows("SELECT id, material_id FROM spools WHERE status!='gastada'"):
        by_spools.setdefault(sp["material_id"], []).append(spool_remaining(sp["id"]))
    for m in ms:
        if m["id"] in by_spools:
            m["track_stock"] = 1
            m["spools"] = len(by_spools[m["id"]])
            m["stock_level"] = round(sum(max(0, x) for x in by_spools[m["id"]]), 1)
        else:
            m["spools"] = 0
            m["stock_level"] = round(lvl.get(m["id"], 0) or 0, 1) if m["track_stock"] else None
        m["stock_low"] = bool(m["track_stock"] and m["stock_level"] <= (m["low_stock"] or 0))
    return ms


@app.post("/api/materials/<int:mid>/stock")
@login_required
def stock_entry(mid):
    """mode=compra: entran N envases (opcional: apunta el gasto y actualiza el precio)
       mode=ajuste: fijas lo que queda de verdad (pesando la bobina, p.ej.)"""
    m = one("SELECT * FROM materials WHERE id=?", (mid,))
    if not m:
        return jsonify(error="no existe"), 404
    d = request.get_json(force=True) or {}
    db, today = get_db(), date.today().isoformat()
    cur = next(x for x in materials_with_stock() if x["id"] == mid)["stock_level"] or 0
    if d.get("mode") == "ajuste":
        target = num(d.get("amount"), None)
        if target is None or target < 0:
            return jsonify(error="cantidad no válida"), 400
        delta, note = target - (cur if m["track_stock"] else 0), "Ajuste de inventario"
        if not m["track_stock"]:   # al empezar a controlar, borramos descuentos antiguos
            db.execute("DELETE FROM stock_moves WHERE material_id=? AND reason!='pedido'", (mid,))
            delta = target - sum(r["delta"] for r in rows(
                "SELECT delta FROM stock_moves WHERE material_id=?", (mid,)))
    else:
        packs = num(d.get("packs"), 0)
        if packs <= 0:
            return jsonify(error="número de envases no válido"), 400
        delta, note = packs * m["qty"], f"Compra {packs:g} × {m['qty']:g} {m['unit']}"
        paid = num(d.get("paid"), 0)
        if paid > 0:
            db.execute("UPDATE materials SET price=? WHERE id=?", (round(paid / packs, 2), mid))
            _record_price(mid, packs, m["qty"], paid, str(d.get("supplier", "")).strip()[:60], "", "compra")
            cat = "Resina" if m["unit"] == "ml" else "Filamento"
            db.execute("INSERT INTO movements(date,kind,category,concept,amount,person) VALUES(?,?,?,?,?,?)",
                       (today, "gasto", cat, f"{m['name']} – {packs:g} envase(s)", paid, d.get("person", "")))
        if not m["track_stock"]:
            # Empezamos a controlar con lo que entra ahora; lo descontado antes no cuenta
            db.execute("DELETE FROM stock_moves WHERE material_id=? AND reason!='pedido'", (mid,))
            delta -= sum(r["delta"] for r in rows("SELECT delta FROM stock_moves WHERE material_id=?", (mid,)))
    db.execute("UPDATE materials SET track_stock=1 WHERE id=?", (mid,))
    db.execute("INSERT INTO stock_moves(date,material_id,delta,reason,note,person) VALUES(?,?,?,?,?,?)",
               (today, mid, round(delta, 2), d.get("mode") or "compra", note, d.get("person", "")))
    db.commit()
    return jsonify(next(x for x in materials_with_stock() if x["id"] == mid))


@app.get("/api/materials/<int:mid>/moves")
@login_required
def stock_moves(mid):
    return jsonify(rows("SELECT * FROM stock_moves WHERE material_id=? ORDER BY id DESC LIMIT 50", (mid,)))


def _sync_payment(oid):
    """Si el pedido está cobrado, mantiene un movimiento de ingreso enlazado."""
    db = get_db()
    o = order_full(oid)
    db.execute("DELETE FROM movements WHERE order_id=? AND kind='ingreso' AND category='Ventas'", (oid,))
    if o and o["paid"] and o["status"] != "cancelado":
        db.execute(
            "INSERT INTO movements(date,kind,category,concept,amount,person,order_id) VALUES(?,?,?,?,?,?,?)",
            (o["paid_date"] or date.today().isoformat(), "ingreso", "Ventas",
             f"Pedido #{oid} - {o['client']}" + (f" ({o['pay_method']})" if o.get("pay_method") else ""),
             o["total"], o["paid_to"], oid))
        if o.get("event_id"):
            db.execute("UPDATE movements SET event_id=? WHERE order_id=? AND category='Ventas'", (o["event_id"], oid))
    db.commit()


@app.get("/api/orders")
@login_required
def list_orders():
    q = "SELECT id FROM orders"
    args = []
    conds = []
    for k in ("status", "source"):
        if request.args.get(k):
            conds.append(f"{k}=?")
            args.append(request.args[k])
    if conds:
        q += " WHERE " + " AND ".join(conds)
    q += " ORDER BY CASE status WHEN 'entregado' THEN 2 WHEN 'cancelado' THEN 3 ELSE 1 END, " \
         "COALESCE(NULLIF(due_date,''),'9999'), id DESC"
    return jsonify([order_full(r["id"]) for r in rows(q, args)])


@app.get("/api/orders/<int:oid>")
@login_required
def get_order(oid):
    o = order_full(oid)
    return (jsonify(o), 200) if o else (jsonify(error="no existe"), 404)


def _save_items(oid, items):
    """Guarda las líneas. Cada línea con cálculo lleva una "foto" (calc_result) del
    desglose en el momento de crearla, para que el extracto mensual no cambie si
    luego cambias el precio de la luz o del filamento."""
    db = get_db()
    db.execute("DELETE FROM order_items WHERE order_id=?", (oid,))
    for it in items or []:
        if not it.get("description"):
            continue
        cj = it.get("calc_json", "")
        if cj and not isinstance(cj, str):
            cj = json.dumps(cj)
        cr = it.get("calc_result") or ""
        if not cr and cj:
            try:
                cr = calculate(json.loads(cj))
            except Exception:  # noqa: BLE001
                cr = ""
        if cr and not isinstance(cr, str):
            cr = json.dumps(cr)
        pi = it.get("print_info") or ""
        if pi and not isinstance(pi, str):
            pi = json.dumps(pi, ensure_ascii=False)
        db.execute(
            "INSERT INTO order_items(order_id,description,qty,unit_price,unit_cost,calc_json,calc_result,product_id,print_info,"
            "variant_id,offer_id) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (oid, it["description"], int(num(it.get("qty"), 1)), num(it.get("unit_price")),
             num(it.get("unit_cost")), cj, cr, it.get("product_id"), pi, it.get("variant_id") or None, it.get("offer_id") or None))


@app.post("/api/orders")
@login_required
def create_order():
    d = request.get_json(force=True) or {}
    if not d.get("client"):
        return jsonify(error="falta el cliente"), 400
    db = get_db()
    vals = {k: d.get(k, "") for k in ORDER_FIELDS}
    vals["status"] = vals["status"] if vals["status"] in ORDER_STATUSES else "recibido"
    vals["source"] = vals["source"] if vals["source"] in ORDER_SOURCES else "interno"
    vals["shipping"] = num(vals["shipping"])
    vals["discount"] = num(vals["discount"])
    vals["event_id"] = vals["event_id"] or None
    vals["pay_method"] = vals["pay_method"] if vals["pay_method"] in PAY_METHODS else ""
    _resolve_client(vals)
    cur = db.execute(
        f"INSERT INTO orders(created,public_token,{','.join(vals)}) VALUES(?,?,{','.join('?' * len(vals))})",
        [datetime.now().isoformat(timespec="seconds"), secrets.token_urlsafe(16), *vals.values()])
    oid = cur.lastrowid
    now = datetime.now().isoformat(timespec="seconds")
    db.execute("UPDATE orders SET status_since=? WHERE id=?", (now, oid))
    db.execute("INSERT INTO order_status_log(order_id,status,at,user) VALUES(?,?,?,?)", (oid, vals["status"], now, session.get("user", "")))
    _save_items(oid, d.get("items"))
    _link_product_files(oid)
    _sync_stock(oid)
    db.commit()
    if d.get("paid"):
        return update_order_payment(oid, d)
    return jsonify(order_full(oid)), 201


def update_order_payment(oid, d):
    get_db().execute("UPDATE orders SET paid=?, paid_to=?, paid_date=? WHERE id=?",
                     (1 if d.get("paid") else 0, d.get("paid_to", ""),
                      d.get("paid_date") or (date.today().isoformat() if d.get("paid") else ""), oid))
    _sync_payment(oid)
    return jsonify(order_full(oid))


@app.put("/api/orders/<int:oid>")
@login_required
def update_order(oid):
    if not one("SELECT id FROM orders WHERE id=?", (oid,)):
        return jsonify(error="no existe"), 404
    d = request.get_json(force=True) or {}
    db = get_db()
    vals = {k: d[k] for k in ORDER_FIELDS if k in d}
    for k in ("shipping", "discount"):
        if k in vals:
            vals[k] = num(vals[k])
    if vals.get("status") and vals["status"] not in ORDER_STATUSES:
        return jsonify(error="estado no válido"), 400
    if "client" in vals or "client_id" in vals:
        cur_o = one("SELECT client, client_id, contact, email, address FROM orders WHERE id=?", (oid,))
        merged = {**cur_o, **vals}
        if "client" in vals and "client_id" not in vals and vals["client"] != cur_o["client"]:
            merged["client_id"] = None
        _resolve_client(merged)
        vals["client"], vals["client_id"] = merged["client"], merged["client_id"]
    if "pay_method" in vals and vals["pay_method"] not in PAY_METHODS:
        vals["pay_method"] = ""
    old = one("SELECT status FROM orders WHERE id=?", (oid,))
    if vals.get("status") and vals["status"] != old["status"]:
        now = datetime.now().isoformat(timespec="seconds")
        vals["status_since"] = now
        db.execute("INSERT INTO order_status_log(order_id,status,at,user) VALUES(?,?,?,?)",
                   (oid, vals["status"], now, session.get("user", "")))
    if vals:
        db.execute(f"UPDATE orders SET {','.join(k + '=?' for k in vals)} WHERE id=?", [*vals.values(), oid])
    if "items" in d:
        _save_items(oid, d["items"])
        _link_product_files(oid)
    _sync_stock(oid)
    _sync_product_stock(oid)
    db.commit()
    if "paid" in d:
        return update_order_payment(oid, d)
    _sync_payment(oid)
    return jsonify(order_full(oid))


@app.delete("/api/orders/<int:oid>")
@login_required
def delete_order(oid):
    db = get_db()
    _undo_product_stock(oid)
    db.execute("DELETE FROM movements WHERE order_id=? AND category='Ventas'", (oid,))
    stored = [r["stored"] for r in rows("SELECT stored FROM files WHERE order_id=? AND product_id IS NULL", (oid,))]
    db.execute("DELETE FROM files WHERE order_id=? AND product_id IS NULL", (oid,))
    db.execute("DELETE FROM orders WHERE id=?", (oid,))
    db.commit()
    for st in stored:
        if not one("SELECT 1 AS x FROM files WHERE stored=?", (st,)):
            try:
                os.remove(os.path.join(FILES_DIR, st))
            except FileNotFoundError:
                pass
    return jsonify(ok=True)


# ---------------------------------------------------------------- archivos de pedidos/productos
def _link_product_files(oid):
    """Si una línea viene del catálogo, el pedido hereda los archivos del producto."""
    db = get_db()
    have = {r["stored"] for r in rows("SELECT stored FROM files WHERE order_id=?", (oid,))}
    pids = [r["product_id"] for r in rows("SELECT DISTINCT product_id FROM order_items WHERE order_id=? AND product_id IS NOT NULL", (oid,))]
    pids += [r["product_id"] for pid in list(pids) for r in rows("SELECT product_id FROM kit_items WHERE kit_id=?", (pid,))]
    for pid in pids:
        for fr in rows("SELECT * FROM files WHERE product_id=?", (pid,)):
            if fr["stored"] in have:
                continue
            db.execute("INSERT INTO files(order_id,stored,name,size,sha256,uploaded,uploaded_by,note) VALUES(?,?,?,?,?,?,?,?)",
                       (oid, fr["stored"], fr["name"], fr["size"], fr["sha256"], fr["uploaded"], fr["uploaded_by"],
                        "del catálogo"))
            have.add(fr["stored"])


def _file_row(fid):
    return one("SELECT * FROM files WHERE id=?", (fid,))


@app.post("/api/files")
@login_required
def upload_file():
    """Adjunta un archivo (STL/3MF/G-code…) a un pedido (order_id) o a un producto (product_id)."""
    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify(error="no se ha enviado archivo"), 400
    name = os.path.basename(f.filename.replace("\\", "/"))[:200]
    low = name.lower()
    ext = "gcode.3mf" if low.endswith(".gcode.3mf") else low.rsplit(".", 1)[-1]
    if ext not in MODEL_EXT and ext != "gcode.3mf":
        return jsonify(error="tipo no admitido (STL, 3MF, OBJ, STEP, G-code, resina, ZIP…)"), 400
    oid, pid = request.form.get("order_id"), request.form.get("product_id")
    if oid and not one("SELECT id FROM orders WHERE id=?", (oid,)):
        return jsonify(error="pedido no existe"), 404
    if pid and not one("SELECT id FROM products WHERE id=?", (pid,)):
        return jsonify(error="producto no existe"), 404
    import hashlib
    os.makedirs(FILES_DIR, exist_ok=True)
    stored = secrets.token_hex(12)
    path = os.path.join(FILES_DIR, stored)
    h, size = hashlib.sha256(), 0
    with open(path, "wb") as out:
        for chunk in iter(lambda: f.stream.read(1024 * 1024), b""):
            h.update(chunk)
            size += len(chunk)
            out.write(chunk)
    cur = get_db().execute(
        "INSERT INTO files(order_id,product_id,stored,name,size,sha256,uploaded,uploaded_by,note) VALUES(?,?,?,?,?,?,?,?,?)",
        (oid or None, pid or None, stored, name, size, h.hexdigest(), datetime.now().isoformat(timespec="seconds"),
         session.get("user"), request.form.get("note", "")))
    get_db().commit()
    return jsonify(one("SELECT id,name,size,uploaded,uploaded_by,note FROM files WHERE id=?", (cur.lastrowid,))), 201


@app.get("/api/files/<int:fid>")
@login_required
def download_file(fid):
    r = _file_row(fid)
    if not r:
        return jsonify(error="no existe"), 404
    ext = r["name"].rsplit(".", 1)[-1].lower() if "." in r["name"] else ""
    img = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}.get(ext)
    if img and request.args.get("inline"):   # fotos de montaje: se ven en la ficha
        resp = send_from_directory(FILES_DIR, r["stored"], mimetype=img)
    else:
        resp = send_from_directory(FILES_DIR, r["stored"], as_attachment=True, download_name=r["name"],
                                   mimetype="application/octet-stream")
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["Content-Security-Policy"] = "default-src 'none'; sandbox"
    return resp


@app.delete("/api/files/<int:fid>")
@login_required
def delete_file(fid):
    r = _file_row(fid)
    if not r:
        return jsonify(error="no existe"), 404
    db = get_db()
    db.execute("DELETE FROM files WHERE id=?", (fid,))
    # el fichero físico puede estar compartido con un pedido repetido
    if not one("SELECT 1 AS x FROM files WHERE stored=?", (r["stored"],)):
        try:
            os.remove(os.path.join(FILES_DIR, r["stored"]))
        except FileNotFoundError:
            pass
    db.commit()
    return jsonify(ok=True)


@app.get("/api/products/<int:pid>/files")
@login_required
def product_files(pid):
    return jsonify(rows("SELECT id,name,size,uploaded,uploaded_by,note FROM files WHERE product_id=? ORDER BY id", (pid,)))


@app.post("/api/orders/<int:oid>/repeat")
@login_required
def repeat_order(oid):
    """Crea un pedido nuevo con las mismas piezas, fichas de impresión y archivos."""
    o = order_full(oid)
    if not o:
        return jsonify(error="no existe"), 404
    db = get_db()
    vals = {k: o.get(k, "") for k in ("client", "contact", "channel", "assigned", "email", "address")}
    vals["notes"] = f"Repetición del pedido #{oid}. " + (o["notes"] or "")
    cur = db.execute(
        f"INSERT INTO orders(created,public_token,status,source,{','.join(vals)}) VALUES(?,?,?,?,{','.join('?' * len(vals))})",
        [datetime.now().isoformat(timespec="seconds"), secrets.token_urlsafe(16), "recibido", "interno", *vals.values()])
    nid = cur.lastrowid
    for it in o["items"]:
        db.execute("INSERT INTO order_items(order_id,description,qty,unit_price,unit_cost,calc_json,calc_result,product_id,print_info)"
                   " VALUES(?,?,?,?,?,?,?,?,?)",
                   (nid, it["description"], it["qty"], it["unit_price"], it["unit_cost"], it["calc_json"],
                    it["calc_result"], it["product_id"], it["print_info"]))
    for fr in rows("SELECT * FROM files WHERE order_id=?", (oid,)):
        db.execute("INSERT INTO files(order_id,stored,name,size,sha256,uploaded,uploaded_by,note) VALUES(?,?,?,?,?,?,?,?)",
                   (nid, fr["stored"], fr["name"], fr["size"], fr["sha256"], fr["uploaded"], fr["uploaded_by"],
                    f"del pedido #{oid}"))
    db.commit()
    return jsonify(order_full(nid)), 201


# ---------------------------------------------------------------- impresoras conectadas (Klipper/Moonraker)
import urllib.error  # noqa: E402
import urllib.parse  # noqa: E402
import urllib.request  # noqa: E402


def _norm_host(h):
    """Acepta 192.168.1.40, u1.local:7125, http://192.168.1.40/ … y lo deja como host[:puerto]."""
    h = str(h or "").strip()
    h = h.split("://", 1)[-1].split("/", 1)[0]
    return "".join(c for c in h if c.isalnum() or c in ".-:[]")[:100]


class PrinterError(Exception):
    pass


def http_json(printer, path, default_port, method="GET", params=None, body=None, headers=None, timeout=6, auth=True):
    """Petición a la API de una impresora (OctoPrint, PrusaLink…). api_key «usuario:contraseña» = autenticación digest."""
    host = printer["host"] if ":" in printer["host"].strip("[]") else f"{printer['host']}:{default_port}"
    url = f"http://{host}{path}" + (("?" + urllib.parse.urlencode(params)) if params else "")
    h = {"Accept": "application/json", **(headers or {})}
    key = printer.get("api_key") or ""
    opener = urllib.request.build_opener()
    if auth and key and ":" in key:
        user, pw = key.split(":", 1)
        mgr = urllib.request.HTTPPasswordMgrWithDefaultRealm()
        mgr.add_password(None, f"http://{host}/", user, pw)
        opener = urllib.request.build_opener(urllib.request.HTTPDigestAuthHandler(mgr), urllib.request.HTTPBasicAuthHandler(mgr))
    elif auth and key:
        h["X-Api-Key"] = key
    req = urllib.request.Request(url, data=body, method=method, headers=h)
    try:
        with opener.open(req, timeout=timeout) as r:
            raw = r.read().decode()
            return json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as e:
        if e.code == 204:
            return {}
        msg = {401: "no autorizado: revisa la API key o el usuario:contraseña", 403: "no autorizado: revisa la API key"}.get(e.code)
        raise PrinterError(msg or f"error HTTP {e.code}") from None
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise PrinterError(f"no responde ({getattr(e, 'reason', e)})") from None
    except ValueError:
        raise PrinterError("respuesta no válida") from None


def _temp(actual, target):
    return {"temperature": actual, "target": target}


def octoprint_status(p):
    job = http_json(p, "/api/job", 80)
    try:
        pr = http_json(p, "/api/printer", 80)
    except PrinterError:
        pr = {}
    state = (job.get("state") or "").lower()
    st = "printing" if state.startswith("printing") else "paused" if state.startswith("paus") else \
         "error" if "error" in state else "standby" if state.startswith("operational") or state == "ready" else state or "desconocido"
    if state.startswith("offline") or state.startswith("closed"):
        raise PrinterError("OctoPrint no está conectado a la impresora")
    prog = job.get("progress") or {}
    t = pr.get("temperature") or {}
    out = {"state": st, "filename": ((job.get("job") or {}).get("file") or {}).get("name") or "",
           "progress": round(prog.get("completion") or 0, 1), "print_duration": prog.get("printTime") or 0, "filament_mm": 0,
           "extruder": _temp((t.get("tool0") or {}).get("actual"), (t.get("tool0") or {}).get("target")),
           "bed": _temp((t.get("bed") or {}).get("actual"), (t.get("bed") or {}).get("target")), "eta": None}
    left = prog.get("printTimeLeft")
    if st in ("printing", "paused") and left:
        out["remaining"] = round(left)
        out["eta"] = (datetime.now() + timedelta(seconds=left)).isoformat(timespec="minutes")
    return out


def prusalink_status(p):
    s = http_json(p, "/api/v1/status", 80)
    pr, job = s.get("printer") or {}, s.get("job") or {}
    state = (pr.get("state") or "").upper()
    st = {"PRINTING": "printing", "PAUSED": "paused", "FINISHED": "complete", "STOPPED": "cancelled", "ERROR": "error",
          "ATTENTION": "paused", "IDLE": "standby", "READY": "standby", "BUSY": "standby"}.get(state, state.lower() or "desconocido")
    name = ""
    if job:
        try:
            jf = http_json(p, "/api/v1/job", 80)
            name = ((jf.get("file") or {}).get("display_name") or (jf.get("file") or {}).get("name") or "")
        except PrinterError:
            pass
    out = {"state": st, "filename": name, "progress": round(job.get("progress") or 0, 1),
           "print_duration": job.get("time_printing") or 0, "filament_mm": 0,
           "extruder": _temp(pr.get("temp_nozzle"), pr.get("target_nozzle")),
           "bed": _temp(pr.get("temp_bed"), pr.get("target_bed")), "eta": None}
    left = job.get("time_remaining")
    if st in ("printing", "paused") and left:
        out["remaining"] = round(left)
        out["eta"] = (datetime.now() + timedelta(seconds=left)).isoformat(timespec="minutes")
    return out


def moon(printer, path, method="GET", params=None, body=None, headers=None, timeout=6):
    if printer.get("conn") != "moonraker" or not printer.get("host"):
        raise PrinterError("la impresora no tiene conexión configurada")
    host = printer["host"] if ":" in printer["host"].strip("[]") else printer["host"] + ":7125"
    url = f"http://{host}{path}" + (("?" + urllib.parse.urlencode(params)) if params else "")
    h = {"Accept": "application/json", **(headers or {})}
    if printer.get("api_key"):
        h["X-Api-Key"] = printer["api_key"]
    req = urllib.request.Request(url, data=body, method=method, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode() or "{}").get("result", {})
    except urllib.error.HTTPError as e:
        msg = {401: "no autorizado: revisa la API key", 403: "no autorizado: revisa la API key o trusted_clients"}.get(e.code)
        raise PrinterError(msg or f"error HTTP {e.code}") from None
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise PrinterError(f"no responde ({getattr(e, 'reason', e)})") from None
    except ValueError:
        raise PrinterError("respuesta no válida (¿es Moonraker?)") from None


def _printer(pid):
    return one("SELECT * FROM printers WHERE id=?", (pid,))


def printer_status(p):
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
        except PrinterError:
            pass
        if est:
            remaining = max(0, est - out["print_duration"])
        elif progress > 0.01:
            remaining = out["print_duration"] / progress - out["print_duration"]
        else:
            remaining = None
        if remaining is not None:
            out["remaining"] = round(remaining)
            out["eta"] = (datetime.now() + timedelta(seconds=remaining)).isoformat(timespec="minutes")
    return out


@app.get("/api/printers/status")
@login_required
def printers_status():
    out = []
    for p in rows("SELECT * FROM printers WHERE active=1 AND conn IN ('moonraker','bridge','octoprint','prusalink') AND host!='' ORDER BY name"):
        item = {"id": p["id"], "name": p["name"], "host": p["host"], "via": p["conn"]}
        try:
            item.update(printer_status_any(p), online=True)
        except PrinterError as e:
            item.update(online=False, error=str(e))
        out.append(item)
    return jsonify(out)


BRIDGE_STALE = 45   # segundos sin noticias del puente → desconectado


def _bridge_cache(p):
    import time
    c = one("SELECT * FROM printer_cache WHERE printer_id=?", (p["id"],))
    b = one("SELECT * FROM bridges WHERE id=?", (p.get("bridge_id"),)) if p.get("bridge_id") else None
    if not b:
        raise PrinterError("no tiene puente asignado")
    if not b["last_seen"] or time.time() - b["last_seen"] > BRIDGE_STALE:
        when = datetime.fromtimestamp(b["last_seen"]).strftime("%d/%m %H:%M") if b["last_seen"] else "nunca"
        raise PrinterError(f"el puente «{b['name']}» no da señales (último contacto: {when})")
    if not c or not c["updated"] or time.time() - c["updated"] > BRIDGE_STALE:
        raise PrinterError("el puente aún no ha informado de esta impresora")
    if c["error"]:
        raise PrinterError(c["error"])
    return c


def printer_status_any(p):
    if p["conn"] == "bridge":
        return json.loads(_bridge_cache(p)["status_json"] or "{}")
    if p["conn"] == "octoprint":
        return octoprint_status(p)
    if p["conn"] == "prusalink":
        return prusalink_status(p)
    return printer_status(p)


@app.post("/api/printers/<int:pid>/test")
@admin_required
def printer_test(pid):
    p = _printer(pid)
    if not p:
        return jsonify(error="no existe"), 404
    if p["conn"] == "bridge":
        try:
            st = printer_status_any(p)
            return jsonify(ok=True, klippy_state=st.get("state"), hostname=f"vía puente · {p['host']}")
        except PrinterError as e:
            return jsonify(ok=False, error=str(e))
    if p["conn"] in ("octoprint", "prusalink"):
        try:
            if p["conn"] == "octoprint":
                v = http_json(p, "/api/version", 80)
                soft = f"OctoPrint {v.get('server', '')}"
            else:
                v = http_json(p, "/api/version", 80)
                soft = f"PrusaLink {v.get('server') or v.get('api') or ''}"
            st = printer_status_any(p)
            return jsonify(ok=True, klippy_state=st.get("state"), hostname=v.get("hostname") or p["host"], software=soft)
        except PrinterError as e:
            return jsonify(ok=False, error=str(e))
    try:
        info = moon(p, "/server/info")
        pi = {}
        try:
            pi = moon(p, "/printer/info")
        except PrinterError:
            pass
        return jsonify(ok=True, klippy_state=info.get("klippy_state"), moonraker=info.get("moonraker_version"),
                       hostname=pi.get("hostname"), software=pi.get("software_version"))
    except PrinterError as e:
        return jsonify(ok=False, error=str(e))


@app.get("/api/printers/<int:pid>/history")
@login_required
def printer_history(pid):
    p = _printer(pid)
    if not p:
        return jsonify(error="no existe"), 404
    if p["conn"] not in ("moonraker", "bridge"):
        return jsonify([])
    linked = {r["job_id"]: r["order_id"] for r in rows("SELECT job_id, order_id FROM print_jobs WHERE printer_id=?", (pid,))}
    if p["conn"] == "bridge":
        try:
            hist = json.loads(_bridge_cache(p)["history_json"] or "[]")
        except PrinterError as e:
            return jsonify(error=str(e)), 502
        for j in hist:
            j["order_id"] = linked.get(str(j.get("job_id")))
        return jsonify(hist)
    try:
        jobs = moon(p, "/server/history/list", params={"limit": 25, "order": "desc"}).get("jobs", [])
    except PrinterError as e:
        return jsonify(error=str(e)), 502
    out = []
    for j in jobs:
        md = j.get("metadata") or {}
        out.append({"job_id": str(j.get("job_id")), "filename": j.get("filename"), "status": j.get("status"),
                    "start_time": j.get("start_time"), "end_time": j.get("end_time"),
                    "print_duration": j.get("print_duration"), "total_duration": j.get("total_duration"),
                    "filament_mm": j.get("filament_used"), "filament_g": md.get("filament_weight_total"),
                    "estimated_time": md.get("estimated_time"), "order_id": linked.get(str(j.get("job_id")))})
    return jsonify(out)


@app.post("/api/printers/<int:pid>/history/<job_id>/assign")
@login_required
def assign_job(pid, job_id):
    """Asocia una impresión real (tiempo y filamento reales) a un pedido."""
    d = request.get_json(force=True) or {}
    oid = d.get("order_id")
    p = _printer(pid)
    if not p:
        return jsonify(error="no existe"), 404
    db = get_db()
    if not oid:
        db.execute("DELETE FROM print_jobs WHERE printer_id=? AND job_id=?", (pid, job_id))
        db.commit()
        return jsonify(ok=True)
    if not one("SELECT id FROM orders WHERE id=?", (oid,)):
        return jsonify(error="pedido no existe"), 404
    if p["conn"] == "bridge":
        c = one("SELECT history_json FROM printer_cache WHERE printer_id=?", (pid,))
        hj = next((x for x in json.loads((c or {}).get("history_json") or "[]") if str(x.get("job_id")) == str(job_id)), None)
        if not hj:
            return jsonify(error="esa impresión ya no está en el historial del puente"), 404
        j = {"filename": hj.get("filename"), "status": hj.get("status"), "start_time": hj.get("start_time"),
             "end_time": hj.get("end_time"), "print_duration": hj.get("print_duration"),
             "total_duration": hj.get("total_duration"), "filament_used": hj.get("filament_mm"),
             "metadata": {"filament_weight_total": hj.get("filament_g"), "estimated_time": hj.get("estimated_time")}}
    else:
        try:
            j = moon(p, "/server/history/job", params={"uid": job_id}).get("job", {})
        except PrinterError as e:
            return jsonify(error=str(e)), 502
    md = j.get("metadata") or {}
    db.execute("""INSERT INTO print_jobs(printer_id,order_id,job_id,filename,status,start_time,end_time,print_duration,
                  total_duration,filament_mm,filament_g,estimated_time) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
                  ON CONFLICT(printer_id,job_id) DO UPDATE SET order_id=excluded.order_id""",
               (pid, oid, str(job_id), j.get("filename", ""), j.get("status", ""), j.get("start_time"), j.get("end_time"),
                j.get("print_duration") or 0, j.get("total_duration") or 0, j.get("filament_used") or 0,
                md.get("filament_weight_total"), md.get("estimated_time")))
    db.commit()
    return jsonify(ok=True)


def _multipart(fields, file_field, filename, fileobj):
    boundary = "----mitallercito" + secrets.token_hex(12)
    parts = []
    for k, v in fields.items():
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
    safe = "".join(c for c in filename if c.isalnum() or c in "._- ")[:120] or "pieza.gcode"
    parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{file_field}"; filename="{safe}"\r\n'
                 f'Content-Type: application/octet-stream\r\n\r\n'.encode())
    body = b"".join(parts) + fileobj.read() + f"\r\n--{boundary}--\r\n".encode()
    return body, f"multipart/form-data; boundary={boundary}", safe


@app.post("/api/printers/<int:pid>/send")
@login_required
def send_to_printer(pid):
    """Sube un G-code adjunto (de un pedido o producto) a la impresora y, si se pide, lo arranca."""
    d = request.get_json(force=True) or {}
    p, f = _printer(pid), _file_row(d.get("file_id"))
    if not p or not f:
        return jsonify(error="impresora o archivo no existe"), 404
    if not f["name"].lower().endswith((".gcode", ".gco", ".g", ".bgcode")):
        return jsonify(error="solo se pueden enviar G-code (.gcode). Desde un 3MF, exporta el G-code de la placa."), 400
    try:
        st = printer_status_any(p)
    except PrinterError as e:
        return jsonify(error=str(e)), 502
    start = bool(d.get("start"))
    if p["conn"] == "bridge":
        if start and st.get("state") in ("printing", "paused"):
            return jsonify(error=f"{p['name']} está ocupada ({st['state']}). Se puede subir sin arrancar."), 409
        import time
        get_db().execute("""INSERT INTO bridge_cmds(bridge_id,printer_id,kind,file_id,start,order_id,created,updated,requested_by)
                            VALUES(?,?,?,?,?,?,?,?,?)""", (p["bridge_id"], pid, "send", f["id"], int(start), d.get("order_id"),
                                                           time.time(), time.time(), session.get("user")))
        get_db().commit()
        return jsonify(ok=True, queued=True, filename=f["name"], started=False,
                       message=f"Enviado al puente: {p['name']} lo recibirá en unos segundos")
    if start and st["state"] in ("printing", "paused"):
        return jsonify(error=f"{p['name']} está ocupada ({st['state']}). Se puede subir sin arrancar."), 409
    with open(os.path.join(FILES_DIR, f["stored"]), "rb") as fh:
        body, ctype, safe = _multipart({"root": "gcodes", "print": "true" if start else "false"}, "file", f["name"], fh)
    try:
        moon(p, "/server/files/upload", method="POST", body=body, headers={"Content-Type": ctype}, timeout=300)
    except PrinterError as e:
        return jsonify(error=str(e)), 502
    app.logger.warning("%s envía %s a %s (arrancar=%s)", session.get("user"), f["name"], p["name"], start)
    oid = d.get("order_id")
    if start and oid and one("SELECT id FROM orders WHERE id=? AND status IN ('recibido','programado','presupuesto')", (oid,)):
        get_db().execute("UPDATE orders SET status='imprimiendo' WHERE id=?", (oid,))
        _sync_stock(oid)
        get_db().commit()
    return jsonify(ok=True, filename=safe, started=start)


# ---------------------------------------------------------------- puentes (impresoras en otra red)
import hashlib  # noqa: E402


def _tok_hash(t):
    return hashlib.sha256(t.encode()).hexdigest()


@app.get("/api/bridges")
@admin_required
def list_bridges():
    import time
    bs = rows("SELECT id,name,created,last_seen,last_ip,version FROM bridges ORDER BY name")
    for b in bs:
        b["online"] = bool(b["last_seen"] and time.time() - b["last_seen"] <= BRIDGE_STALE)
        b["printers"] = [r["name"] for r in rows("SELECT name FROM printers WHERE bridge_id=? AND conn='bridge'", (b["id"],))]
    return jsonify(bs)


@app.post("/api/bridges")
@admin_required
def create_bridge():
    name = str((request.get_json(force=True) or {}).get("name", "")).strip()[:60] or "Puente"
    tok = "mtb_" + secrets.token_urlsafe(32)
    cur = get_db().execute("INSERT INTO bridges(name,token_hash,created) VALUES(?,?,?)",
                           (name, _tok_hash(tok), datetime.now().isoformat(timespec="seconds")))
    get_db().commit()
    return jsonify(id=cur.lastrowid, name=name, token=tok), 201   # el token solo se enseña ahora


@app.delete("/api/bridges/<int:bid>")
@admin_required
def delete_bridge(bid):
    db = get_db()
    db.execute("UPDATE printers SET bridge_id=NULL WHERE bridge_id=?", (bid,))
    db.execute("DELETE FROM bridges WHERE id=?", (bid,))
    db.commit()
    return jsonify(ok=True)


def bridge_required(fn):
    @wraps(fn)
    def wrapper(*a, **kw):
        import time
        h = request.headers.get("Authorization", "")
        tok = h[7:].strip() if h.startswith("Bearer ") else ""
        b = one("SELECT * FROM bridges WHERE token_hash=?", (_tok_hash(tok),)) if tok else None
        if not b:
            return jsonify(error="token de puente no válido"), 401
        get_db().execute("UPDATE bridges SET last_seen=?, last_ip=?, version=? WHERE id=?",
                         (time.time(), request.remote_addr or "", request.headers.get("X-Bridge-Version", "")[:20], b["id"]))
        get_db().commit()
        g.bridge = b
        return fn(*a, **kw)
    return wrapper


@app.get("/api/bridge/config")
@bridge_required
def bridge_config():
    ps = rows("SELECT id,name,host,api_key FROM printers WHERE bridge_id=? AND conn='bridge' AND active=1 AND host!=''",
              (g.bridge["id"],))
    return jsonify(bridge=g.bridge["name"], printers=ps, poll=10, history_every=60)


@app.post("/api/bridge/report")
@bridge_required
def bridge_report():
    import time
    d = request.get_json(force=True) or {}
    mine = {r["id"] for r in rows("SELECT id FROM printers WHERE bridge_id=? AND conn='bridge'", (g.bridge["id"],))}
    db = get_db()
    for it in d.get("printers", [])[:50]:
        pid = it.get("id")
        if pid not in mine:
            continue
        old = one("SELECT history_json FROM printer_cache WHERE printer_id=?", (pid,))
        hist = json.dumps(it["history"][:50]) if isinstance(it.get("history"), list) else (old or {}).get("history_json")
        db.execute("""INSERT INTO printer_cache(printer_id,status_json,error,history_json,updated) VALUES(?,?,?,?,?)
                      ON CONFLICT(printer_id) DO UPDATE SET status_json=excluded.status_json, error=excluded.error,
                      history_json=excluded.history_json, updated=excluded.updated""",
                   (pid, json.dumps(it.get("status") or {}), str(it.get("error") or "")[:300], hist, time.time()))
        if isinstance(it.get("history"), list):
            _import_jobs(pid, it["history"])
    db.commit()
    return jsonify(ok=True)


@app.get("/api/bridge/commands")
@bridge_required
def bridge_commands():
    import time
    db = get_db()
    # lo que se quedó a medias (el puente se reinició) vuelve a la cola a los 10 min
    db.execute("UPDATE bridge_cmds SET state='pending' WHERE state='taken' AND updated<?", (time.time() - 600,))
    cmds = rows("""SELECT c.id, c.kind, c.printer_id, c.file_id, c.start, f.name AS filename, f.size
                   FROM bridge_cmds c LEFT JOIN files f ON f.id=c.file_id
                   WHERE c.bridge_id=? AND c.state='pending' ORDER BY c.id LIMIT 5""", (g.bridge["id"],))
    for c in cmds:
        db.execute("UPDATE bridge_cmds SET state='taken', updated=? WHERE id=?", (time.time(), c["id"]))
    db.commit()
    return jsonify(cmds)


@app.get("/api/bridge/files/<int:cmd_id>")
@bridge_required
def bridge_file(cmd_id):
    c = one("SELECT * FROM bridge_cmds WHERE id=? AND bridge_id=? AND state='taken'", (cmd_id, g.bridge["id"]))
    f = _file_row(c["file_id"]) if c else None
    if not f:
        return jsonify(error="no autorizado"), 404
    return send_from_directory(FILES_DIR, f["stored"], as_attachment=True, download_name=f["name"],
                               mimetype="application/octet-stream")


@app.post("/api/bridge/commands/<int:cmd_id>")
@bridge_required
def bridge_cmd_result(cmd_id):
    import time
    d = request.get_json(force=True) or {}
    c = one("SELECT * FROM bridge_cmds WHERE id=? AND bridge_id=?", (cmd_id, g.bridge["id"]))
    if not c:
        return jsonify(error="no existe"), 404
    db = get_db()
    db.execute("UPDATE bridge_cmds SET state=?, result=?, updated=? WHERE id=?",
               ("done" if d.get("ok") else "error", str(d.get("message", ""))[:300], time.time(), cmd_id))
    if d.get("ok") and c["start"] and c["order_id"] and \
            one("SELECT id FROM orders WHERE id=? AND status IN ('recibido','programado','presupuesto')", (c["order_id"],)):
        db.execute("UPDATE orders SET status='imprimiendo' WHERE id=?", (c["order_id"],))
        _sync_stock(c["order_id"])
    db.commit()
    return jsonify(ok=True)


@app.get("/api/bridge-cmds")
@login_required
def list_bridge_cmds():
    return jsonify(rows("""SELECT c.id, c.state, c.result, c.created, c.start, p.name AS printer, f.name AS filename
                           FROM bridge_cmds c LEFT JOIN printers p ON p.id=c.printer_id LEFT JOIN files f ON f.id=c.file_id
                           ORDER BY c.id DESC LIMIT 20"""))


@app.get("/api/orders/<int:oid>/jobs")
@login_required
def order_jobs(oid):
    js = rows("""SELECT j.*, p.name AS printer FROM print_jobs j LEFT JOIN printers p ON p.id=j.printer_id
                 WHERE j.order_id=? ORDER BY j.start_time""", (oid,))
    return jsonify(js)


# ---------------------------------------------------------------- almacén de bobinas
SPOOL_FIELDS = ["supplier", "material_id", "brand", "color_name", "color_hex", "net_g", "tare_g", "price", "location", "status", "notes"]


def _hex(h):
    h = str(h or "").strip().lstrip("#")
    return "#" + h.upper() if len(h) == 6 and all(c in "0123456789abcdefABCDEF" for c in h) else ""


def _kind_of(material_id):
    m = one("SELECT kind FROM materials WHERE id=?", (material_id,)) if material_id else None
    return (m or {}).get("kind") or ""


def known_tare(brand, kind):
    r = one("SELECT tare_g FROM spool_tares WHERE brand=? AND kind=?", (str(brand).strip().lower(), str(kind).strip().lower()))
    if not r:
        r = one("SELECT AVG(tare_g) AS tare_g FROM spool_tares WHERE brand=?", (str(brand).strip().lower(),))
    return round(r["tare_g"], 1) if r and r["tare_g"] else None


def learn_tare(brand, kind, tare):
    brand, kind = str(brand or "").strip().lower(), str(kind or "").strip().lower()
    if not brand or tare is None or tare <= 0:
        return
    db = get_db()
    r = one("SELECT * FROM spool_tares WHERE brand=? AND kind=?", (brand, kind))
    if r:
        n = r["samples"] + 1
        db.execute("UPDATE spool_tares SET tare_g=?, samples=?, updated=? WHERE id=?",
                   (round((r["tare_g"] * r["samples"] + tare) / n, 1), n, date.today().isoformat(), r["id"]))
    else:
        db.execute("INSERT INTO spool_tares(brand,kind,tare_g,samples,updated) VALUES(?,?,?,?,?)",
                   (brand, kind, round(tare, 1), 1, date.today().isoformat()))


def spool_out(sp):
    m = one("SELECT name, kind, unit, price, qty FROM materials WHERE id=?", (sp["material_id"],)) if sp["material_id"] else None
    sp = dict(sp)
    sp["material"] = (m or {}).get("name", "")
    sp["kind"] = (m or {}).get("kind", "")
    sp["unit"] = (m or {}).get("unit", "g")
    sp["remaining"] = spool_remaining(sp["id"])
    sp["pct"] = round(max(0, sp["remaining"]) / sp["net_g"] * 100) if sp["net_g"] else 0
    sp["suggested_tare"] = sp["tare_g"] if sp["tare_g"] else known_tare(sp["brand"], sp["kind"])
    return sp


@app.get("/api/spools")
@login_required
def list_spools():
    q = "SELECT * FROM spools" + ("" if request.args.get("all") == "1" else " WHERE status!='gastada'")
    return jsonify([spool_out(sp) for sp in rows(q + " ORDER BY material_id, color_name, id")])


@app.post("/api/spools")
@login_required
def create_spools():
    d = request.get_json(force=True) or {}
    count = max(1, min(50, int(num(d.get("count"), 1))))
    created_mat = False
    if d.get("material_id") in (None, "", "new") and isinstance(d.get("new_material"), dict):
        d["material_id"], created_mat = _material_for_spool(d, count)
        if not d["material_id"]:
            return jsonify(error="ponle nombre al material nuevo"), 400
    if not d.get("material_id") or not one("SELECT id FROM materials WHERE id=?", (d["material_id"],)):
        return jsonify(error="elige el material"), 400
    supplier = str(d.get("supplier", "")).strip()[:60]
    kind = _kind_of(d["material_id"])
    tare = num(d.get("tare_g"), None) if d.get("tare_g") not in (None, "") else known_tare(d.get("brand", ""), kind)
    db, ids = get_db(), []
    for _ in range(count):
        cur = db.execute("""INSERT INTO spools(material_id,brand,color_name,color_hex,net_g,tare_g,price,location,status,notes,created,supplier)
                            VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                         (d["material_id"], str(d.get("brand", "")).strip()[:40], str(d.get("color_name", "")).strip()[:40],
                          _hex(d.get("color_hex")), num(d.get("net_g"), 1000), tare, num(d.get("price"), None),
                          str(d.get("location", ""))[:40], "cerrada", str(d.get("notes", ""))[:300], date.today().isoformat(), supplier))
        ids.append(cur.lastrowid)
    lid = d.get("location_id") or None
    if lid and one("SELECT 1 AS x FROM locations WHERE id=?", (lid,)):
        db.execute("UPDATE spools SET location_id=?, location=? WHERE id IN (%s)" % ",".join("?" * len(ids)), [lid, _loc_path(lid), *ids])
    paid = num(d.get("paid_total"), 0)
    if paid > 0:
        m = one("SELECT name, unit FROM materials WHERE id=?", (d["material_id"],))
        db.execute("INSERT INTO movements(date,kind,category,concept,amount,person) VALUES(?,?,?,?,?,?)",
                   (date.today().isoformat(), "gasto", "Resina" if m["unit"] == "ml" else "Filamento",
                    f"{count} × {d.get('brand', '')} {m['name']} {d.get('color_name', '')}".strip(), paid, d.get("person", "")))
        db.execute("UPDATE spools SET price=? WHERE id IN (%s)" % ",".join("?" * len(ids)), [round(paid / count, 2), *ids])
        net = num(d.get("net_g"), 1000) or 1000
        _record_price(d["material_id"], count, net, paid, supplier, str(d.get("brand", "")).strip(), "bobinas")
        if d.get("update_price", True):
            mq = one("SELECT qty FROM materials WHERE id=?", (d["material_id"],))["qty"] or 1000
            db.execute("UPDATE materials SET price=? WHERE id=?", (round(paid / count / net * mq, 2), d["material_id"]))
    if d.get("shopping_id"):
        db.execute("UPDATE shopping SET status='comprado', bought_at=? WHERE id=?", (date.today().isoformat(), d["shopping_id"]))
    if d.get("tare_g") not in (None, "") and tare and not one("SELECT 1 AS x FROM spool_tares WHERE brand=? AND kind=?",
                                                               (str(d.get("brand", "")).strip().lower(), kind.lower())):
        learn_tare(d.get("brand", ""), kind, tare)       # la tara que pones a mano también se recuerda para la marca
    db.execute("UPDATE materials SET track_stock=1 WHERE id=?", (d["material_id"],))
    db.commit()
    resp = jsonify([spool_out(one("SELECT * FROM spools WHERE id=?", (i,))) for i in ids])
    if created_mat:
        resp.headers["X-Material-Created"] = str(d["material_id"])
    return resp, 201


SPOOL_KINDS = ("PLA", "PLA+", "PLA Silk", "PLA Mate", "PLA-CF", "PETG", "PETG-CF", "ABS", "ASA", "TPU", "Nylon", "PC", "Resina")


def _material_for_spool(d, count):
    """Material nuevo desde el alta de bobinas: si ya hay uno con ese nombre se reutiliza; si no, se crea
    con el precio que sale de lo pagado (o el habitual del tipo) y el control de stock activado."""
    nm = d["new_material"]
    name = str(nm.get("name") or "").strip()[:60]
    kind = str(nm.get("kind") or "PLA").strip()[:30] or "PLA"
    if not name:
        return None, False
    ex = one("SELECT id FROM materials WHERE lower(name)=lower(?)", (name,))
    if ex:
        return ex["id"], False
    resin = kind.lower().startswith("resin")
    net = num(d.get("net_g"), 1000) or 1000
    paid = num(d.get("paid_total"), 0)
    price = round(paid / count, 2) if paid > 0 else (32.0 if resin else 20.0)
    mid = get_db().execute("INSERT INTO materials(name,kind,color,price,qty,unit,active,track_stock) VALUES(?,?,?,?,?,?,1,1)",
                           (name, kind, str(d.get("color_name") or "").strip()[:40], price, net, "ml" if resin else "g")).lastrowid
    return mid, True


# ================================================================ leer bobinas de Amazon / tiendas
import html as _html  # noqa: E402
import re as _re  # noqa: E402

SHOP_HOSTS = _re.compile(r"(^|\.)(amazon\.(com|es|de|fr|it|co\.uk|nl|se|pl|com\.be|com\.mx|ca|com\.tr)|amzn\.(to|eu)|a\.co|"
                         r"aliexpress\.(com|us|ru)|s\.click\.aliexpress\.com)$")
SPOOL_BRANDS = ["Bambu Lab", "Bambu", "Sunlu", "eSun", "Elegoo", "Polymaker", "PolyTerra", "Jayo", "Geeetech", "Overture", "Kingroon",
                "Creality", "Anycubic", "Prusament", "Prusa", "Eryone", "Amolen", "Kexcelled", "Fiberlogy", "FormFutura", "Extrudr",
                "Smart Materials", "Winkle", "Fillamentum", "Spectrum", "3DJake", "ColorFabb", "Snapmaker", "Tinmorry", "Iiid Max",
                "Ziro", "Duramic", "Inland", "Hatchbox", "Phrozen", "Siraya Tech", "Flashforge", "Voxelab", "Azurefilm", "Rosa3D", "Sovol",
                "Qidi", "Giantarm", "Ttyt3d", "Marble", "R3D", "Yousu", "Sakata", "Ultimaker", "Raise3D", "Comgrow"]
# (patrón, tipo) en orden: lo más específico primero
SPOOL_KIND_RX = [(r"\bpla[\s-]*cf\b|\bpla\b[^,.;]{0,25}fibra de carbono|carbon fib(er|re) pla", "PLA-CF"),
                 (r"\bpetg[\s-]*cf\b|\bpetg\b[^,.;]{0,25}(fibra de carbono|carbon)", "PETG-CF"),
                 (r"\bsilk\b|\bseda\b|sedoso", "PLA Silk"), (r"\bpla\b[^,.;]{0,20}\b(mate|matte)\b|\b(mate|matte)\b[^,.;]{0,12}\bpla\b", "PLA Mate"),
                 (r"\bpla\s*(\+|plus|pro)", "PLA+"), (r"\bpetg\b", "PETG"), (r"\basa\b", "ASA"), (r"\babs\b", "ABS"), (r"\btpu\b|\bflexible\b", "TPU"),
                 (r"\bnylon\b|\bpa\d*\b", "Nylon"), (r"\bpolicarbonato\b|\bpc\b", "PC"), (r"\bresin[ae]?\b|\b(uv|lcd|dlp)\b[^,.;]{0,15}\bresin", "Resina"),
                 (r"\bpla\b", "PLA")]
# nombre en el texto → nombre en español; los compuestos primero
SPOOL_COLORS = [("brilla en la oscuridad", "Brilla en la oscuridad"), ("glow in the dark", "Brilla en la oscuridad"), ("fosforescente", "Brilla en la oscuridad"),
                ("azul marino", "Azul marino"), ("navy blue", "Azul marino"), ("sky blue", "Celeste"), ("light blue", "Celeste"), ("azul cielo", "Celeste"),
                ("dark grey", "Gris oscuro"), ("dark gray", "Gris oscuro"), ("gris oscuro", "Gris oscuro"), ("light grey", "Gris claro"), ("gris claro", "Gris claro"),
                ("verde oliva", "Verde oliva"), ("olive green", "Verde oliva"), ("cool white", "Blanco"), ("bone white", "Blanco hueso"),
                ("rainbow", "Arcoíris"), ("arcoiris", "Arcoíris"), ("arcoíris", "Arcoíris"), ("multicolor", "Multicolor"),
                ("negro", "Negro"), ("black", "Negro"), ("blanco", "Blanco"), ("white", "Blanco"), ("gris", "Gris"), ("grey", "Gris"), ("gray", "Gris"),
                ("rojo", "Rojo"), ("red", "Rojo"), ("azul", "Azul"), ("blue", "Azul"), ("verde", "Verde"), ("green", "Verde"),
                ("amarillo", "Amarillo"), ("yellow", "Amarillo"), ("naranja", "Naranja"), ("orange", "Naranja"), ("rosa", "Rosa"), ("pink", "Rosa"),
                ("morado", "Morado"), ("purple", "Morado"), ("violeta", "Violeta"), ("violet", "Violeta"), ("lila", "Lila"), ("marrón", "Marrón"),
                ("marron", "Marrón"), ("brown", "Marrón"), ("beige", "Beige"), ("dorado", "Dorado"), ("gold", "Dorado"), ("plateado", "Plateado"),
                ("plata", "Plateado"), ("silver", "Plateado"), ("cobre", "Cobre"), ("copper", "Cobre"), ("bronce", "Bronce"), ("bronze", "Bronce"),
                ("transparente", "Transparente"), ("transparent", "Transparente"), ("clear", "Transparente"), ("natural", "Natural"),
                ("turquesa", "Turquesa"), ("turquoise", "Turquesa"), ("granate", "Granate"), ("piel", "Piel"), ("skin", "Piel"), ("madera", "Madera"), ("wood", "Madera"), ("marfil", "Marfil"), ("ivory", "Marfil"), ("crema", "Crema"), ("cream", "Crema"),
                ("fucsia", "Fucsia"), ("magenta", "Magenta"), ("cian", "Cian"), ("cyan", "Cian"), ("caqui", "Caqui"), ("khaki", "Caqui")]


def parse_spool_text(text):
    """Saca de un título de tienda (o de la URL) lo que hace falta para dar de alta la bobina."""
    raw = _html.unescape(str(text or ""))
    t = " " + _re.sub(r"\s+", " ", raw) + " "
    low = t.lower()
    out = {"title": raw.strip()[:300]}
    for b in SPOOL_BRANDS:
        if _re.search(r"(?<![a-z0-9])" + _re.escape(b.lower()) + r"(?![a-z0-9])", low):
            out["brand"] = "Bambu Lab" if b == "Bambu" else b
            break
    if "brand" not in out:   # marcas que no conocemos: suelen ir delante y en mayúsculas («KINGROON PLA…»)
        m = _re.match(r"\s*([A-Z][A-Z0-9]{2,15})\b", raw.strip())
        if m and m.group(1).lower() not in ("pla", "petg", "abs", "asa", "tpu", "pc", "uv", "lcd", "dlp", "3d", "filamento", "filament", "resina", "resin"):
            out["brand"] = m.group(1).capitalize()
    for rx, k in SPOOL_KIND_RX:
        if _re.search(rx, low):
            out["kind"] = k
            break
    m = _re.search(r"\b(1[.,]75|2[.,]85|3[.,]00?)\s*mm", low)
    if m:
        out["diameter"] = float(m.group(1).replace(",", "."))
    # cuántas: "4 x 1kg", "pack de 4", "4 rollos", "4-pack", "paquete de 4"
    cnt = None
    m = _re.search(r"\b(\d{1,2})\s*[x×]\s*(\d+(?:[.,]\d+)?)\s*(kg|g|gr|ml|l)\b", low)
    if m:
        cnt = int(m.group(1))
    for rx in (r"\b(?:pack|paquete|lote|set)\s*(?:de|of)?\s*(\d{1,2})\b", r"\b(\d{1,2})\s*[-\s]?(?:pack|rollos|rolls|bobinas|spools|unidades|uds?)\b"):
        m2 = _re.search(rx, low)
        if m2 and not cnt:
            cnt = int(m2.group(1))
    if cnt and 1 <= cnt <= 20:
        out["count"] = cnt
    # peso por bobina
    w = None
    m = _re.search(r"\b\d{1,2}\s*[x×]\s*(\d+(?:[.,]\d+)?)\s*(kg|g|gr|ml|l)\b", low) or _re.search(r"\b(\d+(?:[.,]\d+)?)\s*(kg|g|gr|ml|l)\b(?!\s*/)", low)
    if m:
        v, u = float(m.group(1).replace(",", ".")), m.group(2)
        w = v * 1000 if u in ("kg", "l") else v
        total = None
        if not _re.search(r"\b\d{1,2}\s*[x×]", low) and out.get("count", 1) > 1 and w >= 1000 * out["count"] and w % out["count"] == 0:
            total = w           # "4 kg, pack de 4" → 1 kg cada una
        if total:
            w = total / out["count"]
    if w and 50 <= w <= 10000:
        out["net_g"] = round(w)
    # colores (puede haber varios en un pack)
    cols, seen = [], set()
    rest = low
    for word, es in SPOOL_COLORS:
        for mm in _re.finditer(r"(?<![a-záéíóúñ])" + _re.escape(word) + r"(?![a-záéíóúñ])", rest):
            if es not in seen:
                seen.add(es)
                cols.append((mm.start(), es))
            rest = rest[:mm.start()] + " " * len(word) + rest[mm.end():]   # que «azul marino» no cuente también «azul»
    cols = [c for _, c in sorted(cols)]
    if cols:
        out["colors"] = cols[:12]
        out["color_name"] = cols[0]
    m = _re.search(r"(\d{1,4}[.,]\d{2})\s*(€|eur)|€\s*(\d{1,4}[.,]\d{2})", low)
    if m:
        out["price"] = float((m.group(1) or m.group(3)).replace(",", "."))
    if "amazon" in low or "amzn" in low:
        out["supplier"] = "Amazon"
    elif "aliexpress" in low:
        out["supplier"] = "AliExpress"
    if out.get("kind") == "Resina":
        out["unit"] = "ml"
    return out


class _ShopRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not _shop_url_ok(newurl):
            raise urllib.error.URLError("la tienda redirige a otro sitio")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _shop_url_ok(url):
    p = urllib.parse.urlsplit(url)
    return p.scheme in ("http", "https") and bool(SHOP_HOSTS.search((p.hostname or "").lower()))


def _slug_text(url):
    """Las URL de Amazon llevan el título en la ruta: /SUNLU-Filamento-PLA-1-75mm/dp/B0…"""
    path = urllib.parse.unquote(urllib.parse.urlsplit(url).path)
    parts = [x for x in path.split("/") if x and x not in ("dp", "gp", "product", "item", "d") and not x.startswith("ref=")
             and not _re.fullmatch(r"[A-Z0-9]{10}|\d+(\.html)?", x)]
    return " ".join(p.replace("-", " ").replace("_", " ") for p in parts)


def fetch_shop(url, timeout=8):
    """Descarga la ficha (si la tienda se deja). Devuelve (url_final, título, precio) o lanza error."""
    op = urllib.request.build_opener(_ShopRedirect)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36",
                                               "Accept-Language": "es-ES,es;q=0.9,en;q=0.6", "Accept": "text/html"})
    with op.open(req, timeout=timeout) as r:
        final = r.geturl()
        body = r.read(3_000_000).decode("utf-8", "replace")
    if "captcha" in body.lower() and "productTitle" not in body:
        return final, "", None
    title = ""
    for rx in (r'id="productTitle"[^>]*>\s*(.*?)\s*<', r'<meta property="og:title" content="([^"]+)"', r'"subject":"([^"]+)"', r"<title>\s*(.*?)\s*</title>"):
        m = _re.search(rx, body, _re.S)
        if m:
            title = _html.unescape(_re.sub(r"\s+", " ", m.group(1))).strip()
            break
    price = None
    m = _re.search(r'class="a-offscreen">\s*([\d.,]+)\s*€', body) or _re.search(r'"priceAmount":\s*([\d.]+)', body) or \
        _re.search(r'"formatedActivityPrice":"[^\d]*([\d.,]+)', body)
    if m:
        try:
            price = float(m.group(1).replace(".", "").replace(",", ".") if "," in m.group(1) else m.group(1))
        except ValueError:
            price = None
    return final, title, price


@app.post("/api/spools/parse")
@login_required
def spools_parse():
    text = str((request.get_json(force=True) or {}).get("text") or "").strip()[:2000]
    if not text:
        return jsonify(error="pega el enlace o el título del producto"), 400
    return jsonify(_parse_shop_input(text))


@app.post("/api/components/parse")
@login_required
def components_parse():
    """Nombre, precio y unidades del pack de un componente pegado de Amazon o de otra tienda."""
    text = str((request.get_json(force=True) or {}).get("text") or "").strip()[:2000]
    if not text:
        return jsonify(error="pega el enlace o el título del producto"), 400
    r = _parse_shop_input(text)
    title = r.get("title") or ""
    if _re.match(r"https?://", title.strip()):
        title = ""
    low = " " + (title or text).lower() + " "
    m = _re.search(r"\b(\d{1,5})\s*(?:piezas|pzas?|pcs|pc|uds?|unidades|unids|units|pieces|pares|pairs)\b", low) or \
        _re.search(r"\b(?:pack|paquete|lote|set|caja)\s*(?:de|of)\s*(\d{1,5})\b", low)
    pieces = int(m.group(1)) if m else r.get("count")
    name = _re.split(r"\s[,|–—-]\s|, ", title)[0].strip() if title else ""
    return jsonify(name=(name or title)[:80], title=title[:300], price=r.get("price"), pieces=pieces,
                   supplier=r.get("supplier", ""), note=r.get("note", ""))


def _parse_shop_input(text):
    url = (_re.search(r"https?://\S+", text) or [None])[0]
    note, extra = "", ""
    if url:
        if not _shop_url_ok(url):
            note = "Solo leo enlaces de Amazon y AliExpress; con otras tiendas pega el título."
        else:
            try:
                final, title, price = fetch_shop(url)
                extra = " ".join(x for x in (title, _slug_text(final), "amazon" if "amazon" in final or "amzn" in final else "") if x)
                if price:
                    extra += f" {price:.2f} €"
                if not title:
                    note = "La tienda no ha dejado leer la ficha (pide captcha): lo saco del enlace. Si falta algo, pega el título."
            except Exception as e:  # noqa: BLE001
                extra = _slug_text(url) + (" amazon" if "amaz" in url or "amzn" in url else "")
                note = f"No he podido abrir la ficha ({getattr(e, 'reason', None) or e}): lo saco del enlace. Si falta algo, pega el título."
    r = parse_spool_text((text.replace(url, " ") if url else text) + " " + extra)
    if url and "aliexpress" in url:
        r["supplier"] = "AliExpress"
    if url and extra and not (text.replace(url, "").strip()):
        r["title"] = extra.replace(" amazon", "").strip()[:300]
    r["note"] = note
    return r


@app.put("/api/spools/<int:sid>")
@login_required
def update_spool(sid):
    d = request.get_json(force=True) or {}
    f = {k: d[k] for k in SPOOL_FIELDS if k in d}
    if "color_hex" in f:
        f["color_hex"] = _hex(f["color_hex"])
    if f.get("status") and f["status"] not in ("cerrada", "abierta", "gastada"):
        return jsonify(error="estado no válido"), 400
    for k in ("net_g", "tare_g", "price"):
        if k in f:
            f[k] = num(f[k], None)
    if f:
        get_db().execute(f"UPDATE spools SET {','.join(k + '=?' for k in f)} WHERE id=?", [*f.values(), sid])
        get_db().commit()
    sp = one("SELECT * FROM spools WHERE id=?", (sid,))
    return (jsonify(spool_out(sp)), 200) if sp else (jsonify(error="no existe"), 404)


@app.post("/api/spools/<int:sid>/weigh")
@login_required
def weigh_spool(sid):
    """Pesas la bobina entera: lo que queda = peso − bobina vacía."""
    sp = one("SELECT * FROM spools WHERE id=?", (sid,))
    if not sp:
        return jsonify(error="no existe"), 404
    d = request.get_json(force=True) or {}
    gross = num(d.get("gross"), None)
    tare = num(d.get("tare_g"), None) if d.get("tare_g") not in (None, "") else (sp["tare_g"] or known_tare(sp["brand"], _kind_of(sp["material_id"])))
    if gross is None or gross < 0:
        return jsonify(error="peso no válido"), 400
    if tare is None:
        return jsonify(error="falta el peso de la bobina vacía de esta marca"), 400
    target = max(0.0, gross - tare)
    delta = target - spool_remaining(sid)
    db = get_db()
    if not sp["tare_g"]:
        db.execute("UPDATE spools SET tare_g=? WHERE id=?", (tare, sid))
    db.execute("INSERT INTO stock_moves(date,material_id,delta,reason,note,spool_id) VALUES(?,?,?,?,?,?)",
               (date.today().isoformat(), sp["material_id"], round(delta, 1), "pesada",
                f"Pesada {gross:g} g − vacía {tare:g} g", sid))
    if sp["status"] == "cerrada" and target < (sp["net_g"] or 0) - 5:
        db.execute("UPDATE spools SET status='abierta' WHERE id=?", (sid,))
    db.commit()
    return jsonify(spool_out(one("SELECT * FROM spools WHERE id=?", (sid,))))


@app.post("/api/spools/<int:sid>/finish")
@login_required
def finish_spool(sid):
    """Bobina gastada (o a borrar). Si pesas la bobina vacía, se apunta para esa marca y material."""
    sp = one("SELECT * FROM spools WHERE id=?", (sid,))
    if not sp:
        return jsonify(error="no existe"), 404
    d = request.get_json(force=True) or {}
    empty = num(d.get("empty_g"), None) if d.get("empty_g") not in (None, "") else None
    db = get_db()
    if empty:
        if empty <= 0 or empty > 2000:
            return jsonify(error="peso no válido"), 400
        learn_tare(sp["brand"], _kind_of(sp["material_id"]), empty)
        db.execute("UPDATE spools SET tare_g=? WHERE id=?", (empty, sid))
    if d.get("delete"):
        db.execute("DELETE FROM stock_moves WHERE spool_id=? AND reason!='pedido' AND reason!='fallo'", (sid,))
        db.execute("UPDATE stock_moves SET spool_id=NULL WHERE spool_id=?", (sid,))
        db.execute("DELETE FROM spools WHERE id=?", (sid,))
    else:
        rem = spool_remaining(sid)
        if rem:
            db.execute("INSERT INTO stock_moves(date,material_id,delta,reason,note,spool_id) VALUES(?,?,?,?,?,?)",
                       (date.today().isoformat(), sp["material_id"], -rem, "gastada", "Bobina gastada", sid))
        db.execute("UPDATE spools SET status='gastada', finished=? WHERE id=?", (date.today().isoformat(), sid))
    db.commit()
    return jsonify(ok=True, learned=bool(empty and sp["brand"]))


@app.get("/api/spool-tares")
@login_required
def list_tares():
    return jsonify(rows("SELECT * FROM spool_tares ORDER BY brand, kind"))


@app.put("/api/spool-tares")
@login_required
def set_tare():
    d = request.get_json(force=True) or {}
    brand, kind, tare = str(d.get("brand", "")).strip().lower(), str(d.get("kind", "")).strip().lower(), num(d.get("tare_g"), 0)
    if not brand or tare <= 0:
        return jsonify(error="marca y peso obligatorios"), 400
    if d.get("delete"):
        get_db().execute("DELETE FROM spool_tares WHERE brand=? AND kind=?", (brand, kind))
    else:
        get_db().execute("""INSERT INTO spool_tares(brand,kind,tare_g,samples,updated) VALUES(?,?,?,1,?)
                            ON CONFLICT(brand,kind) DO UPDATE SET tare_g=excluded.tare_g, updated=excluded.updated""",
                         (brand, kind, tare, date.today().isoformat()))
    get_db().commit()
    return jsonify(ok=True)


def color_distance(a, b):
    """Distancia aproximada entre colores (fórmula «redmean»): <40 casi igual, <90 parecido."""
    a, b = _hex(a), _hex(b)
    if not a or not b:
        return 999
    r1, g1, b1 = (int(a[i:i + 2], 16) for i in (1, 3, 5))
    r2, g2, b2 = (int(b[i:i + 2], 16) for i in (1, 3, 5))
    rm = (r1 + r2) / 2
    return round(math.sqrt((2 + rm / 256) * (r1 - r2) ** 2 + 4 * (g1 - g2) ** 2 + (2 + (255 - rm) / 256) * (b1 - b2) ** 2) / 3, 1)


@app.post("/api/spools/match")
@login_required
def match_spools():
    """¿Lo puedo imprimir con lo que tengo? Para cada color/material necesario, las bobinas que valen."""
    needs = (request.get_json(force=True) or {}).get("needs") or []
    spools = [spool_out(sp) for sp in rows("SELECT * FROM spools WHERE status!='gastada'")]
    out = []
    for n in needs[:16]:
        kind = str(n.get("kind", "")).strip().lower()
        grams = num(n.get("grams"), 0)
        cands = []
        for sp in spools:
            same_kind = not kind or sp["kind"].lower() == kind or kind in sp["material"].lower()
            dist = color_distance(n.get("color_hex"), sp["color_hex"])
            if not n.get("color_hex") and n.get("color_name"):
                dist = 0 if n["color_name"].strip().lower() in sp["color_name"].lower() else 999
            if dist > 120:
                continue
            cands.append({"spool_id": sp["id"], "material": sp["material"], "brand": sp["brand"], "color_name": sp["color_name"],
                          "color_hex": sp["color_hex"], "remaining": sp["remaining"], "location": sp["location"],
                          "distance": dist, "same_kind": same_kind, "enough": sp["remaining"] >= grams})
        cands.sort(key=lambda c: (not c["same_kind"], c["distance"] > 45, not c["enough"], c["distance"], -c["remaining"]))
        best = cands[0] if cands else None
        ok = bool(best and best["same_kind"] and best["distance"] <= 45 and best["enough"])
        out.append({"need": n, "ok": ok, "close": bool(best and best["distance"] <= 90 and best["same_kind"]), "candidates": cands[:4]})
    return jsonify(all_ok=bool(out) and all(x["ok"] for x in out), results=out)


# ---------------------------------------------------------------- fallos de impresión
@app.post("/api/orders/<int:oid>/failures")
@login_required
def add_failure(oid):
    """Una impresión falló al X %: se apunta el material, la luz y las horas de máquina perdidas."""
    o = order_full(oid)
    if not o:
        return jsonify(error="no existe"), 404
    d = request.get_json(force=True) or {}
    pct = num(d.get("pct"), -1)
    if not 0 < pct <= 100:
        return jsonify(error="porcentaje no válido (1-100)"), 400
    idx = int(num(d.get("item_index"), 0))
    if not 0 <= idx < len(o["items"]):
        return jsonify(error="línea no válida"), 400
    it = o["items"][idx]
    try:
        cr = json.loads(it["calc_result"]) if it["calc_result"] else None
    except ValueError:
        cr = None
    if not cr:
        return jsonify(error="esa línea no tiene cálculo (se metió a mano): no sé qué gastaba"), 400
    f = pct / 100.0
    b = cr.get("breakdown", {})
    grams = [{"material_id": m.get("material_id"), "name": m.get("name"), "amount": round((m.get("amount") or 0) * f, 1),
              "unit": m.get("unit"), "spool_id": m.get("spool_id")} for m in cr.get("materials", []) if m.get("amount")]
    mat_cost = (b.get("material", 0)) * f
    other = (b.get("electricidad", 0) + b.get("amortizacion", 0) + b.get("mantenimiento", 0)) * f
    db = get_db()
    cur = db.execute("""INSERT INTO print_failures(order_id,description,pct,hours,kwh,grams_json,material_cost,other_cost,cost,cause,printer,created,user)
                        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                     (oid, it["description"], pct, round((cr.get("hours") or 0) * f, 2), round((cr.get("kwh") or 0) * f, 3),
                      json.dumps(grams), round(mat_cost, 2), round(other, 2), round(mat_cost + other, 2),
                      str(d.get("cause", ""))[:200], cr.get("printer") or "", datetime.now().isoformat(timespec="seconds"),
                      session.get("user", "")))
    fid = cur.lastrowid
    db.execute("UPDATE print_failures SET printer_id=? WHERE id=?", (cr.get("printer_id"), fid))
    for g in grams:
        if g["material_id"] and g["amount"]:
            sid = g.get("spool_id") or pick_spool(g["material_id"])
            db.execute("INSERT INTO stock_moves(date,material_id,delta,reason,note,order_id,spool_id,fail_id) VALUES(?,?,?,?,?,?,?,?)",
                       (date.today().isoformat(), g["material_id"], -g["amount"], "fallo", f"Fallo pedido #{oid} al {pct:g} %",
                        oid, sid, fid))
    db.commit()
    return jsonify(one("SELECT * FROM print_failures WHERE id=?", (fid,))), 201


@app.delete("/api/failures/<int:fid>")
@login_required
def delete_failure(fid):
    db = get_db()
    db.execute("DELETE FROM stock_moves WHERE fail_id=?", (fid,))
    db.execute("DELETE FROM print_failures WHERE id=?", (fid,))
    db.commit()
    return jsonify(ok=True)


# ---------------------------------------------------------------- conjuntos (kits)
def kit_detail(kid):
    items = rows("""SELECT k.id, k.product_id, k.qty, k.notes, p.name, p.unit_price, p.unit_cost, p.print_info,
                           (SELECT COUNT(*) FROM files f WHERE f.product_id=p.id) AS files
                    FROM kit_items k JOIN products p ON p.id=k.product_id WHERE k.kit_id=? ORDER BY k.id""", (kid,))
    parts = rows("""SELECT k.*, c.name AS comp_name, c.unit AS comp_unit, c.unit_cost AS comp_cost, c.location_id AS comp_loc
                    FROM kit_parts k LEFT JOIN components c ON c.id=k.component_id WHERE k.kit_id=? ORDER BY k.id""", (kid,))
    for pt in parts:
        if pt["component_id"] and pt["comp_cost"] is not None:
            pt["unit_cost"] = pt["comp_cost"]
            pt["name"] = pt["comp_name"]
            pt["stock"] = _comp_stock(pt["component_id"])
            pt["location"] = _loc_path(pt["comp_loc"]) if pt["comp_loc"] else ""
    pieces_price = sum(i["unit_price"] * i["qty"] for i in items)
    pieces_cost = sum(i["unit_cost"] * i["qty"] for i in items)
    parts_cost = sum((p["unit_cost"] or 0) * (p["qty"] or 0) for p in parts)
    margin = load_settings().get("margin_pct", 30)
    return {"items": items, "parts": parts, "pieces_price": round(pieces_price, 2), "pieces_cost": round(pieces_cost, 2),
            "parts_cost": round(parts_cost, 2), "cost": round(pieces_cost + parts_cost, 2),
            "suggested_price": round(pieces_price + parts_cost * (1 + margin / 100), 2)}


@app.get("/api/products/<int:pid>/kit")
@login_required
def get_kit(pid):
    if not one("SELECT id FROM products WHERE id=?", (pid,)):
        return jsonify(error="no existe"), 404
    return jsonify(kit_detail(pid))


@app.put("/api/products/<int:pid>/kit")
@login_required
def put_kit(pid):
    if not one("SELECT id FROM products WHERE id=?", (pid,)):
        return jsonify(error="no existe"), 404
    d = request.get_json(force=True) or {}
    db = get_db()
    if d.get("items"):
        db.execute("UPDATE products SET kind='conjunto' WHERE id=?", (pid,))
    if "items" in d:
        db.execute("DELETE FROM kit_items WHERE kit_id=?", (pid,))
        for it in d["items"][:60]:
            cp = int(num(it.get("product_id"), 0))
            if cp and cp != pid and one("SELECT id FROM products WHERE id=? AND kind!='conjunto'", (cp,)):
                db.execute("INSERT INTO kit_items(kit_id,product_id,qty,notes) VALUES(?,?,?,?)",
                           (pid, cp, max(1, int(num(it.get("qty"), 1))), str(it.get("notes", ""))[:200]))
    if "parts" in d:
        db.execute("DELETE FROM kit_parts WHERE kit_id=?", (pid,))
        for pt in d["parts"][:60]:
            comp = one("SELECT * FROM components WHERE id=?", (pt.get("component_id"),)) if pt.get("component_id") else None
            name = comp["name"] if comp else str(pt.get("name", "")).strip()
            if name:
                db.execute("INSERT INTO kit_parts(kit_id,name,qty,unit_cost,notes,component_id) VALUES(?,?,?,?,?,?)",
                           (pid, name[:80], num(pt.get("qty"), 1), comp["unit_cost"] if comp else num(pt.get("unit_cost"), 0),
                            str(pt.get("notes", ""))[:200], comp["id"] if comp else None))
    db.commit()
    _refresh_product_cost(pid)
    db.commit()
    return jsonify(kit_detail(pid))


@app.get("/api/products/<int:pid>/bundle")
@login_required
def kit_bundle(pid):
    """Cálculo combinado de un conjunto (para meterlo en un pedido como una sola línea)."""
    k, tot = bundle_calc(pid)
    return jsonify(kit=k, calc_result=tot)


def bundle_calc(pid):
    k = kit_detail(pid)
    tot = {"hours": 0.0, "kwh": 0.0, "cost": 0.0, "breakdown": {}, "materials": [], "units": 1, "printer": "",
           "prep_min": 0, "post_min": 0, "sale_type": load_settings()["sale_type"]}
    for it in k["items"]:
        p = one("SELECT calc_json FROM products WHERE id=?", (it["product_id"],))
        try:
            r = calculate(json.loads(p["calc_json"] or "{}"))
        except (ValueError, TypeError):
            continue
        f = it["qty"] / (r.get("units") or 1)
        tot["hours"] += r["hours"] * f
        tot["kwh"] += (r.get("kwh") or 0) * f
        tot["cost"] += r["cost"] * f
        tot["prep_min"] += (r.get("prep_min") or 0) * f
        tot["post_min"] += (r.get("post_min") or 0) * f
        tot["printer"] = tot["printer"] or r.get("printer") or ""
        tot["vat_pct"] = r.get("vat_pct")
        tot["commission_pct"], tot["commission_fixed"] = r.get("commission_pct", 0), 0
        for kk, v in r["breakdown"].items():
            tot["breakdown"][kk] = tot["breakdown"].get(kk, 0) + v * f
        for m in r["materials"]:
            tot["materials"].append({**m, "amount": (m["amount"] or 0) * f if m.get("amount") is not None else None,
                                     "cost": (m.get("cost") or 0) * f})
    tot["breakdown"]["extras"] = tot["breakdown"].get("extras", 0) + k["parts_cost"]
    tot["cost"] += k["parts_cost"]
    return k, _round_all(tot)


@app.get("/api/products/<int:pid>/download.zip")
@login_required
def product_zip(pid):
    """Todo lo necesario para repetir un producto/conjunto: archivos, fichas, piezas extra e instrucciones."""
    import zipfile
    p = one("SELECT * FROM products WHERE id=?", (pid,))
    if not p:
        return jsonify(error="no existe"), 404
    safe = lambda x: "".join(c if c.isalnum() or c in " ._-" else "_" for c in str(x))[:80].strip() or "pieza"  # noqa: E731
    buf = io.BytesIO()
    lines = [f"# {p['name']}", ""]
    if p.get("description"):
        lines += [p["description"], ""]
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        def add_files(prod_id, folder):
            for f in rows("SELECT * FROM files WHERE product_id=?", (prod_id,)):
                path = os.path.join(FILES_DIR, f["stored"])
                if os.path.exists(path):
                    z.write(path, f"{folder}{safe(f['name'])}")

        def sheet(pi):
            try:
                pi = json.loads(pi or "{}")
            except ValueError:
                pi = {}
            return ", ".join(f"{k}: {v}" for k, v in pi.items() if v)
        add_files(pid, "")
        if p.get("kind") == "conjunto":
            k = kit_detail(pid)
            lines += ["## Piezas impresas", ""]
            for it in k["items"]:
                lines.append(f"- {it['qty']} × **{it['name']}**" + (f" — {it['notes']}" if it["notes"] else ""))
                if sheet(it["print_info"]):
                    lines.append(f"  - Ficha: {sheet(it['print_info'])}")
                add_files(it["product_id"], f"piezas/{safe(it['name'])}/")
            if k["parts"]:
                lines += ["", "## Material extra", ""]
                lines += [f"- {pt['qty']:g} × {pt['name']}" + (f" — {pt['notes']}" if pt["notes"] else "") for pt in k["parts"]]
        elif sheet(p.get("print_info")):
            lines += ["## Ficha de impresión", "", sheet(p["print_info"])]
        if p.get("instructions"):
            lines += ["", "## Instrucciones", "", p["instructions"]]
        z.writestr("LEEME.md", "\n".join(lines) + "\n")
    buf.seek(0)
    return Response(buf.getvalue(), mimetype="application/zip",
                    headers={"Content-Disposition": f"attachment; filename=\"{safe(p['name'])}.zip\""})


# ================================================================ organización: ubicaciones, componentes, recetas
COMP_UNITS = ("ud", "m", "cm", "ml", "g", "par")
LOC_KINDS = ("estantería", "cajonera", "cajón", "caja", "armario", "balda", "otro")


def _loc_path(lid, _seen=None):
    """«Estantería taller › Caja 3» (con protección frente a ciclos)."""
    out, seen = [], set()
    while lid and lid not in seen:
        seen.add(lid)
        r = one("SELECT name, parent_id FROM locations WHERE id=?", (lid,))
        if not r:
            break
        out.append(r["name"])
        lid = r["parent_id"]
    return " › ".join(reversed(out))


def _comp_stock(cid):
    return round(one("SELECT COALESCE(SUM(delta),0) AS s FROM component_moves WHERE component_id=?", (cid,))["s"], 3)


def comp_out(c):
    c["stock"] = _comp_stock(c["id"])
    c["low"] = bool(c["min_stock"] and c["stock"] <= c["min_stock"])
    c["location"] = _loc_path(c["location_id"]) if c["location_id"] else ""
    c["used_in"] = rows("""SELECT DISTINCT p.id, p.name, k.qty FROM kit_parts k JOIN products p ON p.id=k.kit_id
                           WHERE k.component_id=? ORDER BY p.name""", (c["id"],))
    return c


def _comp_move(cid, delta, reason, note="", order_id=None, person=""):
    get_db().execute("INSERT INTO component_moves(component_id,date,delta,reason,note,order_id,person) VALUES(?,?,?,?,?,?,?)",
                     (cid, date.today().isoformat(), round(delta, 4), reason, str(note)[:200], order_id, person))


def _comp_vals(d, cur=None):
    cur = cur or {}
    g_ = lambda k, dflt=None: d[k] if k in d else cur.get(k, dflt)  # noqa: E731
    v = {"name": str(g_("name", "") or "").strip()[:80], "category": str(g_("category", "") or "").strip()[:40],
         "unit": g_("unit", "ud") if g_("unit", "ud") in COMP_UNITS else "ud",
         "pack_qty": max(num(g_("pack_qty", 1), 1) or 1, 0.0001), "pack_price": None if g_("pack_price") in (None, "") else num(g_("pack_price")),
         "min_stock": num(g_("min_stock", 0)), "location_id": g_("location_id") or None,
         "supplier": str(g_("supplier", "") or "").strip()[:60], "url": str(g_("url", "") or "").strip()[:500],
         "notes": str(g_("notes", "") or "")[:500], "active": 1 if g_("active", 1) else 0}
    if v["pack_price"] is not None:
        v["unit_cost"] = round(v["pack_price"] / v["pack_qty"], 4)
    elif "unit_cost" in d:
        v["unit_cost"] = num(d["unit_cost"])
    if v["url"] and not v["url"].startswith(("http://", "https://")):
        v["url"] = ""
    if v["location_id"] and not one("SELECT 1 AS x FROM locations WHERE id=?", (v["location_id"],)):
        v["location_id"] = None
    return v


@app.get("/api/components")
@login_required
def list_components():
    return jsonify([comp_out(c) for c in rows("SELECT * FROM components ORDER BY active DESC, category, name")])


@app.post("/api/components")
@login_required
def add_component():
    d = request.get_json(force=True) or {}
    v = _comp_vals(d)
    if not v["name"]:
        return jsonify(error="ponle nombre al componente"), 400
    v["created"] = datetime.now().isoformat(timespec="seconds")
    cid = get_db().execute(f"INSERT INTO components({','.join(v)}) VALUES({','.join('?' * len(v))})", list(v.values())).lastrowid
    st = num(d.get("stock"), 0)
    if st:
        _comp_move(cid, st, "alta", "Stock inicial", person=session.get("user", ""))
    get_db().commit()
    return jsonify(comp_out(one("SELECT * FROM components WHERE id=?", (cid,)))), 201


@app.put("/api/components/<int:cid>")
@login_required
def edit_component(cid):
    cur = one("SELECT * FROM components WHERE id=?", (cid,))
    if not cur:
        return jsonify(error="no existe"), 404
    v = _comp_vals(request.get_json(force=True) or {}, cur)
    if not v["name"]:
        return jsonify(error="ponle nombre al componente"), 400
    get_db().execute(f"UPDATE components SET {','.join(k + '=?' for k in v)} WHERE id=?", [*v.values(), cid])
    _refresh_costs_for_component(cid)
    get_db().commit()
    return jsonify(comp_out(one("SELECT * FROM components WHERE id=?", (cid,))))


@app.delete("/api/components/<int:cid>")
@login_required
def del_component(cid):
    db = get_db()
    db.execute("UPDATE kit_parts SET component_id=NULL WHERE component_id=?", (cid,))   # la receta conserva el nombre y el coste
    db.execute("DELETE FROM shopping WHERE component_id=? AND status='pendiente'", (cid,))
    db.execute("DELETE FROM components WHERE id=?", (cid,))
    db.commit()
    return jsonify(ok=True)


@app.post("/api/components/<int:cid>/stock")
@login_required
def component_stock(cid):
    """compra: +packs×pack_qty (o qty) y gasto opcional · ajuste: recuento real · uso: −qty."""
    c = one("SELECT * FROM components WHERE id=?", (cid,))
    if not c:
        return jsonify(error="no existe"), 404
    d = request.get_json(force=True) or {}
    mode, user, db = d.get("mode"), session.get("user", ""), get_db()
    if mode == "compra":
        qty = num(d.get("qty"), 0) or num(d.get("packs"), 1) * (c["pack_qty"] or 1)
        if qty <= 0:
            return jsonify(error="¿cuántos han entrado?"), 400
        _comp_move(cid, qty, "compra", d.get("note") or "Compra", person=user)
        paid = num(d.get("paid"), 0)
        if paid > 0:
            cats = load_settings().get("expense_categories") or []
            cat = next((x for x in cats if x.lower().startswith(("compon", "ferret", "materia"))), cats[0] if cats else "Material")
            db.execute("INSERT INTO movements(date,kind,category,concept,amount,person) VALUES(?,?,?,?,?,?)",
                       (date.today().isoformat(), "gasto", cat, f"{qty:g} × {c['name']}", paid, d.get("person", "")))
            if d.get("update_price", True):
                db.execute("UPDATE components SET unit_cost=?, pack_price=? WHERE id=?",
                           (round(paid / qty, 4), round(paid / qty * (c["pack_qty"] or 1), 2), cid))
                _refresh_costs_for_component(cid)
        if d.get("supplier"):
            db.execute("UPDATE components SET supplier=? WHERE id=?", (str(d["supplier"])[:60], cid))
        if d.get("shopping_id"):
            db.execute("UPDATE shopping SET status='comprado', bought_at=? WHERE id=?", (date.today().isoformat(), d["shopping_id"]))
    elif mode == "ajuste":
        real = num(d.get("qty"), None)
        if real is None or real < 0:
            return jsonify(error="pon cuántos hay"), 400
        delta = real - _comp_stock(cid)
        if abs(delta) > 1e-9:
            _comp_move(cid, delta, "ajuste", d.get("note") or "Recuento", person=user)
    elif mode == "uso":
        qty = num(d.get("qty"), 0)
        if qty <= 0:
            return jsonify(error="¿cuántos has usado?"), 400
        _comp_move(cid, -qty, "uso", d.get("note") or "Uso", person=user)
    else:
        return jsonify(error="modo no válido"), 400
    db.commit()
    return jsonify(comp_out(one("SELECT * FROM components WHERE id=?", (cid,))))


@app.get("/api/components/<int:cid>/moves")
@login_required
def component_moves_list(cid):
    return jsonify(rows("SELECT * FROM component_moves WHERE component_id=? ORDER BY id DESC LIMIT 60", (cid,)))


def _sync_components(oid):
    """Componentes que se gastan en un pedido (receta de cada producto × unidades), como el filamento:
    se recalcula entero cada vez. Las ventas de puesto no gastan: salen de producto ya fabricado."""
    db = get_db()
    db.execute("DELETE FROM component_moves WHERE order_id=? AND reason='pedido'", (oid,))
    o = one("SELECT status, source FROM orders WHERE id=?", (oid,))
    if not o or o["status"] not in STOCK_STATES or o["source"] == "puesto":
        return
    need = {}
    for it in rows("SELECT product_id, qty FROM order_items WHERE order_id=? AND product_id IS NOT NULL", (oid,)):
        for cid, q in _bom_components(it["product_id"]).items():
            need[cid] = need.get(cid, 0) + q * (it["qty"] or 0)
    for cid, q in need.items():
        if q:
            _comp_move(cid, -q, "pedido", f"Pedido #{oid}", order_id=oid)


def _bom_components(pid, _depth=0):
    """{component_id: cantidad por unidad} de un producto, sumando las piezas de un conjunto."""
    out = {}
    if _depth > 3:
        return out
    for pt in rows("SELECT component_id, qty FROM kit_parts WHERE kit_id=? AND component_id IS NOT NULL", (pid,)):
        out[pt["component_id"]] = out.get(pt["component_id"], 0) + (pt["qty"] or 0)
    for it in rows("SELECT product_id, qty FROM kit_items WHERE kit_id=?", (pid,)):
        for cid, q in _bom_components(it["product_id"], _depth + 1).items():
            out[cid] = out.get(cid, 0) + q * (it["qty"] or 1)
    return out


def _parts_cost(pid):
    """Coste por unidad de los componentes y el material extra de la receta (sin las piezas impresas)."""
    tot = 0.0
    for pt in rows("""SELECT k.qty, k.unit_cost, c.unit_cost AS cc FROM kit_parts k
                      LEFT JOIN components c ON c.id=k.component_id WHERE k.kit_id=?""", (pid,)):
        tot += (pt["qty"] or 0) * (pt["cc"] if pt["cc"] is not None else (pt["unit_cost"] or 0))
    return round(tot, 4)


def calc_product(p):
    """Cálculo de una pieza con sus componentes como «otros gastos» (así llevan margen e IVA como el resto)."""
    cj = json.loads(p["calc_json"] or "{}")
    pc = _parts_cost(p["id"])
    if pc:
        units = max(1, int(num(cj.get("units"), 1) or 1))
        cj = {**cj, "extras": [*(cj.get("extras") or []), {"concept": "Componentes", "amount": round(pc * units, 4)}]}
    return calculate(cj)


def _refresh_costs_for_component(cid):
    """Al cambiar el coste de un componente, actualiza el coste de los productos que lo llevan."""
    for r in rows("SELECT DISTINCT kit_id FROM kit_parts WHERE component_id=?", (cid,)):
        _refresh_product_cost(r["kit_id"])


def _refresh_product_cost(pid):
    p = one("SELECT * FROM products WHERE id=?", (pid,))
    if not p:
        return
    if p.get("kind") == "conjunto":
        get_db().execute("UPDATE products SET unit_cost=? WHERE id=?", (kit_detail(pid)["cost"], pid))
        return
    try:
        r = calc_product(p)
    except (ValueError, TypeError):
        return
    if r["hours"] or r["materials"] or _parts_cost(pid):
        get_db().execute("UPDATE products SET unit_cost=? WHERE id=?", (r["cost_unit"], pid))


# ---------------------------------------------------------------- ubicaciones
@app.get("/api/locations")
@login_required
def list_locations():
    out = rows("SELECT * FROM locations ORDER BY name")
    for l_ in out:
        l_["path"] = _loc_path(l_["id"])
        l_["n_components"] = one("SELECT COUNT(*) AS n FROM components WHERE location_id=? AND active=1", (l_["id"],))["n"]
        l_["n_spools"] = one("SELECT COUNT(*) AS n FROM spools WHERE location_id=? AND status!='gastada'", (l_["id"],))["n"]
        l_["n_products"] = one("SELECT COUNT(*) AS n FROM products WHERE location_id=?", (l_["id"],))["n"]
        l_["n_children"] = sum(1 for x in out if x["parent_id"] == l_["id"])
    out.sort(key=lambda x: x["path"].lower())
    return jsonify(out)


def _loc_vals(d, cur=None, lid=None):
    cur = cur or {}
    name = str(d.get("name", cur.get("name", "")) or "").strip()[:60]
    parent = d.get("parent_id", cur.get("parent_id")) or None
    if parent:
        parent = int(num(parent, 0)) or None
    if parent and (parent == lid or not one("SELECT 1 AS x FROM locations WHERE id=?", (parent,))):
        parent = None
    if parent and lid:   # que una caja no acabe dentro de sí misma
        p, seen = parent, set()
        while p and p not in seen:
            if p == lid:
                return None, "no puede ir dentro de sí misma"
            seen.add(p)
            p = (one("SELECT parent_id FROM locations WHERE id=?", (p,)) or {}).get("parent_id")
    kind = d.get("kind", cur.get("kind", "caja"))
    return {"name": name, "parent_id": parent, "kind": kind if kind in LOC_KINDS else "otro",
            "notes": str(d.get("notes", cur.get("notes", "")) or "")[:300]}, None


@app.post("/api/locations")
@login_required
def add_location():
    v, err = _loc_vals(request.get_json(force=True) or {})
    if err or not v["name"]:
        return jsonify(error=err or "ponle nombre"), 400
    v["created"] = datetime.now().isoformat(timespec="seconds")
    lid = get_db().execute(f"INSERT INTO locations({','.join(v)}) VALUES({','.join('?' * len(v))})", list(v.values())).lastrowid
    get_db().commit()
    return jsonify(id=lid, path=_loc_path(lid)), 201


@app.put("/api/locations/<int:lid>")
@login_required
def edit_location(lid):
    cur = one("SELECT * FROM locations WHERE id=?", (lid,))
    if not cur:
        return jsonify(error="no existe"), 404
    v, err = _loc_vals(request.get_json(force=True) or {}, cur, lid)
    if err or not v["name"]:
        return jsonify(error=err or "ponle nombre"), 400
    get_db().execute(f"UPDATE locations SET {','.join(k + '=?' for k in v)} WHERE id=?", [*v.values(), lid])
    _sync_spool_location_text(lid)
    get_db().commit()
    return jsonify(id=lid, path=_loc_path(lid))


@app.delete("/api/locations/<int:lid>")
@login_required
def del_location(lid):
    cur = one("SELECT * FROM locations WHERE id=?", (lid,))
    if not cur:
        return jsonify(error="no existe"), 404
    db = get_db()   # lo que había dentro pasa al sitio que la contenía
    for t in ("components", "spools", "products"):
        db.execute(f"UPDATE {t} SET location_id=? WHERE location_id=?", (cur["parent_id"], lid))
    db.execute("UPDATE locations SET parent_id=? WHERE parent_id=?", (cur["parent_id"], lid))
    db.execute("DELETE FROM locations WHERE id=?", (lid,))
    if cur["parent_id"]:
        _sync_spool_location_text(cur["parent_id"])
    db.commit()
    return jsonify(ok=True)


def _sync_spool_location_text(lid):
    """Las bobinas guardan también el nombre del sitio (lo usan las etiquetas y los avisos)."""
    ids = [lid] + [r["id"] for r in rows("SELECT id FROM locations")
                   if lid in _loc_ancestors(r["id"])]
    for i in ids:
        get_db().execute("UPDATE spools SET location=? WHERE location_id=?", (_loc_path(i), i))


def _loc_ancestors(lid):
    out, seen = [], set()
    while lid and lid not in seen:
        seen.add(lid)
        r = one("SELECT parent_id FROM locations WHERE id=?", (lid,))
        lid = r["parent_id"] if r else None
        if lid:
            out.append(lid)
    return out


@app.get("/api/locations/<int:lid>")
@login_required
def location_detail(lid):
    l_ = one("SELECT * FROM locations WHERE id=?", (lid,))
    if not l_:
        return jsonify(error="ese sitio no existe"), 404
    l_["path"] = _loc_path(lid)
    l_["children"] = [{**c, "path": _loc_path(c["id"])} for c in rows("SELECT * FROM locations WHERE parent_id=? ORDER BY name", (lid,))]
    l_["components"] = [comp_out(c) for c in rows("SELECT * FROM components WHERE location_id=? ORDER BY name", (lid,))]
    l_["spools"] = [spool_out(s) for s in rows("SELECT * FROM spools WHERE location_id=? AND status!='gastada' ORDER BY id", (lid,))]
    l_["products"] = rows("SELECT id, name, stock, image FROM products WHERE location_id=? ORDER BY name", (lid,))
    return jsonify(l_)


@app.put("/api/spools/<int:sid>/location")
@login_required
def spool_set_location(sid):
    lid = (request.get_json(force=True) or {}).get("location_id") or None
    if lid and not one("SELECT 1 AS x FROM locations WHERE id=?", (lid,)):
        return jsonify(error="ese sitio no existe"), 400
    get_db().execute("UPDATE spools SET location_id=?, location=? WHERE id=?", (lid, _loc_path(lid) if lid else "", sid))
    get_db().commit()
    return jsonify(ok=True)


@app.get("/labels/locations")
@login_required
def location_labels():
    ids = [int(x) for x in (request.args.get("ids") or "").split(",") if x.strip().isdigit()][:200]
    locs = [one("SELECT * FROM locations WHERE id=?", (i,)) for i in ids]
    size = request.args.get("size") if request.args.get("size") in LABEL_SIZES else "a4"
    base, cards = _base_url(), []
    for l_ in [x for x in locs if x]:
        svg = _qr_svg(f"{base}/#loc={l_['id']}", 4) or "<div>QR</div>"
        sub = _loc_path(l_["parent_id"]) if l_["parent_id"] else l_["kind"].capitalize()
        cards.append(f"""<div class="lb"><div class="qr">{svg}</div><div class="tx">
          <div class="b big">{html_esc(l_['name'])}</div><div class="m">{html_esc(sub)}</div></div></div>""")
    return _label_page(cards, size, "locations")


# ---------------------------------------------------------------- receta: ¿qué me falta para hacer N?
def _bom_materials(pid, _depth=0):
    """{material_id: cantidad por unidad} de filamento/resina de un producto (de su cálculo o de sus piezas)."""
    out = {}
    p = one("SELECT * FROM products WHERE id=?", (pid,))
    if not p or _depth > 3:
        return out
    if p.get("kind") == "conjunto":
        for it in rows("SELECT product_id, qty FROM kit_items WHERE kit_id=?", (pid,)):
            for mid, q in _bom_materials(it["product_id"], _depth + 1).items():
                out[mid] = out.get(mid, 0) + q * (it["qty"] or 1)
        return out
    try:
        cj = json.loads(p["calc_json"] or "{}")
        r = calculate(cj)
    except (ValueError, TypeError):
        return out
    units = r.get("units") or 1
    by_name = {m["name"]: m["id"] for m in rows("SELECT id,name FROM materials")}
    for ml in r.get("materials", []):
        mid = ml.get("material_id") or by_name.get(ml.get("name"))
        if mid and ml.get("amount"):
            out[mid] = out.get(mid, 0) + ml["amount"] / units
    return out


def product_needs(pid, qty, variant_id=None):
    p = one("SELECT * FROM products WHERE id=?", (pid,))
    mats = _bom_materials(pid)
    if variant_id:   # una variante puede usar otro material (otro color): sustituye al principal
        va = one("SELECT * FROM product_variants WHERE id=? AND product_id=?", (variant_id, pid))
        if va and va["material_id"] and mats:
            main = max(mats, key=mats.get)
            mats[va["material_id"]] = mats.get(va["material_id"], 0) + mats.pop(main)
    lines, ms = [], {m["id"]: m for m in materials_with_stock()}
    for mid, per in mats.items():
        m = ms.get(mid)
        if not m:
            continue
        have = m["stock_level"]
        need = round(per * qty, 1)
        lines.append({"type": "material", "id": mid, "name": m["name"], "unit": m["unit"], "per_unit": round(per, 2),
                      "need": need, "have": None if have is None else round(have, 1),
                      "missing": None if have is None else round(max(0, need - have), 1), "pack": m["qty"], "price": m["price"]})
    for cid, per in _bom_components(pid).items():
        c = one("SELECT * FROM components WHERE id=?", (cid,))
        if not c:
            continue
        have, need = _comp_stock(cid), round(per * qty, 3)
        lines.append({"type": "component", "id": cid, "name": c["name"], "unit": c["unit"], "per_unit": per, "need": need,
                      "have": have, "missing": round(max(0, need - have), 3), "pack": c["pack_qty"], "price": c["pack_price"],
                      "location": _loc_path(c["location_id"]) if c["location_id"] else ""})
    free = rows("SELECT name, qty, notes FROM kit_parts WHERE kit_id=? AND component_id IS NULL", (pid,))
    pieces = rows("""SELECT p.id, p.name, k.qty FROM kit_items k JOIN products p ON p.id=k.product_id WHERE k.kit_id=?""", (pid,))
    ok = all((x["missing"] or 0) <= 0 for x in lines)
    return {"product": {"id": p["id"], "name": p["name"], "stock": p["stock"]}, "qty": qty, "lines": lines,
            "untracked": [{"name": f["name"], "need": (f["qty"] or 0) * qty, "notes": f["notes"]} for f in free],
            "pieces": [{**x, "need": x["qty"] * qty} for x in pieces], "ok": ok}


@app.get("/api/products/<int:pid>/needs")
@login_required
def get_product_needs(pid):
    if not one("SELECT 1 AS x FROM products WHERE id=?", (pid,)):
        return jsonify(error="no existe"), 404
    qty = max(1, min(10000, int(num(request.args.get("qty"), 1))))
    return jsonify(product_needs(pid, qty, request.args.get("variant_id") or None))


@app.post("/api/products/<int:pid>/needs/shop")
@login_required
def product_needs_to_shop(pid):
    """Manda a la lista de la compra lo que falta (en envases enteros). Si ya estaba apuntado, suma."""
    d = request.get_json(force=True) or {}
    nd = product_needs(pid, max(1, int(num(d.get("qty"), 1))), d.get("variant_id") or None)
    added, db = [], get_db()
    for ln in nd["lines"]:
        if not ln["missing"]:
            continue
        packs = max(1, math.ceil(ln["missing"] / (ln["pack"] or 1)))
        col = "material_id" if ln["type"] == "material" else "component_id"
        ex = one(f"SELECT * FROM shopping WHERE {col}=? AND status='pendiente'", (ln["id"],))
        if ex:
            if ex["units"] < packs:
                db.execute("UPDATE shopping SET units=? WHERE id=?", (packs, ex["id"]))
        else:
            lp = _last_price(ln["id"]) if ln["type"] == "material" else None
            est = round(lp["total"] / (lp["units"] or 1), 2) if lp else ln["price"]
            sup = lp["supplier"] if lp else (one("SELECT supplier FROM components WHERE id=?", (ln["id"],)) or {}).get("supplier", "") \
                if ln["type"] == "component" else ""
            db.execute(f"INSERT INTO shopping({col},units,supplier,est_price,note,created) VALUES(?,?,?,?,?,?)",
                       (ln["id"], packs, sup or "", est, f"Para {nd['qty']} × {nd['product']['name']}"[:200],
                        datetime.now().isoformat(timespec="seconds")))
        added.append(ln["name"])
    db.commit()
    return jsonify(added=added)


# ---------------------------------------------------------------- reposición de producto terminado
@app.get("/api/restock")
@login_required
def restock():
    out = []
    for p in rows("SELECT id, name, stock, min_stock, location_id, image FROM products WHERE min_stock>0 ORDER BY name"):
        st = p["stock"] or 0
        pend = one("""SELECT COALESCE(SUM(i.qty),0) AS n FROM order_items i JOIN orders o ON o.id=i.order_id
                      WHERE o.source='stock' AND o.status NOT IN ('listo','entregado','cancelado') AND i.product_id=?""", (p["id"],))["n"]
        if st + pend < p["min_stock"]:
            out.append({**p, "making": pend, "make": p["min_stock"] - st - pend,
                        "location": _loc_path(p["location_id"]) if p["location_id"] else ""})
    return jsonify(out)


# ---------------------------------------------------------------- Telegram
def tg_send(text, token=None, chat_id=None):
    st = load_settings()
    token, chat_id = token or st.get("telegram_token"), chat_id or st.get("telegram_chat_id")
    if not token or not chat_id:
        raise PrinterError("falta el token del bot o el chat")
    body = json.dumps({"chat_id": chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}).encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read().decode()).get("ok", False)
    except urllib.error.HTTPError as e:
        raise PrinterError({401: "token del bot no válido", 400: "chat no válido (¿has escrito /start al bot?)",
                            403: "el bot no puede escribir en ese chat"}.get(e.code, f"Telegram respondió {e.code}")) from None
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise PrinterError(f"no se pudo contactar con Telegram ({getattr(e, 'reason', e)})") from None


@app.post("/api/telegram/test")
@admin_required
def tg_test():
    try:
        tg_send(f"✅ <b>{html_esc(load_settings().get('shop_name', 'MiTallercito'))}</b>: los avisos de MiTallercito funcionan.")
        return jsonify(ok=True)
    except PrinterError as e:
        return jsonify(ok=False, error=str(e))


@app.get("/api/telegram/chats")
@admin_required
def tg_chats():
    """Chats que han escrito al bot (para no tener que buscar el chat_id a mano)."""
    token = load_settings().get("telegram_token")
    if not token:
        return jsonify(error="pon primero el token del bot"), 400
    try:
        with urllib.request.urlopen(f"https://api.telegram.org/bot{token}/getUpdates", timeout=10) as r:
            ups = json.loads(r.read().decode()).get("result", [])
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
        return jsonify(error=f"no se pudo contactar con Telegram ({getattr(e, 'reason', e)})"), 502
    chats = {}
    for u in ups:
        c = (u.get("message") or u.get("my_chat_member") or u.get("channel_post") or {}).get("chat")
        if c:
            chats[c["id"]] = c.get("title") or " ".join(x for x in (c.get("first_name"), c.get("last_name")) if x) or c.get("username") or str(c["id"])
    return jsonify([{"id": k, "name": v} for k, v in chats.items()])


def html_esc(x):
    return str(x).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _fmt_h(h):
    return f"{h / 24:.1f} días" if h >= 48 else f"{h:.0f} h"


def run_notifications(now=None, send=None):
    try:
        run_recurring((now or datetime.now()).date())
    except Exception:  # noqa: BLE001
        pass
    """Lo lanza el temporizador (mitallercito notify) cada 10 min. Devuelve los mensajes enviados."""
    import time
    st = load_settings()
    if not st.get("telegram_enabled") and send is None:
        get_db().execute("INSERT OR REPLACE INTO settings(key,value) VALUES('notify_last_run',?)",
                         (json.dumps((now or datetime.now()).isoformat(timespec="seconds")),))
        get_db().commit()
        return []
    send = send or tg_send
    now = now or datetime.now()
    db, sent = get_db(), []
    limits = {**DEFAULT_LIMITS, **(st.get("status_limits_h") or {})}
    remind = max(1, num(st.get("remind_hours"), 24)) * 3600
    base = (st.get("public_url") or "").rstrip("/")
    link = lambda oid: f' · <a href="{html_esc(base)}/#order={oid}">abrir</a>' if base else ""  # noqa: E731

    def once(key, text, repeat=False):
        r = one("SELECT * FROM notifications WHERE key=?", (key,))
        if r and (not repeat or time.time() - r["sent_at"] < remind):
            return
        try:
            send(text)
        except PrinterError:
            return
        db.execute("""INSERT INTO notifications(key,sent_at,count) VALUES(?,?,1)
                      ON CONFLICT(key) DO UPDATE SET sent_at=excluded.sent_at, count=count+1""", (key, time.time()))
        db.commit()
        sent.append(text)

    for o in rows("SELECT * FROM orders WHERE status NOT IN ('entregado','cancelado')"):
        what = html_esc(o["client"])
        if st.get("notify_new", True) and o["created"] >= (now - timedelta(days=1)).isoformat():
            items = ", ".join(f"{i['qty']}× {html_esc(i['description'])}" for i in rows("SELECT * FROM order_items WHERE order_id=?", (o["id"],)))
            once(f"new:{o['id']}", f"🆕 Pedido #{o['id']} de <b>{what}</b>: {items or 'sin líneas'}{link(o['id'])}")
        since = o.get("status_since") or o["created"]
        try:
            hours = (now - datetime.fromisoformat(since)).total_seconds() / 3600
        except ValueError:
            hours = 0
        lim = limits.get(o["status"])
        if lim and hours > float(lim):
            once(f"stuck:{o['id']}:{o['status']}:{since}",
                 f"⏰ Pedido #{o['id']} ({what}) lleva <b>{_fmt_h(hours)}</b> en «{o['status']}» (máximo {_fmt_h(float(lim))}){link(o['id'])}",
                 repeat=True)
        if st.get("notify_due", True) and o["due_date"] and o["status"] != "presupuesto":
            days = (date.fromisoformat(o["due_date"]) - now.date()).days
            if days < 0:
                once(f"late:{o['id']}:{o['due_date']}", f"🔴 Pedido #{o['id']} ({what}) tenía que entregarse el {o['due_date']} y está en «{o['status']}»{link(o['id'])}", repeat=True)
            elif days <= 1 and o["status"] not in ("listo",):
                once(f"due:{o['id']}:{o['due_date']}", f"📅 Pedido #{o['id']} ({what}) se entrega {'hoy' if days == 0 else 'mañana'} y está en «{o['status']}»{link(o['id'])}")
    if st.get("notify_maint", True):
        for m in maint_all(sync=True):
            for t in m["tasks"]:
                if t["state"] == "toca":
                    once(f"maint:{t['id']}:{t['last_done']}", f"🔧 <b>{html_esc(m['name'])}</b>: toca «{html_esc(t['name'])}» "
                         f"({t['hours_since']:g} h · {t['prints_since']} impresiones · {t['days_since'] or 0} días desde la última vez)", repeat=True)
    if st.get("notify_low_stock", True):
        for m in forecast(now)["materials"]:
            if m["status"] == "falta":
                once(f"fc:{m['id']}:{now.date().isoformat()[:7]}", f"🧵 No llega <b>{html_esc(m['name'])}</b> para los pedidos pendientes: "
                     f"faltan {-m['left']:g} {m['unit']} (compra {m['buy_units']})")
            elif m["status"] == "comprar" and m["days_left"] is not None:
                once(f"fc:{m['id']}:{now.date().isoformat()[:7]}", f"🛒 <b>{html_esc(m['name'])}</b> se acaba en unos {m['days_left']} días "
                     f"al ritmo actual: conviene comprar {m['buy_units']}")
        for m in materials_with_stock():
            if m["active"] and m["stock_low"]:
                once(f"low:{m['id']}:{now.date().isoformat()[:7]}", f"🧵 Queda poco <b>{html_esc(m['name'])}</b>: {m['stock_level']:g} {m['unit']}")
    # para que la web sepa si el temporizador está funcionando
    db.execute("INSERT OR REPLACE INTO settings(key,value) VALUES('notify_last_run',?)", (json.dumps(now.isoformat(timespec="seconds")),))
    db.commit()
    return sent


# ---------------------------------------------------------------- contabilidad
@app.get("/api/movements")
@login_required
def list_movements():
    q, args = "SELECT * FROM movements WHERE 1=1", []
    if request.args.get("year"):
        q += " AND substr(date,1,4)=?"
        args.append(request.args["year"])
    if request.args.get("month"):
        q += " AND substr(date,6,2)=?"
        args.append(request.args["month"].zfill(2))
    return jsonify(rows(q + " ORDER BY date DESC, id DESC", args))


@app.post("/api/movements")
@login_required
def create_movement():
    d = request.get_json(force=True) or {}
    if d.get("kind") not in ("ingreso", "gasto") or num(d.get("amount")) <= 0:
        return jsonify(error="tipo o importe no válido"), 400
    cur = get_db().execute(
        "INSERT INTO movements(date,kind,category,concept,amount,person) VALUES(?,?,?,?,?,?)",
        (d.get("date") or date.today().isoformat(), d["kind"], d.get("category", ""),
         d.get("concept", ""), num(d["amount"]), d.get("person", "")))
    get_db().commit()
    return jsonify(one("SELECT * FROM movements WHERE id=?", (cur.lastrowid,))), 201


@app.put("/api/movements/<int:mid>")
@login_required
def update_movement(mid):
    d = request.get_json(force=True) or {}
    f = {k: d[k] for k in ("date", "kind", "category", "concept", "amount", "person") if k in d}
    if "amount" in f:
        f["amount"] = num(f["amount"])
    if f:
        get_db().execute(f"UPDATE movements SET {','.join(k + '=?' for k in f)} WHERE id=?", [*f.values(), mid])
        get_db().commit()
    return jsonify(one("SELECT * FROM movements WHERE id=?", (mid,)))


@app.delete("/api/movements/<int:mid>")
@login_required
def delete_movement(mid):
    get_db().execute("DELETE FROM movements WHERE id=?", (mid,))
    get_db().commit()
    return jsonify(ok=True)


@app.get("/api/summary")
@login_required
def summary():
    run_recurring()
    year = request.args.get("year") or str(date.today().year)
    months = rows("""
        SELECT substr(date,1,7) AS month,
               ROUND(SUM(CASE WHEN kind='ingreso' THEN amount ELSE 0 END),2) AS ingresos,
               ROUND(SUM(CASE WHEN kind='gasto' THEN amount ELSE 0 END),2) AS gastos
        FROM movements WHERE substr(date,1,4)=? GROUP BY month ORDER BY month""", (year,))
    for m in months:
        m["beneficio"] = round(m["ingresos"] - m["gastos"], 2)
    cats = rows("""SELECT kind, category, ROUND(SUM(amount),2) AS total FROM movements
                   WHERE substr(date,1,4)=? GROUP BY kind, category ORDER BY total DESC""", (year,))
    # Quién ha puesto/cobrado dinero → para cuadrar cuentas entre vosotros
    people = rows("""SELECT person,
               ROUND(SUM(CASE WHEN kind='ingreso' THEN amount ELSE 0 END),2) AS cobrado,
               ROUND(SUM(CASE WHEN kind='gasto' THEN amount ELSE 0 END),2) AS pagado
               FROM movements WHERE substr(date,1,4)=? GROUP BY person""", (year,))
    tot_in = sum(m["ingresos"] for m in months)
    tot_out = sum(m["gastos"] for m in months)
    pending = rows("SELECT id FROM orders WHERE paid=0 AND status NOT IN ('cancelado','presupuesto')")
    pend_total = sum(order_full(r["id"])["total"] for r in pending)
    open_orders = one(f"SELECT COUNT(*) AS n FROM orders WHERE status IN {OPEN_STATUSES}")["n"]
    return jsonify(year=year, months=months, categories=cats, people=people,
                   ingresos=round(tot_in, 2), gastos=round(tot_out, 2),
                   beneficio=round(tot_in - tot_out, 2), pendiente_cobro=round(pend_total, 2),
                   pedidos_abiertos=open_orders)


# ================================================================ mantenimiento de impresoras
# Intervalos de los fabricantes (wikis y manuales oficiales, revisados en noviembre de 2026). Lo marcado
# «orientativo» no lo publica el fabricante: es la práctica habitual. Todo se puede cambiar en cada impresora.
MAINT_PROFILES = {
    "generica": {"name": "FDM genérica (Klipper, Voron, Ender…)", "tasks": [
        ("Limpiar y lubricar ejes y husillos", 200, None, 90, "Habitual cada 200-300 h o cada 1-3 meses (orientativo)"),
        ("Revisar tensión de correas", 200, None, 90, "Orientativo"),
        ("Revisar tornillería, poleas y conectores", 300, None, None, "Orientativo"),
        ("Limpiar ventiladores y restos de plástico", None, None, 30, "Orientativo"),
        ("Revisar tubo PTFE y disipador", 500, None, None, "Orientativo"),
        ("Cambiar boquilla", 750, None, None, "Latón: 500-1000 h; acero endurecido: 2000 h o más"),
    ]},
    "bambu_a1": {"name": "Bambu Lab A1 / A1 mini", "tasks": [
        ("Lubricar la guía del eje Y", 150, None, 30, "Bambu: una vez al mes y cuando la impresora lo pida (≈150 h)"),
        ("Limpiar y lubricar ejes X, Y y Z", 250, None, None, "Cada 200-300 h o si se ven sucios"),
        ("Engrasar husillo(s) Z", None, None, 90, "Bambu: cada 3 meses"),
        ("Lubricar la polea tensora del eje Y", None, None, 90, "Bambu: cada 3 meses"),
        ("Cambiar boquilla", 750, None, None, "Latón: 500-1000 h"),
    ]},
    "bambu_xp": {"name": "Bambu Lab X1 / P1 / P2", "tasks": [
        ("Limpiar varillas de carbono del eje X (sin grasa)", None, None, 30, "Bambu: no lubricar, solo limpiar"),
        ("Limpiar varillas de los ejes Y y Z", None, None, 30, "Bambu: cada mes (con ABS/ASA, cada 5 kg)"),
        ("Antióxido en varillas Y y Z", None, None, 90, "Bambu: cada 3 meses"),
        ("Engrasar husillos Z", None, None, 90, "Bambu: cada 3 meses"),
        ("Cambiar filtro de carbón activo", 720, None, 90, "Bambu: cada 3 meses a ~8 h/día; en producción, cada mes"),
        ("Cambiar boquilla", 750, None, None, "Latón: 500-1000 h"),
    ]},
    "prusa_mk4": {"name": "Prusa MK4/S, MK3.9/S", "tasks": [
        ("Revisión de ejes y lubricación", 200, None, None, "Prusa: cada 200 h de impresión"),
        ("Revisar conectores de la electrónica", 700, None, None, "Prusa: cada 600-800 h"),
        ("Cambiar boquilla", 750, None, None, "Latón: 500-1000 h"),
    ]},
    "prusa_xl": {"name": "Prusa XL", "tasks": [
        ("Inspección y mantenimiento general", 250, None, None, "Prusa: cada ~200-300 h"),
        ("Lubricar husillos Z", 500, None, None, "Prusa: cada ~500 h"),
        ("Revisar placas electrónicas", 700, None, None, "Prusa: cada ~600-800 h"),
    ]},
    "creality_k1": {"name": "Creality K1 / K1C / K1 Max", "tasks": [
        ("Engrasar ejes (zonas indicadas en el manual)", 300, None, None, "Creality: cada 300 h. K1C: no engrasar la varilla de carbono X"),
        ("Revisión general (correas, tornillería, boquilla)", 500, None, None, "Manual: cada 500 h acumuladas"),
        ("Limpiar restos del interior", None, None, 30, "Orientativo"),
    ]},
    "creality_ender3v3": {"name": "Creality Ender-3 V3 / V3 KE", "tasks": [
        ("Lubricar husillos, ejes y guías", 500, None, None, "Creality: cada 500 h acumuladas"),
        ("Revisar correas y excéntricas", 300, None, None, "Orientativo"),
    ]},
    "snapmaker_u1": {"name": "Snapmaker U1", "tasks": [
        ("Limpiar y lubricar varillas ópticas y rodamientos", None, None, 30, "Snapmaker: mensual"),
        ("Limpiar varillas de carbono (sin aceite ni grasa)", None, None, 30, "Snapmaker: mensual, solo limpiar"),
        ("Limpiar y engrasar husillo y tuerca (grasa de litio blanca)", None, None, 90, "Snapmaker: trimestral"),
        ("Limpiar y engrasar pernos y bolas de acero", None, None, 90, "Snapmaker: trimestral"),
        ("Revisar tensión de correas (sin grasa)", None, None, 90, "Orientativo"),
    ]},
    "anycubic_kobra_s1": {"name": "Anycubic Kobra S1", "tasks": [
        ("Engrasar husillo Z y lubricar varillas del eje Y", None, None, 90, "Anycubic (serie Kobra): cada 3 meses, o antes si suena el eje Z"),
        ("Revisar cuchilla del filamento y boquilla", None, None, 30, "Anycubic: revisión periódica"),
        ("Limpiar ventiladores", None, None, 30, "Orientativo"),
        ("Cambiar boquilla", 750, None, None, "Latón: 500-1000 h"),
    ]},
    "elegoo_cc": {"name": "Elegoo Centauri Carbon", "tasks": [
        ("Lubricar ejes", None, None, 90, "Elegoo: cada 3 meses"),
        ("Limpiar ventilador de capa y del disipador", None, None, 30, "Orientativo"),
        ("Revisar el cable del cabezal", 300, None, None, "Orientativo: fallo conocido hacia las 300-350 h"),
    ]},
    "resina": {"name": "Resina (Anycubic Photon, Elegoo Mars/Saturn…)", "tasks": [
        ("Revisar film FEP", None, 15, None, "Cada 10-15 impresiones"),
        ("Cambiar film FEP", None, 40, None, "≈40 impresiones (Anycubic: ~30.000 capas); antes si está rayado o turbio"),
        ("Filtrar resina y limpiar la cuba", None, 10, None, "Orientativo"),
        ("Nivelar la plataforma", None, None, 30, "Orientativo"),
        ("Limpiar el protector de la pantalla LCD", None, None, 30, "Orientativo"),
    ]},
}


def _ts(iso):
    try:
        return datetime.fromisoformat(iso).timestamp() if iso else 0.0
    except ValueError:
        return 0.0


def _import_jobs(pid, jobs):
    """Guarda los trabajos terminados de Moonraker para el contador de horas (sin duplicar)."""
    db = get_db()
    for j in jobs or []:
        st = j.get("status") or ""
        if st in ("in_progress", "") or not j.get("job_id"):
            continue
        db.execute("INSERT OR IGNORE INTO printer_jobs(printer_id,job_id,end_time,hours,prints,status) VALUES(?,?,?,?,1,?)",
                   (pid, str(j["job_id"]), j.get("end_time") or j.get("start_time"), round((j.get("print_duration") or 0) / 3600, 4), st))


_LAST_JOB_SYNC = {}


def sync_printer_jobs(p, timeout=4, force=False):
    """Trae el historial de Moonraker. La primera vez también el total de horas anterior (/server/history/totals)."""
    import time
    if p["conn"] != "moonraker" or not p["host"]:
        return
    if not force and time.time() - _LAST_JOB_SYNC.get(p["id"], 0) < 300:
        return
    _LAST_JOB_SYNC[p["id"]] = time.time()
    first = not one("SELECT 1 AS x FROM printer_jobs WHERE printer_id=?", (p["id"],))
    try:
        jobs = moon(p, "/server/history/list", params={"limit": 500 if first else 50, "order": "desc"}, timeout=timeout).get("jobs", [])
        _import_jobs(p["id"], [{"job_id": j.get("job_id"), "status": j.get("status"), "end_time": j.get("end_time"),
                                "start_time": j.get("start_time"), "print_duration": j.get("print_duration")} for j in jobs])
        if first:
            tot = (moon(p, "/server/history/totals", timeout=timeout).get("job_totals") or {})
            got = one("SELECT COALESCE(SUM(hours),0) AS h, COUNT(*) AS n, MIN(end_time) AS t FROM printer_jobs WHERE printer_id=?", (p["id"],))
            base_h = (tot.get("total_print_time") or 0) / 3600 - got["h"]
            base_n = int(tot.get("total_jobs") or 0) - got["n"]
            if base_h > 0.05:
                get_db().execute("INSERT OR IGNORE INTO printer_jobs(printer_id,job_id,end_time,hours,prints,status) VALUES(?,?,?,?,?,?)",
                                 (p["id"], "__anteriores__", (got["t"] or time.time()) - 1, round(base_h, 3), max(0, base_n), "anteriores"))
        get_db().commit()
    except PrinterError:
        pass


def _hours_mode(p):
    if p.get("hours_source") != "app" and p.get("conn") in ("moonraker", "bridge") and \
            one("SELECT 1 AS x FROM printer_jobs WHERE printer_id=?", (p["id"],)):
        return "moonraker"
    return "app"


def usage_events(p):
    """Horas e impresiones de una impresora en el tiempo: [(timestamp, horas, impresiones, origen)]."""
    import math
    ev = []
    if _hours_mode(p) == "moonraker":
        for j in rows("SELECT end_time, hours, prints FROM printer_jobs WHERE printer_id=?", (p["id"],)):
            ev.append((j["end_time"] or 0, j["hours"] or 0, j["prints"] or 0, "moonraker"))
    else:
        for it in rows(f"""SELECT o.id, o.created, i.qty, i.calc_result FROM order_items i JOIN orders o ON o.id=i.order_id
                           WHERE o.status IN {STOCK_STATES} AND i.calc_result!=''"""):
            try:
                cr = json.loads(it["calc_result"])
            except ValueError:
                continue
            if cr.get("printer_id") != p["id"] or not cr.get("hours"):
                continue
            plates = (it["qty"] or 0) / (cr.get("units") or 1)
            log = one(f"SELECT at FROM order_status_log WHERE order_id=? AND status IN {STOCK_STATES} ORDER BY id LIMIT 1", (it["id"],))
            ev.append((_ts((log or {}).get("at") or it["created"]), cr["hours"] * plates, math.ceil(plates), "pedido"))
        for f in rows("SELECT created, hours, printer_id, printer FROM print_failures WHERE printer_id=? OR (printer_id IS NULL AND printer=?)",
                      (p["id"], p["name"])):
            ev.append((_ts(f["created"]), f["hours"] or 0, 1, "fallo"))
    for a in rows("SELECT at, hours, prints FROM maint_log WHERE printer_id=? AND kind='ajuste'", (p["id"],)):
        ev.append((_ts(a["at"]), a["hours"] or 0, a["prints"] or 0, "ajuste"))
    return ev


def maint_status(p, now=None):
    now = now or datetime.now()
    ev = usage_events(p)
    tasks = []
    for t in rows("SELECT * FROM maint_tasks WHERE printer_id=? ORDER BY sort, id", (p["id"],)):
        since = _ts(t["last_done"])
        h = sum(e[1] for e in ev if e[0] > since)
        n = sum(e[2] for e in ev if e[0] > since)
        days = (now.timestamp() - since) / 86400 if since else None
        parts = []
        if t["every_h"]:
            parts.append(h / t["every_h"])
        if t["every_prints"]:
            parts.append(n / t["every_prints"])
        if t["every_days"] and days is not None:
            parts.append(days / t["every_days"])
        pct = max(parts) if parts else 0
        t.update(hours_since=round(h, 1), prints_since=n, days_since=None if days is None else int(days), pct=round(pct * 100),
                 state="toca" if pct >= 1 else "pronto" if pct >= 0.85 else "ok")
        tasks.append(t)
    return {"id": p["id"], "name": p["name"], "model": p.get("model") or "", "hours_source": p.get("hours_source") or "auto",
            "conn": p.get("conn") or "", "mode": _hours_mode(p), "hours_total": round(sum(e[1] for e in ev), 1),
            "prints_total": int(sum(e[2] for e in ev)), "tasks": tasks,
            "due": sum(1 for t in tasks if t["state"] == "toca"), "soon": sum(1 for t in tasks if t["state"] == "pronto")}


def maint_all(sync=True):
    out = []
    for p in rows("SELECT * FROM printers WHERE active=1 ORDER BY name"):
        if sync:
            sync_printer_jobs(p, timeout=3)
        out.append(maint_status(p))
    return out


def _apply_profile(pid, key, replace=False, last_done=None):
    prof = MAINT_PROFILES.get(key)
    if not prof:
        return False
    db = get_db()
    if replace:
        db.execute("DELETE FROM maint_tasks WHERE printer_id=?", (pid,))
    have = {r["name"] for r in rows("SELECT name FROM maint_tasks WHERE printer_id=?", (pid,))}
    when = last_done or datetime.now().isoformat(timespec="seconds")
    for i, (name, h, n, d, note) in enumerate(prof["tasks"]):
        if name in have:
            continue
        db.execute("""INSERT INTO maint_tasks(printer_id,name,every_h,every_prints,every_days,notes,source,last_done,sort)
                      VALUES(?,?,?,?,?,?,?,?,?)""", (pid, name, h, n, d, note, key, when, i))
    db.execute("UPDATE printers SET model=? WHERE id=?", (key, pid))
    return True


@app.get("/api/maint-profiles")
@login_required
def maint_profiles():
    return jsonify([{"key": k, "name": v["name"], "tasks": [{"name": t[0], "every_h": t[1], "every_prints": t[2], "every_days": t[3],
                                                            "notes": t[4]} for t in v["tasks"]]} for k, v in MAINT_PROFILES.items()])


@app.get("/api/maintenance")
@login_required
def maintenance():
    return jsonify(maint_all(sync=request.args.get("sync", "1") == "1"))


@app.put("/api/printers/<int:pid>/maint")
@admin_required
def maint_printer_cfg(pid):
    d = request.get_json(force=True) or {}
    p = _printer(pid)
    if not p:
        return jsonify(error="no existe"), 404
    db = get_db()
    if "hours_source" in d:
        db.execute("UPDATE printers SET hours_source=? WHERE id=?", ("app" if d["hours_source"] == "app" else "auto", pid))
    if d.get("profile"):
        if not _apply_profile(pid, d["profile"], replace=bool(d.get("replace")), last_done=d.get("last_done") or None):
            return jsonify(error="perfil desconocido"), 400
    db.commit()
    return jsonify(maint_status(_printer(pid)))


@app.post("/api/printers/<int:pid>/maint/tasks")
@admin_required
def maint_add_task(pid):
    d = request.get_json(force=True) or {}
    if not _printer(pid):
        return jsonify(error="no existe"), 404
    if not (d.get("name") or "").strip():
        return jsonify(error="ponle nombre a la tarea"), 400
    f = lambda k: num(d.get(k)) or None  # noqa: E731
    if not (f("every_h") or f("every_prints") or f("every_days")):
        return jsonify(error="pon cada cuántas horas, impresiones o días"), 400
    get_db().execute("""INSERT INTO maint_tasks(printer_id,name,every_h,every_prints,every_days,notes,source,last_done,sort)
                        VALUES(?,?,?,?,?,?,?,?,99)""", (pid, d["name"].strip()[:120], f("every_h"), f("every_prints"), f("every_days"),
                                                     (d.get("notes") or "")[:300], "propia", d.get("last_done") or datetime.now().isoformat(timespec="seconds")))
    get_db().commit()
    return jsonify(maint_status(_printer(pid))), 201


@app.put("/api/maint/tasks/<int:tid>")
@admin_required
def maint_edit_task(tid):
    t = one("SELECT * FROM maint_tasks WHERE id=?", (tid,))
    if not t:
        return jsonify(error="no existe"), 404
    d = request.get_json(force=True) or {}
    vals = {}
    for k in ("every_h", "every_prints", "every_days"):
        if k in d:
            vals[k] = num(d[k]) or None
    for k in ("name", "notes"):
        if k in d:
            vals[k] = str(d[k])[:300]
    if "last_done" in d:
        try:
            vals["last_done"] = datetime.fromisoformat(d["last_done"]).isoformat(timespec="seconds")
        except (TypeError, ValueError):
            return jsonify(error="fecha no válida"), 400
    if vals:
        get_db().execute(f"UPDATE maint_tasks SET {','.join(k + '=?' for k in vals)} WHERE id=?", [*vals.values(), tid])
        get_db().commit()
    return jsonify(maint_status(_printer(t["printer_id"])))


@app.delete("/api/maint/tasks/<int:tid>")
@admin_required
def maint_del_task(tid):
    t = one("SELECT * FROM maint_tasks WHERE id=?", (tid,))
    if not t:
        return jsonify(error="no existe"), 404
    get_db().execute("DELETE FROM maint_tasks WHERE id=?", (tid,))
    get_db().commit()
    return jsonify(maint_status(_printer(t["printer_id"])))


@app.post("/api/maint/tasks/<int:tid>/done")
@login_required
def maint_done(tid):
    t = one("SELECT * FROM maint_tasks WHERE id=?", (tid,))
    if not t:
        return jsonify(error="no existe"), 404
    d = request.get_json(force=True) or {}
    p = _printer(t["printer_id"])
    st = next((x for x in maint_status(p)["tasks"] if x["id"] == tid), {})
    now = datetime.now().isoformat(timespec="seconds")
    db = get_db()
    db.execute("UPDATE maint_tasks SET last_done=? WHERE id=?", (now, tid))
    db.execute("""INSERT INTO maint_log(printer_id,task_id,task_name,kind,at,hours,prints,note,user) VALUES(?,?,?,?,?,?,?,?,?)""",
               (p["id"], tid, t["name"], "hecho", now, st.get("hours_since") or 0, st.get("prints_since") or 0,
                (d.get("note") or "")[:300], session.get("user", "")))
    db.commit()
    return jsonify(maint_status(p))


@app.post("/api/printers/<int:pid>/maint/adjust")
@admin_required
def maint_adjust(pid):
    """Sumar horas a mano: lo que ya llevaba la impresora, impresiones sin pedido…"""
    d = request.get_json(force=True) or {}
    if not _printer(pid):
        return jsonify(error="no existe"), 404
    h, n = num(d.get("hours")), int(num(d.get("prints")))
    if not h and not n:
        return jsonify(error="pon horas o impresiones"), 400
    at = d.get("at") or datetime.now().isoformat()
    get_db().execute("INSERT INTO maint_log(printer_id,kind,at,hours,prints,note,user) VALUES(?,?,?,?,?,?,?)",
                     (pid, "ajuste", at, h, n, (d.get("note") or "")[:300], session.get("user", "")))
    get_db().commit()
    return jsonify(maint_status(_printer(pid)))


@app.get("/api/printers/<int:pid>/maint/log")
@login_required
def maint_log(pid):
    return jsonify(rows("SELECT * FROM maint_log WHERE printer_id=? ORDER BY at DESC, id DESC LIMIT 100", (pid,)))


# ================================================================ clientes
def _client_stats(cid):
    os_ = [order_full(r["id"]) for r in rows("SELECT id FROM orders WHERE client_id=? ORDER BY id DESC", (cid,))]
    real = [o for o in os_ if o["status"] not in ("cancelado", "presupuesto")]
    return os_, {"orders": len(real), "spent": round(sum(o["total"] for o in real if o["paid"]), 2),
                 "owed": round(sum(o["total"] for o in real if not o["paid"]), 2),
                 "last": os_[0]["created"][:10] if os_ else "", "last_order_id": real[0]["id"] if real else None}


@app.get("/api/clients")
@login_required
def list_clients():
    out = []
    for c in rows("SELECT * FROM clients ORDER BY name COLLATE NOCASE"):
        _, stt = _client_stats(c["id"])
        out.append({**c, **stt})
    return jsonify(out)


@app.get("/api/clients/<int:cid>")
@login_required
def get_client(cid):
    c = one("SELECT * FROM clients WHERE id=?", (cid,))
    if not c:
        return jsonify(error="no existe"), 404
    os_, stt = _client_stats(cid)
    for o in os_:
        o.pop("files", None)
        o.pop("status_log", None)
    return jsonify({**c, **stt, "history": os_})


CLIENT_FIELDS = ("name", "phone", "email", "address", "notes")


@app.post("/api/clients")
@login_required
def add_client():
    d = request.get_json(force=True) or {}
    name = (d.get("name") or "").strip()
    if not name:
        return jsonify(error="falta el nombre"), 400
    if one("SELECT 1 AS x FROM clients WHERE lower(trim(name))=lower(?)", (name,)):
        return jsonify(error="ya hay un cliente con ese nombre"), 400
    cid = get_db().execute("INSERT INTO clients(name,phone,email,address,notes,created) VALUES(?,?,?,?,?,?)",
                           (name[:120], *(str(d.get(k) or "")[:300] for k in CLIENT_FIELDS[1:]),
                            datetime.now().isoformat(timespec="seconds"))).lastrowid
    get_db().commit()
    return jsonify(one("SELECT * FROM clients WHERE id=?", (cid,))), 201


@app.put("/api/clients/<int:cid>")
@login_required
def edit_client(cid):
    c = one("SELECT * FROM clients WHERE id=?", (cid,))
    if not c:
        return jsonify(error="no existe"), 404
    d = request.get_json(force=True) or {}
    vals = {k: str(d[k])[:300] for k in CLIENT_FIELDS if k in d}
    if "name" in vals:
        vals["name"] = vals["name"].strip()
        if not vals["name"]:
            return jsonify(error="falta el nombre"), 400
        if one("SELECT 1 AS x FROM clients WHERE lower(trim(name))=lower(?) AND id!=?", (vals["name"], cid)):
            return jsonify(error="ya hay un cliente con ese nombre"), 400
    db = get_db()
    if vals:
        db.execute(f"UPDATE clients SET {','.join(k + '=?' for k in vals)} WHERE id=?", [*vals.values(), cid])
        if "name" in vals:
            db.execute("UPDATE orders SET client=? WHERE client_id=?", (vals["name"], cid))
    db.commit()
    return get_client(cid)


@app.delete("/api/clients/<int:cid>")
@admin_required
def del_client(cid):
    """Borra la ficha; los pedidos se quedan (con el nombre escrito) pero sin enlazar."""
    db = get_db()
    db.execute("UPDATE orders SET client_id=NULL WHERE client_id=?", (cid,))
    db.execute("DELETE FROM clients WHERE id=?", (cid,))
    db.commit()
    return jsonify(ok=True)


# ================================================================ venta en puestos y stock de producto
def _sync_product_stock(oid):
    """Lo fabricado «para stock» suma al stock del producto cuando está listo (y se resta si se cancela)."""
    o = one("SELECT * FROM orders WHERE id=?", (oid,))
    if not o or o["source"] != "stock":
        return
    done = o["status"] in ("listo", "entregado")
    if bool(o["stock_done"]) == done:
        return
    sign = 1 if done else -1
    db = get_db()
    for it in rows("SELECT product_id, variant_id, qty FROM order_items WHERE order_id=? AND product_id IS NOT NULL", (oid,)):
        _stock_add(it["product_id"], it["variant_id"], sign * it["qty"], create=True)
    db.execute("UPDATE orders SET stock_done=? WHERE id=?", (1 if done else 0, oid))


def _undo_product_stock(oid):
    o = one("SELECT * FROM orders WHERE id=?", (oid,))
    if not o:
        return
    if o["source"] == "puesto":
        for it in rows("SELECT product_id, variant_id, qty FROM order_items WHERE order_id=? AND product_id IS NOT NULL", (oid,)):
            _stock_add(it["product_id"], it["variant_id"], it["qty"])
    elif o["source"] == "stock" and o["stock_done"]:
        for it in rows("SELECT product_id, variant_id, qty FROM order_items WHERE order_id=? AND product_id IS NOT NULL", (oid,)):
            _stock_add(it["product_id"], it["variant_id"], -it["qty"], create=True)


def _sale_price(pr):
    return pr["public_price"] if pr.get("public_price") not in (None, "") else pr["unit_price"]


@app.post("/api/sales")
@login_required
def add_sale():
    """Venta en mano (puesto, mercadillo…): cobrada y entregada al momento, normalmente sin cliente."""
    d = request.get_json(force=True) or {}
    lines = []
    for it in d.get("items") or []:
        qty = int(num(it.get("qty"), 1))
        if qty <= 0:
            continue
        pr = one("SELECT * FROM products WHERE id=?", (it.get("product_id"),)) if it.get("product_id") else None
        if pr:
            va = one("SELECT * FROM product_variants WHERE id=? AND product_id=?", (it.get("variant_id"), pr["id"])) if it.get("variant_id") else None
            base = va["price"] if va and va["price"] is not None else _sale_price(pr)
            lines.append({"product_id": pr["id"], "variant_id": va["id"] if va else None,
                          "description": pr["name"] + (f" ({va['name']})" if va else ""), "qty": qty,
                          "unit_price": num(it["unit_price"]) if it.get("unit_price") not in (None, "") else base,
                          "unit_cost": pr["unit_cost"] or 0, "category": pr.get("category") or ""})
        elif (it.get("description") or "").strip():
            lines.append({"description": it["description"].strip()[:120], "qty": qty, "unit_price": num(it.get("unit_price")),
                          "unit_cost": num(it.get("unit_cost"))})
    if not lines:
        return jsonify(error="la venta está vacía"), 400
    if d.get("offers", True):
        for dsc in apply_offers(lines, "puesto"):
            lines.append({"description": f"Oferta: {dsc['name']}", "qty": 1, "unit_price": -dsc["amount"], "offer_id": dsc["offer_id"]})
    ev = one("SELECT * FROM events WHERE id=?", (d.get("event_id"),)) if d.get("event_id") else None
    if d.get("event_id") and not ev:
        return jsonify(error="ese puesto no existe"), 400
    method = d.get("pay_method") if d.get("pay_method") in PAY_METHODS else "efectivo"
    vals = {"client": (d.get("client") or "").strip() or ANON_CLIENT, "client_id": d.get("client_id"), "contact": d.get("contact") or "",
            "email": "", "address": ""}
    _resolve_client(vals)
    now = datetime.now().isoformat(timespec="seconds")
    db = get_db()
    oid = db.execute("""INSERT INTO orders(created,public_token,client,client_id,contact,channel,status,source,event_id,pay_method,
                        paid,paid_to,paid_date,discount,notes,status_since) VALUES(?,?,?,?,?,?,?,?,?,?,1,?,?,?,?,?)""",
                     (now, secrets.token_urlsafe(16), vals["client"], vals["client_id"], vals["contact"],
                      ev["name"] if ev else "En mano", "entregado", "puesto", ev["id"] if ev else None, method,
                      d.get("paid_to") or session.get("user", ""), date.today().isoformat(), num(d.get("discount")),
                      (d.get("notes") or "")[:300], now)).lastrowid
    db.execute("INSERT INTO order_status_log(order_id,status,at,user) VALUES(?,?,?,?)", (oid, "entregado", now, session.get("user", "")))
    _save_items(oid, lines)
    for ln in lines:
        if ln.get("product_id"):
            _stock_add(ln["product_id"], ln.get("variant_id"), -ln["qty"])
    db.commit()
    _sync_payment(oid)
    return jsonify(order_full(oid)), 201


def _event_full(eid):
    ev = one("SELECT * FROM events WHERE id=?", (eid,))
    if not ev:
        return None
    sales = [order_full(r["id"]) for r in rows("SELECT id FROM orders WHERE event_id=? AND status!='cancelado' ORDER BY id DESC", (eid,))]
    by_method, sold = {}, {}
    for o in sales:
        by_method[o["pay_method"] or "otro"] = round(by_method.get(o["pay_method"] or "otro", 0) + o["total"], 2)
        for it in o["items"]:
            if it.get("offer_id"):
                continue
            k = it["product_id"] or it["description"]
            s_ = sold.setdefault(k, {"product_id": it["product_id"], "name": it["description"], "qty": 0, "total": 0})
            s_["qty"] += it["qty"]
            s_["total"] = round(s_["total"] + it["qty"] * it["unit_price"], 2)
    taken = rows("""SELECT es.product_id, es.qty, p.name, p.stock FROM event_stock es JOIN products p ON p.id=es.product_id
                    WHERE es.event_id=? ORDER BY p.name""", (eid,))
    for t in taken:
        t["sold"] = (sold.get(t["product_id"]) or {}).get("qty", 0)
        t["left"] = max(0, t["qty"] - t["sold"])
    total = round(sum(o["total"] for o in sales), 2)
    goods = round(sum(o["cost"] for o in sales), 2)
    ev.update(sales=[{"id": o["id"], "created": o["created"], "client": o["client"], "pay_method": o["pay_method"], "total": o["total"],
                      "paid_to": o["paid_to"], "what": ", ".join(f"{i['qty']}× {i['description']}" for i in o["items"])} for o in sales],
              count=len(sales), total=total, by_method=by_method, goods_cost=goods,
              profit=round(total - goods - (ev["stand_cost"] or 0), 2),
              cash_expected=round((ev["cash_start"] or 0) + by_method.get("efectivo", 0), 2),
              items_sold=sorted(sold.values(), key=lambda x: -x["total"]), taken=taken)
    return ev


def _sync_event_cost(eid):
    ev = one("SELECT * FROM events WHERE id=?", (eid,))
    db = get_db()
    db.execute("DELETE FROM movements WHERE event_id=? AND kind='gasto' AND category='Puestos'", (eid,))
    if ev and (ev["stand_cost"] or 0) > 0:
        db.execute("INSERT INTO movements(date,kind,category,concept,amount,person,event_id) VALUES(?,?,?,?,?,?,?)",
                   (ev["date"] or date.today().isoformat(), "gasto", "Puestos", f"Puesto: {ev['name']}", ev["stand_cost"],
                    session.get("user", ""), eid))


@app.get("/api/events")
@login_required
def list_events():
    out = []
    for e in rows("SELECT id FROM events ORDER BY CASE status WHEN 'abierto' THEN 0 ELSE 1 END, date DESC, id DESC"):
        ev = _event_full(e["id"])
        ev.pop("sales"), ev.pop("items_sold"), ev.pop("taken")
        out.append(ev)
    return jsonify(out)


@app.get("/api/events/<int:eid>")
@login_required
def get_event(eid):
    ev = _event_full(eid)
    return jsonify(ev) if ev else (jsonify(error="no existe"), 404)


EVENT_FIELDS = ("name", "date", "place", "stand_cost", "cash_start", "notes")


@app.post("/api/events")
@login_required
def add_event():
    d = request.get_json(force=True) or {}
    if not (d.get("name") or "").strip():
        return jsonify(error="ponle nombre al puesto"), 400
    eid = get_db().execute("INSERT INTO events(name,date,place,stand_cost,cash_start,notes,created) VALUES(?,?,?,?,?,?,?)",
                           (d["name"].strip()[:120], d.get("date") or date.today().isoformat(), (d.get("place") or "")[:120],
                            num(d.get("stand_cost")), num(d.get("cash_start")), (d.get("notes") or "")[:500],
                            datetime.now().isoformat(timespec="seconds"))).lastrowid
    _sync_event_cost(eid)
    get_db().commit()
    return jsonify(_event_full(eid)), 201


@app.put("/api/events/<int:eid>")
@login_required
def edit_event(eid):
    if not one("SELECT 1 AS x FROM events WHERE id=?", (eid,)):
        return jsonify(error="no existe"), 404
    d = request.get_json(force=True) or {}
    vals = {k: (num(d[k]) if k in ("stand_cost", "cash_start") else str(d[k])[:500]) for k in EVENT_FIELDS if k in d}
    if "status" in d and d["status"] in ("abierto", "cerrado"):
        vals["status"] = d["status"]
    if "cash_end" in d:
        vals["cash_end"] = None if d["cash_end"] in (None, "") else num(d["cash_end"])
    if vals:
        get_db().execute(f"UPDATE events SET {','.join(k + '=?' for k in vals)} WHERE id=?", [*vals.values(), eid])
    _sync_event_cost(eid)
    get_db().commit()
    return jsonify(_event_full(eid))


@app.put("/api/events/<int:eid>/stock")
@login_required
def event_stock(eid):
    """Lo que te llevas al puesto (para saber qué traes de vuelta)."""
    if not one("SELECT 1 AS x FROM events WHERE id=?", (eid,)):
        return jsonify(error="no existe"), 404
    db = get_db()
    db.execute("DELETE FROM event_stock WHERE event_id=?", (eid,))
    for it in (request.get_json(force=True) or {}).get("items") or []:
        q = int(num(it.get("qty")))
        if q > 0 and one("SELECT 1 AS x FROM products WHERE id=?", (it.get("product_id"),)):
            db.execute("INSERT OR REPLACE INTO event_stock(event_id,product_id,qty) VALUES(?,?,?)", (eid, it["product_id"], q))
    db.commit()
    return jsonify(_event_full(eid))


@app.delete("/api/events/<int:eid>")
@admin_required
def del_event(eid):
    db = get_db()
    if one("SELECT 1 AS x FROM orders WHERE event_id=?", (eid,)):
        return jsonify(error="ese puesto tiene ventas: ciérralo en vez de borrarlo"), 400
    db.execute("DELETE FROM movements WHERE event_id=?", (eid,))
    db.execute("DELETE FROM events WHERE id=?", (eid,))
    db.commit()
    return jsonify(ok=True)


@app.post("/api/products/<int:pid>/make")
@login_required
def make_for_stock(pid):
    """Encarga a la cola de impresión unidades de un producto para tener en stock (puestos, tienda…)."""
    pr = one("SELECT * FROM products WHERE id=?", (pid,))
    if not pr:
        return jsonify(error="no existe"), 404
    d = request.get_json(force=True) or {}
    qty = int(num(d.get("qty"), 1))
    if qty <= 0:
        return jsonify(error="cantidad no válida"), 400
    va = one("SELECT * FROM product_variants WHERE id=? AND product_id=?", (d.get("variant_id"), pid)) if d.get("variant_id") else None
    if d.get("variant_id") and not va:
        return jsonify(error="esa variante no existe"), 400
    calc = pr["calc_json"]
    if va and va["material_id"]:
        try:
            cj = json.loads(calc or "{}")
            if cj.get("materials"):
                cj["materials"][0]["material_id"] = va["material_id"]
                cj["materials"][0].pop("spool_id", None)
            calc = json.dumps(cj)
        except ValueError:
            pass
    now = datetime.now().isoformat(timespec="seconds")
    db = get_db()
    oid = db.execute("""INSERT INTO orders(created,public_token,client,channel,status,source,status_since,notes)
                        VALUES(?,?,?,?,?,?,?,?)""", (now, secrets.token_urlsafe(16), STOCK_CLIENT, "Stock", "recibido", "stock", now,
                                                     "Al pasar a «listo» se suma al stock del producto")).lastrowid
    db.execute("INSERT INTO order_status_log(order_id,status,at,user) VALUES(?,?,?,?)", (oid, "recibido", now, session.get("user", "")))
    line = {"product_id": pid, "variant_id": va["id"] if va else None,
            "description": pr["name"] + (f" ({va['name']})" if va else ""), "qty": qty, "unit_price": 0,
            "unit_cost": pr["unit_cost"] or 0, "calc_json": calc, "print_info": pr.get("print_info") or ""}
    if pr.get("kind") == "conjunto":   # un conjunto gasta el material de todas sus piezas
        line["calc_result"] = json.dumps(bundle_calc(pid)[1])
    _save_items(oid, [line])
    _link_product_files(oid)
    db.commit()
    return jsonify(order_full(oid)), 201


# ================================================================ variantes de producto
def _sync_variant_total(pid):
    """Con variantes, el stock del producto es la suma de las suyas (NULL si todas van bajo pedido)."""
    vs = rows("SELECT stock FROM product_variants WHERE product_id=?", (pid,))
    if vs:
        tracked = [v["stock"] for v in vs if v["stock"] is not None]
        get_db().execute("UPDATE products SET stock=? WHERE id=?", (sum(tracked) if tracked else None, pid))


def _stock_add(pid, vid, delta, create=False):
    """Suma (o resta) unidades al stock de un producto o de su variante. create: si no llevaba stock, empieza en 0."""
    db = get_db()
    if vid:
        q = "UPDATE product_variants SET stock=MAX(0, COALESCE(stock,0)+?) WHERE id=?" if create else \
            "UPDATE product_variants SET stock=MAX(0, stock+?) WHERE id=? AND stock IS NOT NULL"
        db.execute(q, (delta, vid))
        _sync_variant_total(pid)
    else:
        q = "UPDATE products SET stock=MAX(0, COALESCE(stock,0)+?) WHERE id=?" if create else \
            "UPDATE products SET stock=MAX(0, stock+?) WHERE id=? AND stock IS NOT NULL"
        db.execute(q, (delta, pid))


@app.get("/api/products/<int:pid>/variants")
@login_required
def get_variants(pid):
    return jsonify(rows("SELECT * FROM product_variants WHERE product_id=? ORDER BY sort, id", (pid,)))


@app.put("/api/products/<int:pid>/variants")
@login_required
def put_variants(pid):
    """Sustituye las variantes. Las que traen id se actualizan (conservan su historial de ventas)."""
    if not one("SELECT 1 AS x FROM products WHERE id=?", (pid,)):
        return jsonify(error="no existe"), 404
    items = (request.get_json(force=True) or {}).get("variants") or []
    db = get_db()
    keep = []
    for i, v in enumerate(items):
        name = str(v.get("name") or "").strip()[:60]
        if not name:
            continue
        price = None if v.get("price") in (None, "") else num(v["price"])
        stock = None if v.get("stock") in (None, "") else int(num(v["stock"]))
        mat = v.get("material_id") or None
        hexc = str(v.get("color_hex") or "")[:9]
        cur = one("SELECT id FROM product_variants WHERE id=? AND product_id=?", (v.get("id"), pid)) if v.get("id") else None
        if cur:
            db.execute("UPDATE product_variants SET name=?, color_hex=?, price=?, stock=?, material_id=?, sort=? WHERE id=?",
                       (name, hexc, price, stock, mat, i, cur["id"]))
            keep.append(cur["id"])
        else:
            keep.append(db.execute("INSERT INTO product_variants(product_id,name,color_hex,price,stock,material_id,sort) VALUES(?,?,?,?,?,?,?)",
                                   (pid, name, hexc, price, stock, mat, i)).lastrowid)
    q = "DELETE FROM product_variants WHERE product_id=?" + (f" AND id NOT IN ({','.join('?' * len(keep))})" if keep else "")
    db.execute(q, (pid, *keep))
    if keep:
        _sync_variant_total(pid)
    db.commit()
    return get_variants(pid)


# ================================================================ packs y ofertas
OFFER_KINDS = ("pack", "nth", "pct")


def _offer_text(o):
    if o["kind"] == "pack":
        return f"{o['qty']} por {o['price']:g} €"
    if o["kind"] == "nth":
        return f"la {o['qty']}ª al {100 - (o['pct'] or 0):g} %" if (o["pct"] or 0) < 100 else f"la {o['qty']}ª gratis"
    return f"−{o['pct']:g} %"


def apply_offers(lines, where):
    """Descuentos de las ofertas activas. Cada unidad entra como mucho en una oferta; se agrupan de la más cara a la
    más barata. Devuelve [{offer_id, name, amount}]."""
    offers = rows("SELECT * FROM offers WHERE active=1 AND applies IN ('todo', ?) ORDER BY id", (where,))
    if not offers:
        return []
    cats = {r["id"]: (r["category"] or "") for r in rows("SELECT id, category FROM products")}
    units = []
    for i, ln in enumerate(lines):
        if not ln.get("product_id") or (ln.get("unit_price") or 0) <= 0:
            continue
        units += [{"line": i, "pid": ln["product_id"], "cat": cats.get(ln["product_id"], ""), "price": ln["unit_price"], "used": False}
                  for _ in range(int(ln.get("qty") or 0))]
    out = []
    for o in offers:
        pool = [u for u in units if not u["used"] and (not o["product_id"] or u["pid"] == o["product_id"])
                and (not o["category"] or u["cat"].lower() == o["category"].lower())]
        pool.sort(key=lambda u: -u["price"])
        disc, n = 0.0, max(1, int(o["qty"] or 1))
        if o["kind"] == "pct":
            for u in pool:
                disc += u["price"] * (o["pct"] or 0) / 100
                u["used"] = True
        else:
            for g in range(len(pool) // n):
                grp = pool[g * n:(g + 1) * n]
                if o["kind"] == "pack":
                    d = sum(u["price"] for u in grp) - (o["price"] or 0)
                else:
                    d = grp[-1]["price"] * (o["pct"] or 0) / 100
                if d > 0.004:
                    disc += d
                    for u in grp:
                        u["used"] = True
        if disc > 0.004:
            out.append({"offer_id": o["id"], "name": f"{o['name']} ({_offer_text(o)})", "amount": round(disc, 2)})
    return out


@app.get("/api/offers")
@login_required
def list_offers():
    out = rows("SELECT o.*, p.name AS product FROM offers o LEFT JOIN products p ON p.id=o.product_id ORDER BY o.active DESC, o.id")
    for o in out:
        o["text"] = _offer_text(o)
    return jsonify(out)


def _offer_vals(d):
    kind = d.get("kind") if d.get("kind") in OFFER_KINDS else "pack"
    v = {"name": str(d.get("name") or "").strip()[:80], "kind": kind, "qty": int(num(d.get("qty"), 2)) or 2,
         "price": None if d.get("price") in (None, "") else num(d["price"]), "pct": None if d.get("pct") in (None, "") else num(d["pct"]),
         "product_id": d.get("product_id") or None, "category": str(d.get("category") or "")[:60],
         "applies": d.get("applies") if d.get("applies") in ("todo", "puesto", "pedidos") else "todo",
         "active": 1 if d.get("active", True) else 0}
    if not v["name"]:
        return None, "ponle nombre a la oferta"
    if kind == "pack" and (v["price"] is None or v["price"] <= 0 or v["qty"] < 2):
        return None, "un pack necesita al menos 2 unidades y un precio"
    if kind == "nth" and (v["pct"] is None or not 0 < v["pct"] <= 100 or v["qty"] < 2):
        return None, "pon desde qué unidad (2 o más) y el % de descuento (1-100)"
    if kind == "pct" and (v["pct"] is None or not 0 < v["pct"] < 100):
        return None, "el descuento tiene que estar entre 1 y 99 %"
    return v, None


@app.post("/api/offers")
@login_required
def add_offer():
    v, err = _offer_vals(request.get_json(force=True) or {})
    if err:
        return jsonify(error=err), 400
    v["created"] = datetime.now().isoformat(timespec="seconds")
    oid = get_db().execute(f"INSERT INTO offers({','.join(v)}) VALUES({','.join('?' * len(v))})", list(v.values())).lastrowid
    get_db().commit()
    return jsonify(one("SELECT * FROM offers WHERE id=?", (oid,))), 201


@app.put("/api/offers/<int:oid>")
@login_required
def edit_offer(oid):
    cur = one("SELECT * FROM offers WHERE id=?", (oid,))
    if not cur:
        return jsonify(error="no existe"), 404
    v, err = _offer_vals({**cur, **(request.get_json(force=True) or {})})
    if err:
        return jsonify(error=err), 400
    get_db().execute(f"UPDATE offers SET {','.join(k + '=?' for k in v)} WHERE id=?", [*v.values(), oid])
    get_db().commit()
    return jsonify(one("SELECT * FROM offers WHERE id=?", (oid,)))


@app.delete("/api/offers/<int:oid>")
@login_required
def del_offer(oid):
    get_db().execute("DELETE FROM offers WHERE id=?", (oid,))
    get_db().commit()
    return jsonify(ok=True)


@app.post("/api/offers/preview")
@login_required
def preview_offers():
    d = request.get_json(force=True) or {}
    lines = [it for it in d.get("items") or [] if not it.get("offer_id")]
    for ln in lines:
        ln["unit_price"], ln["qty"] = num(ln.get("unit_price")), int(num(ln.get("qty"), 1))
    disc = apply_offers(lines, "puesto" if d.get("where") == "puesto" else "pedidos")
    sub = round(sum(ln["qty"] * ln["unit_price"] for ln in lines), 2)
    return jsonify(discounts=disc, subtotal=sub, total=round(sub - sum(x["amount"] for x in disc), 2))


# ================================================================ etiquetas QR de bobinas
def _qr_svg(text, scale=4):
    try:
        import segno
    except ImportError:
        return None
    import io
    buf = io.BytesIO()
    segno.make(text, error="m").save(buf, kind="svg", scale=scale, border=1, xmldecl=False, svgns=True, dark="#000")
    return buf.getvalue().decode()


def _base_url():
    return (load_settings().get("public_url") or request.host_url).rstrip("/")


@app.get("/api/spools/<int:sid>/qr.svg")
@login_required
def spool_qr(sid):
    if not one("SELECT 1 AS x FROM spools WHERE id=?", (sid,)):
        return jsonify(error="no existe"), 404
    svg = _qr_svg(f"{_base_url()}/#spool={sid}", 6)
    if not svg:
        return jsonify(error="falta el módulo segno (se instala al actualizar)"), 500
    return app.response_class(svg, mimetype="image/svg+xml")


LABEL_SIZES = {"a4": ("A4 · 3×8 (70×37 mm)", 70, 37), "62x29": ("62×29 mm (Brother QL)", 62, 29),
               "50x30": ("50×30 mm", 50, 30), "40x30": ("40×30 mm", 40, 30)}


@app.get("/labels/spools")
@login_required
def spool_labels():
    ids = [int(x) for x in (request.args.get("ids") or "").split(",") if x.strip().isdigit()]
    size = request.args.get("size") if request.args.get("size") in LABEL_SIZES else "a4"
    _, w, h = LABEL_SIZES[size]
    st = load_settings()
    base = _base_url()
    sps = rows(f"""SELECT s.*, m.name AS material, m.kind FROM spools s LEFT JOIN materials m ON m.id=s.material_id
                   WHERE s.id IN ({','.join('?' * len(ids)) or 'NULL'}) ORDER BY s.id""", ids)
    cards = []
    for sp in sps:
        svg = _qr_svg(f"{base}/#spool={sp['id']}", 4) or "<div>QR</div>"
        cards.append(f"""<div class="lb"><div class="qr">{svg}</div><div class="tx">
          <div class="b">#{sp['id']} · {html_esc(sp.get('kind') or '')}</div>
          <div class="c"><i style="background:{html_esc(sp['color_hex'] or '#ccc')}"></i>{html_esc(sp['color_name'] or sp.get('material') or '')}</div>
          <div>{html_esc(sp['brand'] or '')} · {sp['net_g']:g} g</div>
          <div class="m">{html_esc(sp['created'][:10])}{(' · ' + html_esc(sp['location'])) if sp['location'] else ''}</div></div></div>""")
    return _label_page(cards, size, "spools")


def _label_page(cards, size, what="spools"):
    """Hoja de etiquetas con QR (A4 o rollo) lista para imprimir."""
    _, w, h = LABEL_SIZES[size]
    st = load_settings()
    titles = {"spools": ("Spool labels", "Etiquetas de bobinas", "No spools selected.", "No hay bobinas seleccionadas."),
              "locations": ("Location labels", "Etiquetas de ubicaciones", "No locations selected.", "No hay ubicaciones seleccionadas.")}[what]
    en = st.get("language") == "en"
    a4 = size == "a4"
    page = "@page{size:A4;margin:12mm 0 0 0}" if a4 else f"@page{{size:{w}mm {h}mm;margin:0}}"
    grid = "display:grid;grid-template-columns:repeat(3,70mm);grid-auto-rows:37mm;justify-content:center" if a4 else ""
    html = f"""<!DOCTYPE html><html lang="{'en' if en else 'es'}"><head><meta charset="utf-8"><title>{titles[0] if en else titles[1]}</title><style>
{page} *{{box-sizing:border-box}} body{{margin:0;font:11px system-ui,sans-serif;color:#000}}
.bar{{padding:10px 14px;background:#f4f3ef;border-bottom:1px solid #ddd;display:flex;gap:10px;align-items:center;font-size:14px}}
.bar button,.bar select{{font:inherit;padding:6px 10px}} @media print{{.bar{{display:none}}}}
.sheet{{{grid}}} .lb{{width:{w}mm;height:{h}mm;display:flex;gap:2mm;align-items:center;padding:2mm 3mm;overflow:hidden;
{'' if a4 else 'page-break-after:always;'}}} .qr{{height:100%;aspect-ratio:1}} .qr svg{{width:100%;height:100%}}
.tx{{flex:1;min-width:0;line-height:1.25}} .big{{font-size:{'17' if h > 30 else '13'}px;line-height:1.1}} .b{{font-weight:700;font-size:{'13' if h > 30 else '11'}px}} .m{{color:#555;font-size:9px}}
.c{{display:flex;align-items:center;gap:4px;font-weight:600}} .c i{{width:9px;height:9px;border-radius:50%;border:1px solid #0003;display:inline-block}}
</style></head><body><div class="bar"><b>{len(cards)} {'label(s)' if en else 'etiqueta(s)'}</b>
<select onchange="location.search=location.search.replace(/size=[^&]*/,'')+(location.search.includes('?')?'&':'?')+'size='+this.value">
{''.join(f'<option value="{k}" {"selected" if k == size else ""}>{v[0]}</option>' for k, v in LABEL_SIZES.items())}</select>
<button onclick="print()">{'Print' if en else 'Imprimir'}</button><span style="color:#666">{html_esc(st.get('shop_name') or 'MiTallercito')}</span></div>
<div class="sheet">{''.join(cards) or ('<p style="padding:20px">' + (titles[2] if en else titles[3]) + '</p>')}</div></body></html>"""
    return app.response_class(html, mimetype="text/html")


# ================================================================ Manyfold (biblioteca de modelos)
# Solo habla el servidor con Manyfold (red interna). El navegador nunca ve Manyfold ni sus credenciales.
_MF_TOKEN = {"token": None, "exp": 0, "key": ""}


class ManyfoldError(Exception):
    pass


def _ua():
    return {"User-Agent": f"MiTallercito/{app_version()} (+https://github.com/Oda615/MiTallercito)"}


def _mf_http_error(e, default):
    """Explica los bloqueos que no son de Manyfold (Cloudflare, proxy inverso…)."""
    try:
        body = e.read(4000).decode("utf-8", "ignore").lower()
    except Exception:  # noqa: BLE001
        body = ""
    srv = (e.headers.get("Server") or "").lower() if e.headers else ""
    if "cloudflare" in srv or "cloudflare" in body or "cf-ray" in {k.lower() for k in (e.headers or {})}:
        return ManyfoldError("Cloudflare está bloqueando la petición (HTTP %d). Pon la dirección interna de Manyfold "
                             "(p. ej. http://192.168.1.20:3214) o crea en Cloudflare una regla que permita /oauth y /models." % e.code)
    if e.code == 403 and ("nginx" in srv or "openresty" in srv or "nginx" in body):
        return ManyfoldError("El proxy inverso (Nginx) deniega el acceso (HTTP 403): revisa la lista de acceso o usa la dirección interna de Manyfold.")
    return ManyfoldError(default)


def _mf_base():
    u = (load_settings().get("manyfold_url") or "").strip().rstrip("/")
    if not u:
        raise ManyfoldError("configura la dirección de Manyfold en Ajustes")
    if not u.startswith(("http://", "https://")):
        u = "http://" + u
    return u


def _mf_token():
    import time
    st = load_settings()
    cid, sec = st.get("manyfold_client_id") or "", st.get("manyfold_client_secret") or ""
    if not cid or not sec:
        return None          # Manyfold con modelos públicos
    key = f"{_mf_base()}|{cid}"
    if _MF_TOKEN["token"] and _MF_TOKEN["key"] == key and time.time() < _MF_TOKEN["exp"] - 60:
        return _MF_TOKEN["token"]
    body = urllib.parse.urlencode({"grant_type": "client_credentials", "client_id": cid, "client_secret": sec,
                                   "scope": "read"}).encode()
    try:
        with urllib.request.urlopen(urllib.request.Request(f"{_mf_base()}/oauth/token", data=body, method="POST",
                                                           headers={"Accept": "application/json", **_ua()}), timeout=10) as r:
            t = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise _mf_http_error(e, "Manyfold ha rechazado las credenciales (revisa el client id/secret y que la aplicación tenga «read»)"
                             if e.code in (400, 401) else f"Manyfold: error HTTP {e.code} al pedir el token") from None
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise ManyfoldError(f"Manyfold no responde ({getattr(e, 'reason', e)})") from None
    _MF_TOKEN.update(token=t.get("access_token"), exp=time.time() + int(t.get("expires_in") or 7200), key=key)
    return _MF_TOKEN["token"]


def _mf_url(path):
    """Ruta o URL de Manyfold → URL absoluta, solo si es del mismo servidor configurado."""
    base = _mf_base()
    u = urllib.parse.urljoin(base + "/", path or "")
    if urllib.parse.urlsplit(u).netloc != urllib.parse.urlsplit(base).netloc:
        raise ManyfoldError("esa dirección no es de tu Manyfold")
    return u


def mf_get_json(path, params=None):
    u = _mf_url(path) + (("?" + urllib.parse.urlencode(params)) if params else "")
    h = {"Accept": "application/vnd.manyfold.v0+json", **_ua()}
    tok = _mf_token()
    if tok:
        h["Authorization"] = f"Bearer {tok}"
    try:
        with urllib.request.urlopen(urllib.request.Request(u, headers=h), timeout=15) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise _mf_http_error(e, {401: "Manyfold pide credenciales: crea una aplicación con permiso «read» y pon su client id/secret",
                             403: "Manyfold no deja ver eso con estas credenciales", 404: "no encontrado en Manyfold",
                             406: "este Manyfold no tiene API (actualízalo a una versión reciente)"}.get(e.code, f"Manyfold: error HTTP {e.code}")) from None
    except (urllib.error.URLError, OSError) as e:
        raise ManyfoldError(f"Manyfold no responde ({getattr(e, 'reason', e)})") from None
    except ValueError:
        raise ManyfoldError("Manyfold no ha devuelto datos de la API (¿versión antigua?)") from None


def mf_download(url, dest, limit=500 * 1024 * 1024):
    """Descarga un archivo de Manyfold a disco. Devuelve (tamaño, sha256)."""
    import hashlib
    h = dict(_ua())
    tok = _mf_token()
    if tok:
        h["Authorization"] = f"Bearer {tok}"
    sha, size = hashlib.sha256(), 0
    try:
        with urllib.request.urlopen(urllib.request.Request(_mf_url(url), headers=h), timeout=60) as r, open(dest, "wb") as out:
            for chunk in iter(lambda: r.read(1024 * 1024), b""):
                size += len(chunk)
                if size > limit:
                    raise ManyfoldError("archivo demasiado grande (más de 500 MB)")
                sha.update(chunk)
                out.write(chunk)
    except urllib.error.HTTPError as e:
        raise _mf_http_error(e, f"no se pudo descargar el archivo (HTTP {e.code})") from None
    except (urllib.error.URLError, OSError) as e:
        raise ManyfoldError(f"no se pudo descargar el archivo ({getattr(e, 'reason', e)})") from None
    return size, sha.hexdigest()


def _mf_id(x):
    return urllib.parse.urlsplit(x or "").path


@app.get("/api/manyfold/search")
@login_required
def mf_search():
    q = (request.args.get("q") or "").strip()
    try:
        d = mf_get_json("/models", {"q": q, "order": "name"} if q else {"order": "recent"})
        base = _mf_base()
    except ManyfoldError as e:
        return jsonify(error=str(e)), 400
    return jsonify(total=d.get("totalItems"), models=[{"id": _mf_id(m.get("@id")), "name": m.get("name") or "",
                                                       "url": urllib.parse.urljoin(base + "/", m.get("@id") or "")}
                                                      for m in d.get("member") or []])


@app.get("/api/manyfold/model")
@login_required
def mf_model():
    try:
        m = mf_get_json(_mf_id(request.args.get("id")))
        base = _mf_base()
    except ManyfoldError as e:
        return jsonify(error=str(e)), 400
    files = [{"id": _mf_id(f.get("@id")), "name": f.get("name") or "", "format": f.get("encodingFormat") or ""}
             for f in m.get("hasPart") or []]
    return jsonify(id=_mf_id(m.get("@id")), name=m.get("name") or "", description=m.get("description") or "",
                   url=urllib.parse.urljoin(base + "/", m.get("@id") or ""), files=files)


@app.post("/api/manyfold/import")
@login_required
def mf_import():
    """Copia archivos de un modelo de Manyfold a un pedido o a un producto del catálogo."""
    d = request.get_json(force=True) or {}
    oid, pid = d.get("order_id"), d.get("product_id")
    if oid and not one("SELECT id FROM orders WHERE id=?", (oid,)):
        return jsonify(error="pedido no existe"), 404
    if pid and not one("SELECT id FROM products WHERE id=?", (pid,)):
        return jsonify(error="producto no existe"), 404
    if not oid and not pid:
        return jsonify(error="¿a qué pedido o producto?"), 400
    os.makedirs(FILES_DIR, exist_ok=True)
    out = []
    try:
        for fid in d.get("file_ids") or []:
            f = mf_get_json(_mf_id(fid))
            name = os.path.basename(str(f.get("name") or "").replace("\\", "/"))[:200] or "modelo"
            # Manyfold da los enlaces con su dominio público aunque le hables por IP: se descarga siempre
            # del servidor configurado, con la misma ruta (así tampoco pasa por Cloudflare ni por el proxy).
            sp = urllib.parse.urlsplit(f.get("contentUrl") or "")
            src = sp.path + (("?" + sp.query) if sp.query else "")
            fn = os.path.basename(urllib.parse.urlsplit(src).path)
            ext = urllib.parse.unquote(fn).rsplit(".", 1)[-1].lower() if "." in fn else ""
            if ext and not name.lower().endswith("." + ext):
                name += "." + ext
            stored = secrets.token_hex(12)
            size, sha = mf_download(src, os.path.join(FILES_DIR, stored))
            fid_new = get_db().execute(
                "INSERT INTO files(order_id,product_id,stored,name,size,sha256,uploaded,uploaded_by,note) VALUES(?,?,?,?,?,?,?,?,?)",
                (oid or None, pid or None, stored, name, size, sha, datetime.now().isoformat(timespec="seconds"),
                 session.get("user"), "de Manyfold")).lastrowid
            out.append(one("SELECT id,name,size,uploaded,uploaded_by,note FROM files WHERE id=?", (fid_new,)))
        if pid and d.get("model_id"):
            get_db().execute("UPDATE products SET manyfold_id=? WHERE id=?", (_mf_id(d["model_id"]), pid))
        get_db().commit()
    except ManyfoldError as e:
        get_db().commit()
        return jsonify(error=str(e), imported=out), 400
    return jsonify(imported=out), 201


@app.get("/api/manyfold/test")
@admin_required
def mf_test():
    try:
        d = mf_get_json("/models", {"order": "recent"})
        return jsonify(ok=True, models=d.get("totalItems"), auth=bool(_mf_token()))
    except ManyfoldError as e:
        return jsonify(ok=False, error=str(e))


# ================================================================ previsión de filamento
COLOR_NAMES = {"negro": "#222222", "black": "#222222", "blanco": "#f2f2f2", "white": "#f2f2f2", "gris": "#8a8a8a", "grey": "#8a8a8a",
               "gray": "#8a8a8a", "rojo": "#c62828", "red": "#c62828", "azul": "#1e5bb8", "blue": "#1e5bb8", "verde": "#3fae6a",
               "green": "#3fae6a", "amarillo": "#f2c200", "yellow": "#f2c200", "naranja": "#ef7d22", "orange": "#ef7d22", "rosa": "#e88fb3",
               "pink": "#e88fb3", "morado": "#7b4bb8", "purple": "#7b4bb8", "marrón": "#7a4e2d", "marron": "#7a4e2d", "brown": "#7a4e2d",
               "dorado": "#c9a227", "gold": "#c9a227", "plata": "#c0c0c0", "silver": "#c0c0c0", "transparente": "#dfe9ee"}


def forecast(now=None):
    """Lo que piden los pedidos aún sin imprimir frente a lo que queda, y a qué ritmo se gasta."""
    import math
    st = load_settings()
    now = now or datetime.now()
    win = max(7, int(num(st.get("forecast_window_days"), 60)))
    lead = max(0, int(num(st.get("forecast_lead_days"), 7)))
    states = ["recibido", "programado"] + (["presupuesto"] if st.get("forecast_quotes") else [])
    pend, pend_orders = {}, {}
    by_name = {m["name"]: m["id"] for m in rows("SELECT id,name FROM materials")}
    for it in rows(f"""SELECT o.id, o.due_date, i.qty, i.calc_result FROM order_items i JOIN orders o ON o.id=i.order_id
                       WHERE o.status IN ({','.join('?' * len(states))}) AND i.calc_result!=''""", states):
        try:
            cr = json.loads(it["calc_result"])
        except ValueError:
            continue
        f = (it["qty"] or 0) / (cr.get("units") or 1)
        for ml in cr.get("materials", []):
            mid = ml.get("material_id") or by_name.get(ml.get("name"))
            if mid and ml.get("amount"):
                pend[mid] = pend.get(mid, 0) + ml["amount"] * f
                pend_orders.setdefault(mid, set()).add(it["id"])
    since = (now - timedelta(days=win)).date().isoformat()
    used = {r["material_id"]: -r["s"] for r in rows(
        "SELECT material_id, SUM(delta) AS s FROM stock_moves WHERE delta<0 AND reason IN ('pedido','fallo') AND date>=? GROUP BY material_id",
        (since,))}
    hexes = {}
    for sp in rows("SELECT material_id, color_hex FROM spools WHERE color_hex!='' ORDER BY status='gastada', id DESC"):
        hexes.setdefault(sp["material_id"], sp["color_hex"])
    out = []
    for m in materials_with_stock():
        if not m["active"] and m["id"] not in pend:
            continue
        stock = m["stock_level"] if m["stock_level"] is not None else None
        p = round(pend.get(m["id"], 0), 1)
        rate = round((used.get(m["id"]) or 0) / win, 1)
        if stock is None and not p:
            continue
        left = None if stock is None else round(stock - p, 1)
        days = None if left is None or rate <= 0 else max(0, int(left / rate))
        need = 0 if stock is None else max(0.0, p + rate * (lead + 30) - stock)
        status = "sin_stock" if stock is None else "falta" if left < 0 else \
            "comprar" if (days is not None and days <= lead) or (m["track_stock"] and left <= (m["low_stock"] or 0)) else "ok"
        cn = (m["color"] or "").strip().lower()
        hx = m["color"] if cn.startswith("#") else COLOR_NAMES.get(cn) or COLOR_NAMES.get(m["name"].split()[-1].lower()) or hexes.get(m["id"], "")
        out.append({"id": m["id"], "name": m["name"], "kind": m["kind"], "color": hx, "unit": m["unit"],
                    "stock": stock, "pending": p, "pending_orders": sorted(pend_orders.get(m["id"], [])), "left": left,
                    "rate_day": rate, "days_left": days,
                    "runs_out": (now + timedelta(days=days)).date().isoformat() if days is not None else None,
                    "buy_units": math.ceil(need / (m["qty"] or 1000)) if need > 0 else 0, "pack": m["qty"] or 1000,
                    "status": status})
    order = {"falta": 0, "comprar": 1, "sin_stock": 2, "ok": 3}
    out.sort(key=lambda x: (order[x["status"]], x["days_left"] if x["days_left"] is not None else 9999, x["name"]))
    return {"lead_days": lead, "window_days": win, "materials": out}


@app.get("/api/forecast")
@login_required
def api_forecast():
    return jsonify(forecast())


# ================================================================ precios, proveedores y lista de la compra
def _record_price(mid, units, unit_qty, total, supplier="", brand="", source=""):
    units, unit_qty = num(units, 1) or 1, num(unit_qty, 1000) or 1000
    m = one("SELECT unit FROM materials WHERE id=?", (mid,))
    per = round(total / units / unit_qty * 1000, 2) if total else None   # €/kg o €/l
    get_db().execute("""INSERT INTO material_prices(material_id,date,supplier,brand,units,unit_qty,total,per_kg,source)
                        VALUES(?,?,?,?,?,?,?,?,?)""", (mid, date.today().isoformat(), supplier, brand, units, unit_qty,
                                                        round(total, 2), per, source + (" (ml)" if m and m["unit"] == "ml" else "")))


def _last_price(mid):
    return one("SELECT * FROM material_prices WHERE material_id=? ORDER BY date DESC, id DESC LIMIT 1", (mid,))


@app.get("/api/materials/<int:mid>/prices")
@login_required
def material_prices(mid):
    hist = rows("SELECT * FROM material_prices WHERE material_id=? ORDER BY date DESC, id DESC", (mid,))
    pk = [h["per_kg"] for h in hist if h["per_kg"]]
    best = {}
    for h in hist:
        if h["per_kg"] and h["supplier"] and (h["supplier"] not in best or h["per_kg"] < best[h["supplier"]]):
            best[h["supplier"]] = h["per_kg"]
    return jsonify(history=hist, min=min(pk) if pk else None, max=max(pk) if pk else None,
                   avg=round(sum(pk) / len(pk), 2) if pk else None,
                   suppliers=sorted(({"supplier": k, "best_per_kg": v} for k, v in best.items()), key=lambda x: x["best_per_kg"]))


@app.get("/api/suppliers")
@login_required
def suppliers():
    return jsonify([r["s"] for r in rows("""SELECT supplier AS s FROM material_prices WHERE supplier!='' UNION
                                             SELECT supplier FROM spools WHERE supplier!='' UNION
                                             SELECT supplier FROM shopping WHERE supplier!='' ORDER BY 1""")])


def _shop_item(it):
    m = one("SELECT name, unit, qty, color FROM materials WHERE id=?", (it["material_id"],)) if it["material_id"] else None
    c = one("SELECT name, unit, pack_qty, url FROM components WHERE id=?", (it["component_id"],)) if it.get("component_id") else None
    it["material"] = m["name"] if m else (c["name"] if c else "")
    it["unit"] = m["unit"] if m else (c["unit"] if c else "")
    it["pack"] = m["qty"] if m else (c["pack_qty"] if c else None)
    it["url"] = c["url"] if c else ""
    it["total"] = round((it["est_price"] or 0) * (it["units"] or 0), 2) if it["est_price"] is not None else None
    return it


@app.get("/api/shopping")
@login_required
def shopping_list():
    items = [_shop_item(r) for r in rows("SELECT * FROM shopping WHERE status='pendiente' ORDER BY supplier, id")]
    done = [_shop_item(r) for r in rows("SELECT * FROM shopping WHERE status='comprado' ORDER BY bought_at DESC, id DESC LIMIT 15")]
    listed = {i["material_id"] for i in items}
    clisted = {i["component_id"] for i in items}
    sugg = []
    for c in rows("SELECT * FROM components WHERE active=1 AND min_stock>0"):
        st = _comp_stock(c["id"])
        if st <= c["min_stock"] and c["id"] not in clisted:
            want = max(c["min_stock"] * 2 - st, c["pack_qty"] or 1)
            sugg.append({"component_id": c["id"], "material": c["name"], "units": max(1, math.ceil(want / (c["pack_qty"] or 1))),
                         "pack": c["pack_qty"], "unit": c["unit"], "reason": f"quedan {st:g}", "supplier": c["supplier"],
                         "est_price": c["pack_price"], "last_date": ""})
    for m in forecast()["materials"]:
        if m["status"] in ("falta", "comprar") and m["buy_units"] and m["id"] not in listed:
            lp = _last_price(m["id"])
            sugg.append({"material_id": m["id"], "material": m["name"], "units": m["buy_units"], "pack": m["pack"], "unit": m["unit"],
                         "reason": "no llega para los pedidos" if m["status"] == "falta" else f"se acaba en {m['days_left']} días",
                         "supplier": lp["supplier"] if lp else "", "est_price": round(lp["total"] / (lp["units"] or 1), 2) if lp else None,
                         "last_date": lp["date"] if lp else ""})
    return jsonify(items=items, done=done, suggestions=sugg,
                   total=round(sum(i["total"] or 0 for i in items), 2))


@app.post("/api/shopping")
@login_required
def shopping_add():
    d = request.get_json(force=True) or {}
    mid = d.get("material_id") or None
    cid = d.get("component_id") or None
    if cid:
        c = one("SELECT * FROM components WHERE id=?", (cid,))
        if not c:
            return jsonify(error="ese componente no existe"), 400
        sid = get_db().execute("INSERT INTO shopping(component_id,units,supplier,est_price,note,created) VALUES(?,?,?,?,?,?)",
                               (cid, num(d.get("units"), 1) or 1, str(d.get("supplier") or c["supplier"] or "")[:60],
                                c["pack_price"] if d.get("est_price") in (None, "") else num(d["est_price"]),
                                str(d.get("note") or "")[:200], datetime.now().isoformat(timespec="seconds"))).lastrowid
        get_db().commit()
        return jsonify(_shop_item(one("SELECT * FROM shopping WHERE id=?", (sid,)))), 201
    if not mid and not (d.get("text") or "").strip():
        return jsonify(error="¿qué hay que comprar?"), 400
    if mid and not one("SELECT 1 AS x FROM materials WHERE id=?", (mid,)):
        return jsonify(error="ese material no existe"), 400
    lp = _last_price(mid) if mid else None
    est = d.get("est_price")
    if est in (None, "") and lp:
        est = round(lp["total"] / (lp["units"] or 1), 2)
    sid = get_db().execute("INSERT INTO shopping(material_id,text,units,supplier,est_price,note,created) VALUES(?,?,?,?,?,?,?)",
                           (mid, str(d.get("text") or "")[:120], num(d.get("units"), 1) or 1,
                            str(d.get("supplier") if d.get("supplier") is not None else (lp["supplier"] if lp else ""))[:60],
                            None if est in (None, "") else num(est), str(d.get("note") or "")[:200],
                            datetime.now().isoformat(timespec="seconds"))).lastrowid
    get_db().commit()
    return jsonify(_shop_item(one("SELECT * FROM shopping WHERE id=?", (sid,)))), 201


@app.put("/api/shopping/<int:sid>")
@login_required
def shopping_edit(sid):
    if not one("SELECT 1 AS x FROM shopping WHERE id=?", (sid,)):
        return jsonify(error="no existe"), 404
    d = request.get_json(force=True) or {}
    vals = {}
    for k in ("text", "supplier", "note"):
        if k in d:
            vals[k] = str(d[k] or "")[:120]
    if "units" in d:
        vals["units"] = num(d["units"], 1) or 1
    if "est_price" in d:
        vals["est_price"] = None if d["est_price"] in (None, "") else num(d["est_price"])
    if d.get("status") in ("pendiente", "comprado"):
        vals["status"] = d["status"]
        vals["bought_at"] = date.today().isoformat() if d["status"] == "comprado" else ""
    if vals:
        get_db().execute(f"UPDATE shopping SET {','.join(k + '=?' for k in vals)} WHERE id=?", [*vals.values(), sid])
        get_db().commit()
    return jsonify(_shop_item(one("SELECT * FROM shopping WHERE id=?", (sid,))))


@app.delete("/api/shopping/<int:sid>")
@login_required
def shopping_del(sid):
    get_db().execute("DELETE FROM shopping WHERE id=?", (sid,))
    get_db().commit()
    return jsonify(ok=True)


# ================================================================ gastos fijos
RECUR_EVERY = {"mensual": 1, "trimestral": 3, "semestral": 6, "anual": 12}


def _periods(r, today):
    """Periodos (AAAA-MM) que tocan desde el inicio hasta hoy."""
    y, m = map(int, r["start"][:7].split("-"))
    step = RECUR_EVERY.get(r["every"], 1)
    out = []
    while True:
        day = min(int(r["day"] or 1), 28)
        when = date(y, m, day)
        if when > today or (r["until"] and f"{y:04d}-{m:02d}" > r["until"][:7]):
            break
        out.append((f"{y:04d}-{m:02d}", when))
        m += step
        while m > 12:
            m -= 12
            y += 1
    return out


def run_recurring(today=None):
    """Apunta en Contabilidad los gastos fijos que ya han llegado y aún no estaban."""
    today = today or date.today()
    db = get_db()
    n = 0
    for r in rows("SELECT * FROM recurring WHERE active=1"):
        done = {x["period"] for x in rows("SELECT period FROM movements WHERE recurring_id=?", (r["id"],))}
        for per, when in _periods(r, today):
            if per in done:
                continue
            db.execute("INSERT INTO movements(date,kind,category,concept,amount,person,recurring_id,period) VALUES(?,?,?,?,?,?,?,?)",
                       (when.isoformat(), "gasto", r["category"] or "Fijos", r["concept"], r["amount"], r["person"], r["id"], per))
            n += 1
    if n:
        db.commit()
    return n


def _recur_next(r, today=None):
    today = today or date.today()
    if not r["active"]:
        return None
    y, m = map(int, r["start"][:7].split("-"))
    step = RECUR_EVERY.get(r["every"], 1)
    for _ in range(400):
        when = date(y, m, min(int(r["day"] or 1), 28))
        if r["until"] and f"{y:04d}-{m:02d}" > r["until"][:7]:
            return None
        if when > today:
            return when.isoformat()
        m += step
        while m > 12:
            m -= 12
            y += 1
    return None


def _recur_vals(d, cur=None):
    cur = cur or {}
    g = lambda k, dflt=None: d[k] if k in d else cur.get(k, dflt)  # noqa: E731
    v = {"concept": str(g("concept", "") or "").strip()[:120], "category": str(g("category", "") or "")[:60],
         "amount": num(g("amount", 0)), "person": str(g("person", "") or "")[:40],
         "every": g("every", "mensual") if g("every", "mensual") in RECUR_EVERY else "mensual",
         "day": max(1, min(28, int(num(g("day", 1), 1)))), "start": str(g("start", "") or date.today().isoformat()[:7])[:7],
         "until": str(g("until", "") or "")[:7], "active": 1 if g("active", 1) else 0}
    if not v["concept"]:
        return None, "pon el concepto (p. ej. Cuota de autónomo)"
    if v["amount"] <= 0:
        return None, "pon el importe"
    try:
        date(*map(int, v["start"].split("-")), 1)
    except (ValueError, TypeError):
        return None, "mes de inicio no válido (AAAA-MM)"
    return v, None


@app.get("/api/recurring")
@login_required
def list_recurring():
    run_recurring()
    out = rows("SELECT * FROM recurring ORDER BY active DESC, concept")
    for r in out:
        r["next"] = _recur_next(r)
        r["booked"] = one("SELECT COUNT(*) AS n, COALESCE(SUM(amount),0) AS s FROM movements WHERE recurring_id=?", (r["id"],))
        r["per_month"] = round(r["amount"] / RECUR_EVERY.get(r["every"], 1), 2)
    return jsonify(items=out, per_month=round(sum(r["per_month"] for r in out if r["active"]), 2))


@app.post("/api/recurring")
@login_required
def add_recurring():
    v, err = _recur_vals(request.get_json(force=True) or {})
    if err:
        return jsonify(error=err), 400
    v["created"] = datetime.now().isoformat(timespec="seconds")
    rid = get_db().execute(f"INSERT INTO recurring({','.join(v)}) VALUES({','.join('?' * len(v))})", list(v.values())).lastrowid
    get_db().commit()
    n = run_recurring()
    return jsonify(id=rid, booked=n), 201


@app.put("/api/recurring/<int:rid>")
@login_required
def edit_recurring(rid):
    cur = one("SELECT * FROM recurring WHERE id=?", (rid,))
    if not cur:
        return jsonify(error="no existe"), 404
    v, err = _recur_vals(request.get_json(force=True) or {}, cur)
    if err:
        return jsonify(error=err), 400
    get_db().execute(f"UPDATE recurring SET {','.join(k + '=?' for k in v)} WHERE id=?", [*v.values(), rid])
    get_db().commit()
    return jsonify(booked=run_recurring())


@app.delete("/api/recurring/<int:rid>")
@login_required
def del_recurring(rid):
    """Borra la plantilla; lo ya apuntado se queda en Contabilidad (salvo ?movements=1)."""
    db = get_db()
    if request.args.get("movements") == "1":
        db.execute("DELETE FROM movements WHERE recurring_id=?", (rid,))
    else:
        db.execute("UPDATE movements SET recurring_id=NULL WHERE recurring_id=?", (rid,))
    db.execute("DELETE FROM recurring WHERE id=?", (rid,))
    db.commit()
    return jsonify(ok=True)


# ================================================================ buscador global
@app.get("/api/search")
@login_required
def search():
    q = (request.args.get("q") or "").strip()
    if not q:
        return jsonify(results=[])
    like = f"%{q.lower()}%"
    res = []
    num_q = q.lstrip("#")
    if num_q.isdigit():
        o = one("SELECT id, client, status, created FROM orders WHERE id=?", (int(num_q),))
        if o:
            res.append({"type": "order", "id": o["id"], "title": f"Pedido #{o['id']} · {o['client']}", "sub": o["status"]})
        sp = one("SELECT s.id, s.color_name, s.brand, m.name AS material FROM spools s LEFT JOIN materials m ON m.id=s.material_id WHERE s.id=?",
                 (int(num_q),))
        if sp:
            res.append({"type": "spool", "id": sp["id"], "title": f"Bobina #{sp['id']} · {sp['material'] or ''} {sp['color_name'] or ''}".strip(),
                        "sub": sp["brand"] or ""})
    for o in rows("""SELECT DISTINCT o.id, o.client, o.status, o.created FROM orders o LEFT JOIN order_items i ON i.order_id=o.id
                     WHERE lower(o.client) LIKE ? OR lower(i.description) LIKE ? OR lower(o.notes) LIKE ? OR lower(o.contact) LIKE ?
                     ORDER BY o.id DESC LIMIT 6""", (like, like, like, like)):
        if not any(r["type"] == "order" and r["id"] == o["id"] for r in res):
            items = ", ".join(f"{i['qty']}× {i['description']}" for i in rows("SELECT qty, description FROM order_items WHERE order_id=? LIMIT 3", (o["id"],)))
            res.append({"type": "order", "id": o["id"], "title": f"Pedido #{o['id']} · {o['client']}", "sub": f"{o['status']} · {items}"[:120]})
    for c in rows("SELECT id, name, phone, email FROM clients WHERE lower(name) LIKE ? OR lower(phone) LIKE ? OR lower(email) LIKE ? ORDER BY name LIMIT 5",
                  (like, like, like)):
        res.append({"type": "client", "id": c["id"], "title": c["name"], "sub": " · ".join(x for x in (c["phone"], c["email"]) if x)})
    for p in rows("""SELECT DISTINCT p.id, p.name, p.category, p.sku FROM products p LEFT JOIN product_variants v ON v.product_id=p.id
                     WHERE lower(p.name) LIKE ? OR lower(p.sku) LIKE ? OR lower(p.category) LIKE ? OR lower(v.name) LIKE ? ORDER BY p.name LIMIT 5""",
                  (like, like, like, like)):
        res.append({"type": "product", "id": p["id"], "title": p["name"], "sub": " · ".join(x for x in (p["category"], p["sku"]) if x)})
    for c in rows("""SELECT id, name, category, unit, location_id FROM components
                     WHERE active=1 AND (lower(name) LIKE ? OR lower(category) LIKE ? OR lower(notes) LIKE ?) ORDER BY name LIMIT 6""",
                  (like, like, like)):
        st = _comp_stock(c["id"])
        res.append({"type": "component", "id": c["id"], "title": c["name"],
                    "sub": " · ".join(x for x in (f"{st:g} {c['unit']}", _loc_path(c["location_id"]) if c["location_id"] else "") if x)})
    for l_ in rows("SELECT id, name FROM locations WHERE lower(name) LIKE ? OR lower(notes) LIKE ? ORDER BY name LIMIT 4", (like, like)):
        res.append({"type": "location", "id": l_["id"], "title": l_["name"], "sub": _loc_path(l_["id"])})
    for sp in rows("""SELECT s.id, s.color_name, s.brand, s.location, s.status, m.name AS material FROM spools s LEFT JOIN materials m ON m.id=s.material_id
                      WHERE s.status!='gastada' AND (lower(s.color_name) LIKE ? OR lower(s.brand) LIKE ? OR lower(m.name) LIKE ? OR lower(s.location) LIKE ?)
                      ORDER BY s.id LIMIT 5""", (like, like, like, like)):
        if not any(r["type"] == "spool" and r["id"] == sp["id"] for r in res):
            res.append({"type": "spool", "id": sp["id"], "title": f"Bobina #{sp['id']} · {sp['material'] or ''} {sp['color_name'] or ''}".strip(),
                        "sub": " · ".join(x for x in (sp["brand"], sp["location"]) if x)})
    for m in rows("SELECT id, name, kind FROM materials WHERE lower(name) LIKE ? OR lower(kind) LIKE ? ORDER BY name LIMIT 3", (like, like)):
        res.append({"type": "material", "id": m["id"], "title": m["name"], "sub": m["kind"]})
    for p in rows("SELECT id, name, host FROM printers WHERE lower(name) LIKE ? OR lower(host) LIKE ? ORDER BY name LIMIT 3", (like, like)):
        res.append({"type": "printer", "id": p["id"], "title": p["name"], "sub": p["host"] or ""})
    for e in rows("SELECT id, name, date, place FROM events WHERE lower(name) LIKE ? OR lower(place) LIKE ? ORDER BY date DESC LIMIT 3", (like, like)):
        res.append({"type": "event", "id": e["id"], "title": e["name"], "sub": " · ".join(x for x in (e["date"], e["place"]) if x)})
    return jsonify(results=res[:30])


@app.get("/api/dashboard")
@login_required
def dashboard():
    """Resumen para la pantalla de inicio."""
    run_recurring()
    today = date.today()
    month = today.strftime("%Y-%m")
    prev = (today.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")

    def money(m):
        r = one("""SELECT ROUND(COALESCE(SUM(CASE WHEN kind='ingreso' THEN amount END),0),2) AS i,
                          ROUND(COALESCE(SUM(CASE WHEN kind='gasto' THEN amount END),0),2) AS g
                   FROM movements WHERE substr(date,1,7)=?""", (m,))
        return {"ingresos": r["i"], "gastos": r["g"], "beneficio": round(r["i"] - r["g"], 2)}

    open_ids = [r["id"] for r in rows(f"""SELECT id FROM orders WHERE status IN {OPEN_STATUSES + ("presupuesto",)}
                                         ORDER BY CASE WHEN due_date='' THEN 1 ELSE 0 END, due_date, id""")]
    open_orders = [order_full(i) for i in open_ids]
    for o in open_orders:
        o.pop("files", None)
        o["overdue"] = bool(o["due_date"] and o["due_date"] < today.isoformat() and o["status"] != "presupuesto")
        o["days_left"] = (date.fromisoformat(o["due_date"]) - today).days if o["due_date"] else None
    by_status = {r["status"]: r["n"] for r in rows("SELECT status, COUNT(*) AS n FROM orders GROUP BY status")}
    unpaid = [o for o in (order_full(r["id"]) for r in rows(
        "SELECT id FROM orders WHERE paid=0 AND status IN ('listo','entregado') ORDER BY id DESC LIMIT 20"))]
    top = rows("""SELECT i.description AS name, SUM(i.qty) AS qty, ROUND(SUM(i.qty*i.unit_price),2) AS total
                  FROM order_items i JOIN orders o ON o.id=i.order_id
                  WHERE substr(o.created,1,7)=? AND o.status NOT IN ('cancelado','presupuesto')
                  GROUP BY i.description ORDER BY total DESC LIMIT 5""", (month,))
    week_ago = (today - timedelta(days=7)).isoformat()
    return jsonify(
        month=month, this_month=money(month), last_month=money(prev),
        orders_month=one("""SELECT COUNT(*) AS n FROM orders WHERE substr(created,1,7)=?
                            AND status NOT IN ('cancelado','presupuesto')""", (month,))["n"],
        new_this_week=one("SELECT COUNT(*) AS n FROM orders WHERE created>=?", (week_ago,))["n"],
        by_status=by_status,
        upcoming=[{k: o.get(k) for k in ("id", "client", "status", "due_date", "overdue", "days_left", "total", "assigned",
                                     "channel", "paid", "hours_in_status")} | {"what": ", ".join(f"{i['qty']}× {i['description']}" for i in o["items"])}
                  for o in open_orders[:12]],
        overdue=sum(1 for o in open_orders if o["overdue"]),
        unpaid=[{"id": o["id"], "client": o["client"], "total": o["total"], "status": o["status"]} for o in unpaid],
        unpaid_total=round(sum(o["total"] for o in unpaid), 2),
        low_stock=[{"name": m["name"], "color": m["color"], "level": m["stock_level"], "unit": m["unit"]}
                   for m in materials_with_stock() if m["active"] and m["stock_low"]],
        top_products=top,
        maintenance=[{"printer": m["name"], "printer_id": m["id"], "task": t["name"], "task_id": t["id"], "state": t["state"], "pct": t["pct"]}
                     for m in maint_all(sync=False) for t in m["tasks"] if t["state"] != "ok"],
        open_events=rows("SELECT id, name, date FROM events WHERE status='abierto' ORDER BY date DESC"),
        forecast=[m for m in forecast()["materials"] if m["status"] in ("falta", "comprar")],
        recent_movements=rows("SELECT date, kind, category, concept, amount, person FROM movements ORDER BY date DESC, id DESC LIMIT 6"),
    )


@app.get("/api/export/movements.csv")
@login_required
def export_movements():
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(["fecha", "tipo", "categoria", "concepto", "importe", "persona", "pedido"])
    for m in rows("SELECT * FROM movements ORDER BY date, id"):
        w.writerow([m["date"], m["kind"], m["category"], m["concept"],
                    f"{m['amount']:.2f}".replace(".", ","), m["person"], m["order_id"] or ""])
    return Response("﻿" + buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=movimientos.csv"})


@app.get("/api/backup")
@admin_required
def backup():
    return send_from_directory(DATA_DIR, "mitallercito.db", as_attachment=True,
                               download_name=f"mitallercito-{date.today().isoformat()}.db")


@app.get("/api/meta")
@login_required
def meta():
    return jsonify(statuses=ORDER_STATUSES)


# ---------------------------------------------------------------- marca / ficheros
app.config["MAX_CONTENT_LENGTH"] = int(os.environ.get("MT_MAX_UPLOAD_MB", "500")) * 1024 * 1024
IMG_MAX = 5 * 1024 * 1024
FILES_DIR = os.path.join(DATA_DIR, "files")
MODEL_EXT = {"stl", "3mf", "obj", "step", "stp", "gcode", "gco", "bgcode", "pwmx", "pwma", "pm3", "ctb", "zip", "f3d", "scad",
             "jpg", "jpeg", "png", "webp", "pdf"}   # fotos y PDF de montaje

MAGIC = {b"\x89PNG": "png", b"\xff\xd8\xff": "jpg", b"RIFF": "webp", b"\x00\x00\x01\x00": "ico",
         b"GIF8": "gif"}


def _store_image(file):
    """Guarda una imagen subida comprobando la firma real (nada de SVG/HTML)."""
    head = file.stream.read(16)
    file.stream.seek(0)
    ext = next((e for m, e in MAGIC.items() if head.startswith(m)), None)
    if ext == "webp" and head[8:12] != b"WEBP":
        ext = None
    if not ext:
        return None
    name = f"{secrets.token_hex(8)}.{ext}"
    os.makedirs(MEDIA_DIR, exist_ok=True)
    file.save(os.path.join(MEDIA_DIR, name))
    return name


def _remove_media(name):
    if name and "/" not in name and ".." not in name:
        try:
            os.remove(os.path.join(MEDIA_DIR, name))
        except FileNotFoundError:
            pass


@app.get("/media/<name>")
def media(name):
    ext = name.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_IMG:
        return "", 404
    resp = send_from_directory(MEDIA_DIR, name, mimetype=ALLOWED_IMG[ext], max_age=86400)
    resp.headers["Content-Security-Policy"] = "default-src 'none'; sandbox"
    return resp


@app.get("/api/brand")
def brand():
    s = load_settings()
    out = {k: s.get(k) for k in PUBLIC_SETTINGS}
    out["logo_url"] = f"/media/{s['logo']}" if s.get("logo") else ""
    out["favicon_url"] = f"/media/{s['favicon']}" if s.get("favicon") else (out["logo_url"] or "/static/favicon.svg")
    return jsonify(out)


@app.get("/favicon.ico")
def favicon():
    s = load_settings()
    f = s.get("favicon") or s.get("logo")
    if f:
        return media(f)
    return send_from_directory(app.static_folder, "favicon.svg", mimetype="image/svg+xml")


@app.post("/api/upload/<kind>")
@login_required
def upload(kind):
    """kind = logo | favicon | product-<id>"""
    if (request.content_length or 0) > IMG_MAX + 4096:
        return jsonify(error="imagen demasiado grande (máx. 5 MB)"), 400
    if kind in ("logo", "favicon") and not is_admin():
        return jsonify(error="solo un administrador puede hacer esto"), 403
    f = request.files.get("file")
    if not f:
        return jsonify(error="no se ha enviado archivo"), 400
    name = _store_image(f)
    if not name:
        return jsonify(error="formato no válido (usa PNG, JPG, WEBP, GIF o ICO)"), 400
    db = get_db()
    if kind in ("logo", "favicon"):
        _remove_media(load_settings().get(kind))
        db.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)", (kind, json.dumps(name)))
    elif kind.startswith("product-") and kind[8:].isdigit():
        old = one("SELECT image FROM products WHERE id=?", (int(kind[8:]),))
        if not old:
            _remove_media(name)
            return jsonify(error="producto no existe"), 404
        _remove_media(old["image"])
        db.execute("UPDATE products SET image=? WHERE id=?", (name, int(kind[8:])))
    else:
        _remove_media(name)
        return jsonify(error="destino no válido"), 400
    db.commit()
    return jsonify(name=name, url=f"/media/{name}")


@app.delete("/api/upload/<kind>")
@admin_required
def delete_upload(kind):
    if kind not in ("logo", "favicon"):
        return jsonify(error="destino no válido"), 400
    _remove_media(load_settings().get(kind))
    get_db().execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)", (kind, json.dumps("")))
    get_db().commit()
    return jsonify(ok=True)


# ---------------------------------------------------------------- extracto mensual
def _vat_part(price, cr, s):
    """IVA contenido en un precio de venta según cómo se calculó la línea."""
    sale = (cr or {}).get("sale_type", s["sale_type"])
    rate = ((cr or {}).get("vat_pct", s["vat_pct"] if s.get("apply_vat") else 0) or 0) / 100.0
    if not rate:
        return 0.0, price
    if sale == "B2C":
        net = price / (1 + rate)
        return price - net, net
    return price * rate, price  # B2B: precio sin IVA, IVA aparte


def monthly_report(year):
    s = load_settings()
    printers = {p["id"]: p["name"] for p in rows("SELECT id,name FROM printers")}
    months = {}

    def M(key):
        if key not in months:
            months[key] = {
                "month": key, "pedidos": 0, "piezas": 0, "lineas_sin_desglose": 0,
                "facturado": 0.0, "base_imponible": 0.0, "iva": 0.0, "envios": 0.0, "descuentos": 0.0,
                "horas_maquina": 0.0, "kwh": 0.0, "luz": 0.0,
                "material": 0.0, "merma": 0.0, "amortizacion": 0.0, "mantenimiento": 0.0,
                "horas_mano_obra": 0.0, "mano_obra": 0.0, "extras": 0.0, "riesgo_fallo": 0.0,
                "comisiones": 0.0, "coste_total": 0.0, "beneficio": 0.0, "fallos": 0, "fallos_coste": 0.0, "fallos_g": 0.0,
                "por_impresora": {}, "por_material": {}, "por_canal": {},
            }
        return months[key]

    orders = rows("""SELECT * FROM orders WHERE substr(created,1,4)=?
                     AND status NOT IN ('cancelado','presupuesto')""", (str(year),))
    for o in orders:
        m = M(o["created"][:7])
        m["pedidos"] += 1
        m["envios"] += o["shipping"] or 0
        m["descuentos"] += o["discount"] or 0
        canal = o["channel"] or "—"
        order_total = 0.0
        for it in rows("SELECT * FROM order_items WHERE order_id=?", (o["id"],)):
            qty = it["qty"] or 0
            m["piezas"] += qty
            line_price = qty * (it["unit_price"] or 0)
            order_total += line_price
            cr = None
            if it["calc_result"]:
                try:
                    cr = json.loads(it["calc_result"])
                except ValueError:
                    cr = None
            vat, net = _vat_part(line_price, cr, s)
            m["iva"] += vat
            m["base_imponible"] += net
            if not cr:
                m["lineas_sin_desglose"] += 1
                m["coste_total"] += qty * (it["unit_cost"] or 0)
                continue
            f = qty / (cr.get("units") or 1)       # fracción del trabajo calculado
            b = cr.get("breakdown", {})
            h = (cr.get("hours") or 0) * f
            m["horas_maquina"] += h
            m["kwh"] += (cr.get("kwh") or 0) * f
            m["luz"] += b.get("electricidad", 0) * f
            for k in ("material", "merma", "amortizacion", "mantenimiento", "extras", "riesgo_fallo"):
                m[k] += b.get(k, 0) * f
            m["mano_obra"] += (b.get("preparacion", 0) + b.get("postprocesado", 0)) * f
            m["horas_mano_obra"] += ((cr.get("prep_min") or 0) + (cr.get("post_min") or 0)) / 60 * f
            # comisión real sobre el precio cobrado (sin IVA)
            m["comisiones"] += net * (cr.get("commission_pct") or 0) / 100 + \
                (cr.get("commission_fixed") or 0) * f
            m["coste_total"] += (cr.get("cost") or 0) * f
            pname = cr.get("printer") or printers.get(cr.get("printer_id")) or "—"
            pi = m["por_impresora"].setdefault(pname, {"horas": 0.0, "kwh": 0.0, "luz": 0.0})
            pi["horas"] += h
            pi["kwh"] += (cr.get("kwh") or 0) * f
            pi["luz"] += b.get("electricidad", 0) * f
            for ml in cr.get("materials", []):
                key = ml["name"] if ml.get("amount") is not None else "Coste laminador"
                pm = m["por_material"].setdefault(key, {"cantidad": 0.0, "unidad": ml.get("unit", ""), "coste": 0.0})
                pm["cantidad"] += (ml.get("amount") or 0) * f
                pm["coste"] += (ml.get("cost") or 0) * f
        order_total += (o["shipping"] or 0) - (o["discount"] or 0)
        m["facturado"] += order_total
        pc = m["por_canal"].setdefault(canal, {"pedidos": 0, "facturado": 0.0})
        pc["pedidos"] += 1
        pc["facturado"] += order_total

    for fl in rows("SELECT * FROM print_failures WHERE substr(created,1,4)=?", (str(year),)):
        m = M(fl["created"][:7])
        m["fallos"] += 1
        m["fallos_coste"] += fl["cost"] or 0
        m["fallos_g"] += sum(g.get("amount") or 0 for g in json.loads(fl["grams_json"] or "[]"))
        m["kwh"] += fl["kwh"] or 0
        m["horas_maquina"] += fl["hours"] or 0
    out = []
    for key in sorted(months):
        m = months[key]
        m["coste_total"] += m["comisiones"]
        # beneficio = lo cobrado sin IVA (sin contar envíos, que se pagan al transportista) - costes
        m["beneficio"] = m["base_imponible"] - m["descuentos"] - m["coste_total"] - m["fallos_coste"]
        lights = one("""SELECT ROUND(SUM(amount),2) AS t FROM movements WHERE kind='gasto'
                        AND category='Electricidad' AND substr(date,1,7)=?""", (key,))
        m["luz_apuntada"] = lights["t"] or 0
        out.append(_round_all(m))
    return out


def _round_all(x):
    if isinstance(x, float):
        return round(x, 2)
    if isinstance(x, dict):
        return {k: _round_all(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_round_all(v) for v in x]
    return x


@app.get("/api/report/monthly")
@login_required
def api_monthly():
    return jsonify(monthly_report(request.args.get("year") or date.today().year))


@app.post("/api/report/electricity")
@login_required
def book_electricity():
    """Apunta como gasto la luz estimada de un mes (o actualiza el apunte si ya existe)."""
    d = request.get_json(force=True) or {}
    month = str(d.get("month", ""))
    if len(month) != 7:
        return jsonify(error="mes no válido"), 400
    rep = next((m for m in monthly_report(month[:4]) if m["month"] == month), None)
    if not rep or rep["luz"] <= 0:
        return jsonify(error="no hay consumo ese mes"), 400
    db = get_db()
    concept = f"Luz impresoras {month} (estimada, {rep['kwh']} kWh)"
    db.execute("DELETE FROM movements WHERE category='Electricidad' AND concept LIKE ?", (f"Luz impresoras {month}%",))
    y, mo = int(month[:4]), int(month[5:])
    last = (date(y + (mo == 12), mo % 12 + 1, 1) - date.resolution).isoformat()
    db.execute("INSERT INTO movements(date,kind,category,concept,amount,person) VALUES(?,?,?,?,?,?)",
               (last, "gasto", "Electricidad", concept, rep["luz"], d.get("person", "")))
    db.commit()
    return jsonify(ok=True, amount=rep["luz"])


@app.get("/api/export/monthly.csv")
@login_required
def export_monthly():
    year = request.args.get("year") or date.today().year
    cols = ["month", "pedidos", "piezas", "facturado", "base_imponible", "iva", "horas_maquina", "kwh", "luz",
            "material", "merma", "amortizacion", "mantenimiento", "horas_mano_obra", "mano_obra", "extras",
            "riesgo_fallo", "comisiones", "coste_total", "beneficio"]
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(cols)
    for m in monthly_report(year):
        w.writerow([str(m[c]).replace(".", ",") if isinstance(m[c], float) else m[c] for c in cols])
    return Response("﻿" + buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": f"attachment; filename=extracto-{year}.csv"})


# ---------------------------------------------------------------- actualizaciones desde la web
UPD_DIR = os.path.join(DATA_DIR, "updates")


IN_DOCKER = os.environ.get("MT_DOCKER") == "1"


def app_repo():
    r = os.environ.get("MT_REPO")
    if not r:
        try:
            r = open(os.path.join(BASE_DIR, "REPO")).read().strip()
        except OSError:
            r = ""
    return "" if "__" in r else r


def app_commit():
    try:
        return open(os.path.join(BASE_DIR, "COMMIT")).read().strip()[:40]
    except OSError:
        return ""


def app_version():
    try:
        return open(os.path.join(BASE_DIR, "VERSION")).read().strip()
    except OSError:
        return "dev"


def _check_password():
    pw = request.form.get("password") or (request.get_json(silent=True) or {}).get("password", "")
    u = one("SELECT pw_hash FROM users WHERE username=?", (session.get("user"),))
    return bool(u and check_password_hash(u["pw_hash"], pw))


def _request_update(action):
    os.makedirs(UPD_DIR, exist_ok=True)
    tmp = os.path.join(UPD_DIR, ".request.tmp")
    with open(tmp, "w") as f:
        json.dump({"action": action, "user": session.get("user"),
                   "time": datetime.now().isoformat(timespec="seconds")}, f)
    os.replace(tmp, os.path.join(UPD_DIR, "request.json"))   # el .path de systemd vigila este fichero


@app.get("/api/version")
@login_required
def version():
    return jsonify(version=app_version())


@app.get("/api/update/status")
@login_required
def update_status():
    st = {}
    try:
        st = json.load(open(os.path.join(UPD_DIR, "status.json")))
    except (OSError, ValueError):
        pass
    hist = []
    try:
        hist = open(os.path.join(UPD_DIR, "history.log")).read().splitlines()[-15:][::-1]
    except OSError:
        pass
    prev = None
    try:
        prev = open("/opt/mitallercito.prev/VERSION").read().strip()
    except OSError:
        pass
    return jsonify(version=app_version(), status=st, history=hist, previous=prev,
                   pending=os.path.exists(os.path.join(UPD_DIR, "request.json")),
                   updater=os.path.exists("/usr/local/sbin/mitallercito-updater"),
                   signed_only=os.path.exists("/etc/mitallercito/signing.pub"),
                   docker=IN_DOCKER, repo=app_repo(), commit=app_commit(),
                   channel=load_settings().get("update_channel", "releases"))


def _vtuple(v):
    out = []
    for part in str(v).lstrip("vV").split("."):
        digits = "".join(c for c in part if c.isdigit())
        out.append(int(digits) if digits else 0)
    return tuple(out + [0] * (3 - len(out)))


_REL_CACHE = {"t": 0, "data": None}


def latest_release(force=False):
    import time
    repo = app_repo()
    if not repo:
        raise PrinterError("no hay repositorio configurado")
    if not force and _REL_CACHE["data"] and time.time() - _REL_CACHE["t"] < 3600:
        return _REL_CACHE["data"]
    req = urllib.request.Request(f"https://api.github.com/repos/{repo}/releases/latest",
                                 headers={"Accept": "application/vnd.github+json", "User-Agent": "mitallercito"})
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            rel = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise PrinterError("no hay versiones publicadas todavía" if e.code == 404 else f"GitHub respondió {e.code}") from None
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
        raise PrinterError(f"no se pudo consultar GitHub ({getattr(e, 'reason', e)})") from None
    asset = next((a for a in rel.get("assets", []) if a.get("name", "").endswith(".mtc")), None)
    data = {"tag": rel.get("tag_name", ""), "version": rel.get("tag_name", "").lstrip("vV"), "name": rel.get("name") or "",
            "notes": (rel.get("body") or "")[:4000], "url": rel.get("html_url", ""),
            "asset": asset["browser_download_url"] if asset else None, "asset_name": asset["name"] if asset else None,
            "size": asset.get("size") if asset else None}
    _REL_CACHE.update(t=time.time(), data=data)
    return data


def _gh_json(url, timeout=8):
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "mitallercito"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise PrinterError("no encontrado en GitHub" if e.code == 404 else f"GitHub respondió {e.code}") from None
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
        raise PrinterError(f"no se pudo consultar GitHub ({getattr(e, 'reason', e)})") from None


def latest_main():
    """Último commit de la rama main y la VERSION que trae."""
    repo = app_repo()
    if not repo:
        raise PrinterError("no hay repositorio configurado")
    c = _gh_json(f"https://api.github.com/repos/{repo}/commits/main")
    sha = c.get("sha", "")
    if len(sha) != 40 or not all(ch in "0123456789abcdef" for ch in sha):
        raise PrinterError("respuesta de GitHub no válida")
    try:
        with urllib.request.urlopen(urllib.request.Request(f"https://raw.githubusercontent.com/{repo}/{sha}/VERSION",
                                                           headers={"User-Agent": "mitallercito"}), timeout=8) as r:
            version = r.read().decode().strip()[:30]
    except (urllib.error.URLError, TimeoutError, OSError):
        version = "?"
    msg = (c.get("commit", {}).get("message") or "").strip()
    return {"sha": sha, "short": sha[:7], "version": version, "date": (c.get("commit", {}).get("committer") or {}).get("date", ""),
            "notes": msg[:4000], "url": c.get("html_url", f"https://github.com/{repo}/commit/{sha}"), "name": msg.split("\n")[0][:120]}


def _signed_only():
    return os.path.exists("/etc/mitallercito/signing.pub")


@app.put("/api/update/channel")
@admin_required
def set_channel():
    ch = (request.get_json(force=True) or {}).get("channel")
    if ch not in ("releases", "main"):
        return jsonify(error="canal no válido"), 400
    get_db().execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)", ("update_channel", json.dumps(ch)))
    get_db().commit()
    return jsonify(ok=True, channel=ch)


@app.get("/api/update/check")
@admin_required
def update_check():
    channel = load_settings().get("update_channel", "releases")
    try:
        if channel == "main":
            m = latest_main()
            cur = app_commit()
            newer = (m["sha"] != cur) if cur else (m["version"] != "?" and _vtuple(m["version"]) >= _vtuple(app_version()))
            return jsonify(ok=True, channel="main", current=app_version(), current_commit=cur[:7], newer=newer,
                           blocked=_signed_only(), **m)
        rel = latest_release(force=request.args.get("force") == "1")
    except PrinterError as e:
        return jsonify(ok=False, channel=channel, error=str(e), current=app_version())
    return jsonify(ok=True, channel="releases", current=app_version(), newer=_vtuple(rel["version"]) > _vtuple(app_version()), **rel)


MAIN_FILES = ("app.py", "static", "requirements.txt", "VERSION", "REPO", "README.md", "LICENSE", "CHANGELOG.md",
              "install.sh", "updater", "signing.pub")


def build_payload_from_main(sha, dst):
    """Descarga el código de un commit de main y lo reempaqueta como paquete de la app (sin firmar)."""
    import tarfile
    repo = app_repo()
    url = f"https://codeload.github.com/{repo}/tar.gz/{sha}"
    raw = io.BytesIO()
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "mitallercito"}), timeout=60) as r:
        for chunk in iter(lambda: r.read(1 << 20), b""):
            raw.write(chunk)
            if raw.tell() > 40 * 1024 * 1024:
                raise PrinterError("el repositorio es demasiado grande")
    raw.seek(0)
    with tarfile.open(fileobj=raw, mode="r:gz") as src, tarfile.open(dst, "w:gz") as out:
        for m in src.getmembers():
            parts = m.name.split("/", 1)
            if len(parts) < 2 or not parts[1]:
                continue
            rel = parts[1]
            if rel.split("/")[0] not in MAIN_FILES or not (m.isfile() or m.isdir()) or ".." in rel.split("/"):
                continue
            data = src.extractfile(m) if m.isfile() else None
            m.name = "mitallercito/" + rel
            m.uid = m.gid = 0
            m.uname = m.gname = "root"
            out.addfile(m, data)
        ti = tarfile.TarInfo("mitallercito/COMMIT")
        ti.size = len(sha)
        out.addfile(ti, io.BytesIO(sha.encode()))


@app.post("/api/update/install-latest")
@admin_required
def install_latest():
    if IN_DOCKER:
        return jsonify(error="en Docker se actualiza con «docker compose pull && docker compose up -d»"), 400
    if not _check_password():
        return jsonify(error="contraseña incorrecta"), 403
    if load_settings().get("update_channel") == "main":
        if _signed_only():
            return jsonify(error="esta instalación solo acepta versiones firmadas: usa el canal «Versiones publicadas»"), 400
        os.makedirs(UPD_DIR, exist_ok=True)
        dst = os.path.join(UPD_DIR, "pending.tar.gz")
        try:
            m = latest_main()
            build_payload_from_main(m["sha"], dst)
        except (PrinterError, urllib.error.URLError, TimeoutError, OSError) as e:
            return jsonify(error=f"no se pudo descargar main: {e}"), 502
        _request_update("update")
        app.logger.warning("instalación de main@%s pedida por %s", m["short"], session.get("user"))
        return jsonify(ok=True, version=f"{m['version']} (main@{m['short']})"), 202
    try:
        rel = latest_release(force=True)
    except PrinterError as e:
        return jsonify(error=str(e)), 502
    if not rel["asset"]:
        return jsonify(error="la última versión no tiene paquete .mtc"), 400
    if not rel["asset"].startswith("https://github.com/") and not rel["asset"].startswith("https://objects.githubusercontent.com/"):
        return jsonify(error="origen del paquete no esperado"), 400
    os.makedirs(UPD_DIR, exist_ok=True)
    dst = os.path.join(UPD_DIR, "pending.tar.gz")
    req = urllib.request.Request(rel["asset"], headers={"User-Agent": "mitallercito", "Accept": "application/octet-stream"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r, open(dst, "wb") as out:
            size = 0
            for chunk in iter(lambda: r.read(1 << 20), b""):
                size += len(chunk)
                if size > 50 * 1024 * 1024:
                    raise PrinterError("paquete demasiado grande")
                out.write(chunk)
    except (urllib.error.URLError, TimeoutError, OSError, PrinterError) as e:
        try:
            os.remove(dst)
        except OSError:
            pass
        return jsonify(error=f"no se pudo descargar: {e}"), 502
    _request_update("update")
    app.logger.warning("instalación de %s desde GitHub pedida por %s", rel["version"], session.get("user"))
    return jsonify(ok=True, version=rel["version"]), 202


@app.post("/api/update")
@admin_required
def upload_update():
    if IN_DOCKER:
        return jsonify(error="en Docker se actualiza con «docker compose pull && docker compose up -d»"), 400
    if (request.content_length or 0) > 50 * 1024 * 1024:
        return jsonify(error="paquete demasiado grande"), 400
    if not _check_password():
        return jsonify(error="contraseña incorrecta"), 403
    f = request.files.get("file")
    if not f:
        return jsonify(error="no se ha enviado el paquete"), 400
    os.makedirs(UPD_DIR, exist_ok=True)
    dst = os.path.join(UPD_DIR, "pending.tar.gz")
    f.save(dst)
    # Validación rápida aquí (la buena la repite el aplicador como root)
    import tarfile
    try:
        with tarfile.open(dst, "r:*") as t:
            names = t.getnames()
            if "payload.tar.gz" in names:          # paquete firmado .mtc
                inner = tarfile.open(fileobj=io.BytesIO(t.extractfile("payload.tar.gz").read()), mode="r:gz")
                t, names = inner, inner.getnames()
            ver_member = t.extractfile("mitallercito/VERSION") if "mitallercito/VERSION" in names else None
            new_ver = ver_member.read().decode().strip() if ver_member else None
    except (tarfile.TarError, OSError, KeyError):
        os.remove(dst)
        return jsonify(error="no es un paquete .tar / .tar.gz válido"), 400
    if not new_ver or "mitallercito/app.py" not in names:
        os.remove(dst)
        return jsonify(error="el paquete no es de MiTallercito (falta VERSION o app.py)"), 400
    _request_update("update")
    app.logger.warning("actualización a %s pedida por %s", new_ver, session.get("user"))
    return jsonify(ok=True, version=new_ver), 202


@app.post("/api/update/rollback")
@admin_required
def rollback():
    if not _check_password():
        return jsonify(error="contraseña incorrecta"), 403
    _request_update("rollback")
    return jsonify(ok=True), 202


# ---------------------------------------------------------------- API pública (tienda online, futuro)
@app.get("/api/public/catalog")
def public_catalog():
    s = load_settings()
    if not s.get("store_enabled"):
        return jsonify(error="tienda no activa"), 404
    items = rows("""SELECT id, sku, name, category, description, image,
                    COALESCE(public_price, unit_price) AS price, stock, lead_days
                    FROM products WHERE public=1 ORDER BY category, name""")
    for i in items:
        i["image_url"] = f"/media/{i['image']}" if i["image"] else ""
        i.pop("image")
        i["availability"] = "bajo pedido" if i["stock"] is None else ("en stock" if i["stock"] > 0 else "agotado")
    return jsonify(shop=s["shop_name"], currency="EUR", vat_included=s["sale_type"] == "B2C", products=items)


@app.get("/api/public/order/<token>")
def public_order(token):
    """Estado de un pedido para el cliente (enlace con token, sin datos internos)."""
    if not load_settings().get("store_enabled") or len(token) < 16:
        return jsonify(error="no disponible"), 404
    o = one("SELECT id FROM orders WHERE public_token=?", (token,))
    if not o:
        return jsonify(error="no existe"), 404
    o = order_full(o["id"])
    return jsonify(id=o["id"], status=o["status"], due_date=o["due_date"], total=o["total"],
                   items=[{"description": i["description"], "qty": i["qty"], "unit_price": i["unit_price"]}
                          for i in o["items"]])


# ---------------------------------------------------------------- frontend
@app.get("/")
def index():
    html = open(os.path.join(app.static_folder, "index.html"), encoding="utf-8").read()
    resp = Response(html.replace("__V__", app_version()), mimetype="text/html")
    resp.headers["Cache-Control"] = "no-cache"
    return resp


with app.app_context():
    init_db()


# ---------------------------------------------------------------- CLI
def cli():
    import getpass
    admin_flag = "--admin" in sys.argv
    sys.argv = [a for a in sys.argv if a != "--admin"]
    if len(sys.argv) > 1 and sys.argv[1] == "notify":
        with app.app_context():
            for m in run_notifications():
                print("enviado:", m)
        return
    if len(sys.argv) > 1 and sys.argv[1] == "setup-token":
        with app.app_context():
            if not setup_needed():
                print("La tienda ya está configurada (hay usuarios). Usa «mitallercito adduser».")
                sys.exit(1)
            print(setup_token(create=True))
        return
    if len(sys.argv) < 2 or sys.argv[1] not in ("adduser", "passwd", "deluser", "users", "role"):
        print("uso: mitallercito adduser <usuario> [--admin] | passwd <usuario> | deluser <usuario> | "
              "role <usuario> admin|user | users")
        sys.exit(1)
    with app.app_context():
        db = get_db()
        cmd = sys.argv[1]
        if cmd == "users":
            for u in rows("SELECT username, role FROM users ORDER BY username"):
                print(f"{u['username']}\t{u['role']}")
            return
        if len(sys.argv) < 3 or not sys.argv[2].strip():
            print(f"falta el nombre de usuario. Ejemplo: mitallercito {cmd} oda")
            sys.exit(1)
        user = sys.argv[2].strip().lower()
        if cmd == "deluser":
            db.execute("DELETE FROM users WHERE username=?", (user,))
        elif cmd == "role":
            role = sys.argv[3] if len(sys.argv) > 3 else ""
            if role not in ("admin", "user"):
                print("rol: admin o user"); sys.exit(1)
            db.execute("UPDATE users SET role=? WHERE username=?", (role, user))
        else:
            if len(sys.argv) > 3:
                pw = sys.argv[3]
            elif not sys.stdin.isatty():      # p.ej. desde el script del host: echo pass | mitallercito adduser x
                pw = sys.stdin.readline().rstrip("\n")
                if not pw:
                    print("contraseña vacía")
                    sys.exit(1)
            else:
                pw = getpass.getpass(f"Contraseña para {user}: ")
                if pw != getpass.getpass("Repite la contraseña: "):
                    print("las contraseñas no coinciden, no se ha cambiado nada")
                    sys.exit(1)
                if not pw:
                    print("contraseña vacía, no se ha cambiado nada")
                    sys.exit(1)
            h = generate_password_hash(pw)
            exists = one("SELECT 1 AS x FROM users WHERE username=?", (user,))
            if exists:
                db.execute("UPDATE users SET pw_hash=? WHERE username=?", (h, user))
                if admin_flag:
                    db.execute("UPDATE users SET role='admin' WHERE username=?", (user,))
            else:
                first = not one("SELECT 1 AS x FROM users")
                db.execute("INSERT INTO users(username,pw_hash,role) VALUES(?,?,?)",
                           (user, h, "admin" if (admin_flag or first) else "user"))
        db.commit()
        if one("SELECT 1 AS x FROM users"):
            try:
                os.remove(SETUP_FILE)
            except OSError:
                pass
        print(f"ok ({user})")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        cli()
    else:
        # Solo para pruebas locales. En producción lo sirve gunicorn (systemd).
        app.run(host=os.environ.get("HOST", "127.0.0.1"), port=int(os.environ.get("PORT", 8080)),
                debug=os.environ.get("MT_DEBUG") == "1")
