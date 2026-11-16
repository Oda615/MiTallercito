import os
import sys
import tempfile

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("MT_DATA_DIR", tempfile.mkdtemp(prefix="t3d-import-"))
os.environ.setdefault("MT_SECRET", "test")

import app as appmod  # noqa: E402


@pytest.fixture()
def app(tmp_path, monkeypatch):
    """App con base de datos y carpetas nuevas en cada test."""
    d = str(tmp_path)
    for name, val in {"DATA_DIR": d, "DB_PATH": os.path.join(d, "mitallercito.db"), "MEDIA_DIR": os.path.join(d, "media"),
                      "FILES_DIR": os.path.join(d, "files"), "UPD_DIR": os.path.join(d, "updates"),
                      "SETUP_FILE": os.path.join(d, "setup_token")}.items():
        monkeypatch.setattr(appmod, name, val)
    appmod.app.config["TESTING"] = True
    with appmod.app.app_context():
        appmod.init_db()
    return appmod.app


def make_user(app, name="admin", pw="clave1234", role="admin"):
    with app.app_context():
        db = appmod.get_db()
        db.execute("INSERT INTO users(username,pw_hash,role) VALUES(?,?,?)", (name, appmod.generate_password_hash(pw), role))
        db.commit()


@pytest.fixture()
def admin(app):
    make_user(app)
    c = app.test_client()
    assert c.post("/api/login", json={"username": "admin", "password": "clave1234"}).status_code == 200
    return c


@pytest.fixture()
def user(app):
    make_user(app, "pepe", "clave1234", "user")
    c = app.test_client()
    assert c.post("/api/login", json={"username": "pepe", "password": "clave1234"}).status_code == 200
    return c


def add_printer(c, **kw):
    data = {"name": "P1", "watts": 200, "cost": 1000, "hours_day": 10, "amort_months": 10, "maint_month": 30, **kw}
    return c.post("/api/printers", json=data).get_json()["id"]


def add_material(c, **kw):
    data = {"name": "PLA", "kind": "PLA", "price": 20, "qty": 1000, "unit": "g", **kw}
    return c.post("/api/materials", json=data).get_json()["id"]
