import io
import json

import app as appmod
from conftest import add_material, add_printer


def test_setup_wizard_requires_token(app):
    c = app.test_client()
    assert c.get("/api/setup").get_json()["needed"] is True
    with app.app_context():
        tok = appmod.setup_token(create=True)
    assert c.post("/api/setup", json={"token": "malo", "admin": {"username": "x", "password": "12345678"}}).status_code == 403
    r = c.post("/api/setup", json={"token": tok, "admin": {"username": "Ana", "password": "12345678"},
                                   "shop_name": "Mi tienda", "people": ["Ana"], "printers": [{"name": "U1", "watts": 200}],
                                   "materials": [{"name": "PLA", "price": 18}]})
    assert r.status_code == 200 and r.get_json()["role"] == "admin"
    assert c.get("/api/me").get_json()["user"] == "ana"
    assert c.post("/api/setup", json={"token": tok}).status_code == 409
    with app.app_context():
        assert appmod.setup_token() is None


def test_no_personal_seed_data(app):
    with app.app_context():
        assert not appmod.rows("SELECT * FROM printers")
        assert not appmod.rows("SELECT * FROM materials")
        assert appmod.load_settings()["people"] == []


def test_roles(admin, user):
    assert user.put("/api/settings", json={"margin_pct": 1}).status_code == 403
    assert user.post("/api/printers", json={"name": "x"}).status_code == 403
    assert user.get("/api/users").status_code == 403
    assert user.post("/api/update/rollback", json={}).status_code == 403
    assert user.post("/api/orders", json={"client": "Juan"}).status_code == 201
    assert admin.put("/api/users/admin", json={"role": "user"}).status_code == 400   # último admin


def test_login_rate_limit(app):
    c = app.test_client()
    codes = [c.post("/api/login", json={"username": "x", "password": "y"}).status_code for _ in range(6)]
    assert codes[:5] == [401] * 5 and codes[5] == 429


def test_stock_follows_order_status(admin):
    p, m = add_printer(admin), add_material(admin)
    admin.post(f"/api/materials/{m}/stock", json={"mode": "ajuste", "amount": 1000})
    inp = {"printer_id": p, "hours": 1, "units": 2, "materials": [{"material_id": m, "amount": 100}]}
    r = admin.post("/api/calc", json=inp).get_json()
    o = admin.post("/api/orders", json={"client": "X", "items": [{"description": "a", "qty": 4, "unit_price": 5,
                                                                    "calc_json": inp, "calc_result": r}]}).get_json()
    level = lambda: next(x for x in admin.get("/api/materials").get_json() if x["id"] == m)["stock_level"]  # noqa: E731
    assert level() == 1000
    admin.put(f"/api/orders/{o['id']}", json={"status": "imprimiendo"})
    assert level() == 800                     # 4 piezas de un trabajo de 2 → 2 trabajos × 100 g
    admin.put(f"/api/orders/{o['id']}", json={"status": "cancelado"})
    assert level() == 1000


def test_paid_order_creates_single_income(admin):
    o = admin.post("/api/orders", json={"client": "X", "items": [{"description": "a", "qty": 2, "unit_price": 5}]}).get_json()
    admin.put(f"/api/orders/{o['id']}", json={"paid": True, "paid_to": "Ana"})
    admin.put(f"/api/orders/{o['id']}", json={"notes": "otra vez"})
    inc = [m for m in admin.get("/api/movements").get_json() if m["kind"] == "ingreso"]
    assert len(inc) == 1 and inc[0]["amount"] == 10


def test_files_and_repeat(admin):
    o = admin.post("/api/orders", json={"client": "X", "items": [{"description": "a", "qty": 1, "unit_price": 5,
                                                                    "print_info": {"layer_height": "0.2"}}]}).get_json()
    f = admin.post("/api/files", data={"file": (io.BytesIO(b"solid"), "pieza.stl"), "order_id": o["id"]})
    assert f.status_code == 201
    assert admin.post("/api/files", data={"file": (io.BytesIO(b"x"), "virus.exe"), "order_id": o["id"]}).status_code == 400
    n = admin.post(f"/api/orders/{o['id']}/repeat").get_json()
    assert n["id"] != o["id"] and n["status"] == "recibido" and len(n["files"]) == 1
    assert json.loads(n["items"][0]["print_info"])["layer_height"] == "0.2"
    assert admin.get(f"/api/files/{n['files'][0]['id']}").data == b"solid"


def test_image_upload_rejects_svg(admin):
    r = admin.post("/api/upload/logo", data={"file": (io.BytesIO(b"<svg onload=alert(1)>"), "x.png")})
    assert r.status_code == 400


def test_printer_api_key_never_returned(admin):
    pid = add_printer(admin, conn="moonraker", host="http://10.0.0.5/", api_key="secreta")
    p = next(x for x in admin.get("/api/printers").get_json() if x["id"] == pid)
    assert p["api_key"] != "secreta" and p["host"] == "10.0.0.5"


def test_bridge_flow(admin, app):
    b = admin.post("/api/bridges", json={"name": "Casa"}).get_json()
    pid = add_printer(admin, conn="bridge", bridge_id=str(b["id"]), host="192.168.1.9")
    br = app.test_client()
    h = {"Authorization": f"Bearer {b['token']}"}
    assert br.get("/api/bridge/config", headers={"Authorization": "Bearer mtb_x"}).status_code == 401
    cfg = br.get("/api/bridge/config", headers=h).get_json()
    assert [p["id"] for p in cfg["printers"]] == [pid]
    br.post("/api/bridge/report", headers=h, json={"printers": [{"id": pid, "status": {"state": "standby"}, "history": []},
                                                                {"id": 999, "status": {"state": "hack"}}]})
    st = admin.get("/api/printers/status").get_json()[0]
    assert st["online"] and st["state"] == "standby"


def test_dashboard(admin):
    o = admin.post("/api/orders", json={"client": "X", "due_date": "2000-01-01",
                                        "items": [{"description": "a", "qty": 2, "unit_price": 5}]}).get_json()
    admin.put(f"/api/orders/{o['id']}", json={"status": "imprimiendo"})
    d = admin.get("/api/dashboard").get_json()
    assert d["overdue"] == 1 and d["upcoming"][0]["id"] == o["id"] and d["upcoming"][0]["what"] == "2× a"
    assert d["by_status"]["imprimiendo"] == 1


def test_update_channel(admin, user):
    assert user.put("/api/update/channel", json={"channel": "main"}).status_code == 403
    assert admin.put("/api/update/channel", json={"channel": "nightly"}).status_code == 400
    assert admin.put("/api/update/channel", json={"channel": "main"}).get_json()["channel"] == "main"


def test_spools_weigh_finish_and_tare_learning(admin):
    m = add_material(admin, name="PLA Sunlu", kind="PLA")
    sp = admin.post("/api/spools", json={"material_id": m, "brand": "Sunlu", "color_name": "Rojo", "color_hex": "#d01010",
                                         "net_g": 1000, "count": 2, "paid_total": 36, "person": "Ana"}).get_json()
    assert len(sp) == 2 and sp[0]["remaining"] == 1000 and sp[0]["price"] == 18
    assert admin.post(f"/api/spools/{sp[0]['id']}/weigh", json={"gross": 600}).status_code == 400   # sin tara conocida
    r = admin.post(f"/api/spools/{sp[0]['id']}/weigh", json={"gross": 600, "tare_g": 150}).get_json()
    assert r["remaining"] == 450 and r["status"] == "abierta"
    assert admin.post(f"/api/spools/{sp[1]['id']}/finish", json={"empty_g": 160}).get_json()["learned"]
    nuevo = admin.post("/api/spools", json={"material_id": m, "brand": "SUNLU ", "color_name": "Azul", "net_g": 1000}).get_json()[0]
    assert nuevo["tare_g"] == 160                                     # aprendido para la marca
    mat = next(x for x in admin.get("/api/materials").get_json() if x["id"] == m)
    assert mat["stock_level"] == 1450 and mat["spools"] == 2
    gasto = [x for x in admin.get("/api/movements").get_json() if x["kind"] == "gasto"]
    assert gasto and gasto[0]["amount"] == 36


def test_spool_match(admin):
    m = add_material(admin, name="PLA", kind="PLA")
    admin.post("/api/spools", json={"material_id": m, "brand": "X", "color_name": "Negro", "color_hex": "#111111", "net_g": 1000})
    admin.post("/api/spools", json={"material_id": m, "brand": "X", "color_name": "Naranja", "color_hex": "#E8572A", "net_g": 50})
    r = admin.post("/api/spools/match", json={"needs": [{"kind": "PLA", "color_hex": "#1A1A1A", "grams": 100},
                                                         {"kind": "PLA", "color_hex": "#F05A2A", "grams": 100},
                                                         {"kind": "PLA", "color_hex": "#00AE42", "grams": 10}]}).get_json()
    a, b, c = r["results"]
    assert a["ok"] and not b["ok"] and b["close"] and not c["close"] and not r["all_ok"]


def test_order_status_history_and_telegram_alerts(admin, app):
    from datetime import datetime, timedelta
    o = admin.post("/api/orders", json={"client": "Juan", "items": [{"description": "Granada", "qty": 1, "unit_price": 5}]}).get_json()
    assert o["status"] == "recibido" and o["status_log"][0]["status"] == "recibido"
    admin.put(f"/api/orders/{o['id']}", json={"status": "programado"})
    sent = []
    with app.app_context():
        msgs = appmod.run_notifications(now=datetime.now() + timedelta(hours=100), send=sent.append)
        again = appmod.run_notifications(now=datetime.now() + timedelta(hours=101), send=sent.append)
    assert any("Pedido #" in m and "programado" in m for m in msgs)
    assert not any("programado" in m for m in again)                 # no repite hasta el recordatorio
    assert admin.get("/api/settings").get_json()["telegram_token"] == ""


def test_failure_records_waste(admin):
    p, m = add_printer(admin), add_material(admin)
    inp = {"printer_id": p, "hours": 4, "units": 1, "materials": [{"material_id": m, "amount": 200}]}
    r = admin.post("/api/calc", json=inp).get_json()
    o = admin.post("/api/orders", json={"client": "X", "items": [{"description": "Grip", "qty": 1, "unit_price": 20,
                                                                    "calc_json": inp, "calc_result": r}]}).get_json()
    f = admin.post(f"/api/orders/{o['id']}/failures", json={"item_index": 0, "pct": 25, "cause": "despegue"}).get_json()
    assert json.loads(f["grams_json"])[0]["amount"] == 50 and f["hours"] == 1
    o2 = admin.get(f"/api/orders/{o['id']}").get_json()
    assert o2["failure_cost"] > 0 and o2["profit"] < 20 - o2["cost"]
    rep = admin.get("/api/report/monthly").get_json()[0]
    assert rep["fallos"] == 1 and rep["fallos_g"] == 50


def test_kits(admin):
    p, m = add_printer(admin), add_material(admin)
    ids = []
    for n, g in (("Cuerpo", 120), ("Tapa", 30)):
        inp = {"printer_id": p, "hours": 2, "units": 1, "materials": [{"material_id": m, "amount": g}]}
        r = admin.post("/api/calc", json=inp).get_json()
        ids.append(admin.post("/api/products", json={"name": n, "calc_json": inp, "unit_price": r["unit"]["price"],
                                                    "unit_cost": r["cost_unit"]}).get_json()["id"])
    kit = admin.post("/api/products", json={"name": "Granada", "calc_json": {}, "kind": "conjunto",
                                            "instructions": "Montar con el muelle"}).get_json()["id"]
    k = admin.put(f"/api/products/{kit}/kit", json={"items": [{"product_id": ids[0], "qty": 1}, {"product_id": ids[1], "qty": 2}],
                                                    "parts": [{"name": "Muelle", "qty": 1, "unit_cost": 0.5}]}).get_json()
    assert len(k["items"]) == 2 and k["parts_cost"] == 0.5
    b = admin.get(f"/api/products/{kit}/bundle").get_json()["calc_result"]
    assert b["materials"] and sum(x["amount"] for x in b["materials"]) == 180
    admin.post("/api/files", data={"file": (io.BytesIO(b"solid"), "tapa.stl"), "product_id": ids[1]})
    z = admin.get(f"/api/products/{kit}/download.zip")
    import zipfile
    names = zipfile.ZipFile(io.BytesIO(z.data)).namelist()
    assert "LEEME.md" in names and any(n.endswith("tapa.stl") for n in names)
    o = admin.post("/api/orders", json={"client": "X", "items": [{"description": "Granada", "qty": 1, "unit_price": 9,
                                                                    "product_id": kit, "calc_result": b}]}).get_json()
    assert any(f["name"] == "tapa.stl" for f in o["files"])           # hereda archivos de las piezas


def test_maintenance_hours_from_orders_failures_and_profiles(admin, app):
    p, m = add_printer(admin), add_material(admin)
    st = admin.put(f"/api/printers/{p}/maint", json={"profile": "prusa_mk4", "last_done": "2020-01-01T00:00:00"}).get_json()
    assert st["model"] == "prusa_mk4" and len(st["tasks"]) == 3 and st["mode"] == "app"
    inp = {"printer_id": p, "hours": 50, "units": 1, "materials": [{"material_id": m, "amount": 10}]}
    r = admin.post("/api/calc", json=inp).get_json()
    o = admin.post("/api/orders", json={"client": "X", "items": [{"description": "a", "qty": 3, "unit_price": 5,
                                                                    "calc_json": inp, "calc_result": r}]}).get_json()
    hours = lambda: next(x for x in admin.get("/api/maintenance?sync=0").get_json() if x["id"] == p)  # noqa: E731
    assert hours()["hours_total"] == 0                      # aún no se ha impreso
    admin.put(f"/api/orders/{o['id']}", json={"status": "imprimiendo"})
    h = hours()
    assert h["hours_total"] == 150 and h["prints_total"] == 3
    t200 = next(t for t in h["tasks"] if t["every_h"] == 200)
    assert t200["pct"] == 75 and t200["state"] == "ok"
    admin.post(f"/api/orders/{o['id']}/failures", json={"item_index": 0, "pct": 100})     # +50 h de un fallo
    t200 = next(t for t in hours()["tasks"] if t["every_h"] == 200)
    assert t200["state"] == "toca"
    with app.app_context():
        sent = appmod.run_notifications(send=lambda m: None)
    assert any("Revisión de ejes" in x for x in sent)
    after = admin.post(f"/api/maint/tasks/{t200['id']}/done", json={}).get_json()
    t200 = next(t for t in after["tasks"] if t["id"] == t200["id"])
    assert t200["hours_since"] == 0 and t200["state"] == "ok"
    admin.post(f"/api/printers/{p}/maint/adjust", json={"hours": 120})
    assert next(t for t in hours()["tasks"] if t["id"] == t200["id"])["hours_since"] == 120
    log = admin.get(f"/api/printers/{p}/maint/log").get_json()
    assert {x["kind"] for x in log} == {"hecho", "ajuste"}
    assert admin.post(f"/api/printers/{p}/maint/tasks", json={"name": "Cambiar FEP", "every_prints": 40}).status_code == 201


def test_maintenance_uses_moonraker_jobs(admin, app):
    p = add_printer(admin)
    admin.put(f"/api/printers/{p}", json={"conn": "moonraker", "host": "10.0.0.9"})
    with app.app_context():
        appmod._import_jobs(p, [{"job_id": "a1", "status": "completed", "end_time": 2e9, "print_duration": 7200},
                                {"job_id": "a2", "status": "cancelled", "end_time": 2e9, "print_duration": 1800},
                                {"job_id": "a3", "status": "in_progress", "end_time": None, "print_duration": 99}])
        appmod._import_jobs(p, [{"job_id": "a1", "status": "completed", "end_time": 2e9, "print_duration": 7200}])
        appmod.get_db().commit()
    m = next(x for x in admin.get("/api/maintenance?sync=0").get_json() if x["id"] == p)
    assert m["mode"] == "moonraker" and m["hours_total"] == 2.5 and m["prints_total"] == 2
    admin.put(f"/api/printers/{p}/maint", json={"hours_source": "app"})
    assert next(x for x in admin.get("/api/maintenance?sync=0").get_json() if x["id"] == p)["mode"] == "app"


def test_clients_linked_and_history(admin):
    a = admin.post("/api/orders", json={"client": "Lucía Pérez", "contact": "600111222", "items": [
        {"description": "Llavero", "qty": 2, "unit_price": 3}]}).get_json()
    b = admin.post("/api/orders", json={"client": "lucía pérez ", "status": "entregado", "items": [
        {"description": "Maceta", "qty": 1, "unit_price": 10}], "paid": True}).get_json()
    assert a["client_id"] and a["client_id"] == b["client_id"]
    anon = admin.post("/api/orders", json={"client": appmod.ANON_CLIENT}).get_json()
    assert anon["client_id"] is None
    cl = admin.get("/api/clients").get_json()
    assert len(cl) == 1 and cl[0]["phone"] == "600111222" and cl[0]["spent"] == 10 and cl[0]["owed"] == 6
    c = admin.put(f"/api/clients/{a['client_id']}", json={"name": "Lucía P."}).get_json()
    assert c["name"] == "Lucía P." and all(o["client"] == "Lucía P." for o in c["history"])
    assert admin.post("/api/clients", json={"name": "lucía p."}).status_code == 400


def test_clients_migrated_from_old_orders(app):
    with app.app_context():
        db = appmod.get_db()
        db.execute("INSERT INTO orders(created,client,contact) VALUES('2026-01-01','Marta','611')")
        db.execute("INSERT INTO orders(created,client) VALUES('2026-01-02','marta')")
        db.execute("INSERT INTO orders(created,client) VALUES('2026-01-03','Venta anónima')")
        db.execute("DELETE FROM settings WHERE key='clients_migrated'")
        db.commit()
        appmod.init_db()
        cs = appmod.rows("SELECT * FROM clients")
        assert len(cs) == 1 and cs[0]["phone"] == "611"
        assert appmod.one("SELECT COUNT(*) AS n FROM orders WHERE client_id=?", (cs[0]["id"],))["n"] == 2


def test_market_stall_sales_and_stock(admin):
    p, m = add_printer(admin), add_material(admin)
    inp = {"printer_id": p, "hours": 1, "units": 1, "materials": [{"material_id": m, "amount": 20}]}
    pid = admin.post("/api/products", json={"name": "Dragón", "calc_json": inp, "unit_price": 8, "unit_cost": 1.5,
                                            "public_price": 10}).get_json()["id"]
    mk = admin.post(f"/api/products/{pid}/make", json={"qty": 5}).get_json()
    assert mk["source"] == "stock" and mk["client"] == appmod.STOCK_CLIENT and mk["total"] == 0
    stock = lambda: next(x for x in admin.get("/api/products").get_json() if x["id"] == pid)["stock"]  # noqa: E731
    assert not stock()
    admin.put(f"/api/orders/{mk['id']}", json={"status": "listo"})
    assert stock() == 5
    ev = admin.post("/api/events", json={"name": "Mercadillo medieval", "stand_cost": 20, "cash_start": 50}).get_json()
    admin.put(f"/api/events/{ev['id']}/stock", json={"items": [{"product_id": pid, "qty": 4}]})
    s1 = admin.post("/api/sales", json={"event_id": ev["id"], "pay_method": "efectivo",
                                        "items": [{"product_id": pid, "qty": 2}]}).get_json()
    assert s1["client"] == appmod.ANON_CLIENT and s1["paid"] and s1["total"] == 20 and s1["status"] == "entregado"
    admin.post("/api/sales", json={"event_id": ev["id"], "pay_method": "bizum",
                                   "items": [{"product_id": pid, "qty": 1}, {"description": "Llavero suelto", "qty": 1, "unit_price": 3}]})
    assert stock() == 2
    e = admin.get(f"/api/events/{ev['id']}").get_json()
    assert e["count"] == 2 and e["total"] == 33 and e["by_method"] == {"efectivo": 20, "bizum": 13}
    assert e["cash_expected"] == 70 and e["goods_cost"] == 4.5 and e["profit"] == 33 - 4.5 - 20
    assert e["taken"][0]["sold"] == 3 and e["taken"][0]["left"] == 1
    admin.delete(f"/api/orders/{s1['id']}")                       # deshacer venta: vuelve al stock
    assert stock() == 4
    acc = admin.get("/api/movements").get_json()
    assert any(x["category"] == "Puestos" and x["amount"] == 20 for x in acc)
    assert admin.delete(f"/api/events/{ev['id']}").status_code == 400     # tiene ventas
    assert admin.post("/api/sales", json={"items": []}).status_code == 400


def test_octoprint_and_prusalink_status(admin, app, monkeypatch):
    p = add_printer(admin)
    admin.put(f"/api/printers/{p}", json={"conn": "octoprint", "host": "10.0.0.5"})
    calls = {"/api/job": {"state": "Printing", "job": {"file": {"name": "grip.gcode"}},
                          "progress": {"completion": 42.5, "printTime": 600, "printTimeLeft": 900}},
             "/api/printer": {"temperature": {"tool0": {"actual": 210, "target": 215}, "bed": {"actual": 60, "target": 60}}},
             "/api/v1/status": {"printer": {"state": "PRINTING", "temp_nozzle": 220, "target_nozzle": 220, "temp_bed": 70,
                                            "target_bed": 70}, "job": {"id": 3, "progress": 10, "time_remaining": 3600, "time_printing": 300}},
             "/api/v1/job": {"file": {"display_name": "caja.bgcode"}}}
    monkeypatch.setattr(appmod, "http_json", lambda pr, path, port, **kw: calls[path])
    st = admin.get("/api/printers/status").get_json()[0]
    assert st["online"] and st["state"] == "printing" and st["progress"] == 42.5 and st["remaining"] == 900
    assert st["extruder"]["target"] == 215
    admin.put(f"/api/printers/{p}", json={"conn": "prusalink"})
    st = admin.get("/api/printers/status").get_json()[0]
    assert st["state"] == "printing" and st["filename"] == "caja.bgcode" and st["bed"]["temperature"] == 70
    assert admin.get(f"/api/printers/{p}/history").get_json() == []


def test_variants_stock_sales_and_make(admin):
    p, m = add_printer(admin), add_material(admin)
    m2 = admin.post("/api/materials", json={"name": "PLA rojo", "kind": "PLA", "color": "#c00", "price": 20, "qty": 1000}).get_json()["id"]
    inp = {"printer_id": p, "hours": 1, "units": 1, "materials": [{"material_id": m, "amount": 15}]}
    pid = admin.post("/api/products", json={"name": "Llavero", "calc_json": inp, "unit_price": 3, "unit_cost": 0.6}).get_json()["id"]
    vs = admin.put(f"/api/products/{pid}/variants", json={"variants": [
        {"name": "Negro", "stock": 4}, {"name": "Rojo", "stock": 2, "price": 3.5, "material_id": m2}, {"name": "Brilla", "price": 5}]}).get_json()
    assert [v["name"] for v in vs] == ["Negro", "Rojo", "Brilla"]
    prod = lambda: next(x for x in admin.get("/api/products").get_json() if x["id"] == pid)  # noqa: E731
    assert prod()["stock"] == 6 and len(prod()["variants"]) == 3
    rojo, brilla = vs[1], vs[2]
    s = admin.post("/api/sales", json={"items": [{"product_id": pid, "variant_id": rojo["id"], "qty": 2},
                                                 {"product_id": pid, "variant_id": brilla["id"], "qty": 1}]}).get_json()
    assert s["total"] == 12 and any(i["description"] == "Llavero (Rojo)" for i in s["items"])
    v = {x["name"]: x for x in prod()["variants"]}
    assert v["Rojo"]["stock"] == 0 and v["Brilla"]["stock"] is None and prod()["stock"] == 4
    admin.delete(f"/api/orders/{s['id']}")
    assert {x["name"]: x for x in prod()["variants"]}["Rojo"]["stock"] == 2
    mk = admin.post(f"/api/products/{pid}/make", json={"qty": 3, "variant_id": rojo["id"]}).get_json()
    cr = mk["items"][0]["calc_result"]
    cr = json.loads(cr) if isinstance(cr, str) else cr
    assert mk["items"][0]["description"] == "Llavero (Rojo)" and cr["materials"][0]["material_id"] == m2
    admin.put(f"/api/orders/{mk['id']}", json={"status": "listo"})
    assert {x["name"]: x for x in prod()["variants"]}["Rojo"]["stock"] == 5 and prod()["stock"] == 9
    keep = [x for x in prod()["variants"] if x["name"] != "Brilla"]       # borrar una variante conserva las demás
    admin.put(f"/api/products/{pid}/variants", json={"variants": keep})
    assert [x["name"] for x in prod()["variants"]] == ["Negro", "Rojo"]


def test_offers_pack_nth_pct(admin):
    mk = lambda n, price, cat="": admin.post("/api/products", json={"name": n, "calc_json": {}, "unit_price": price,  # noqa: E731
                                                                     "category": cat}).get_json()["id"]
    a, b, c = mk("Llavero", 4, "Llaveros"), mk("Imán", 3, "Llaveros"), mk("Maceta", 12, "Hogar")
    assert admin.post("/api/offers", json={"name": "Mal", "kind": "pack", "qty": 1, "price": 5}).status_code == 400
    admin.post("/api/offers", json={"name": "Llaveros", "kind": "pack", "qty": 3, "price": 10, "category": "llaveros"})
    admin.post("/api/offers", json={"name": "Macetas", "kind": "nth", "qty": 2, "pct": 50, "product_id": c, "applies": "puesto"})
    items = [{"product_id": a, "qty": 3, "unit_price": 4}, {"product_id": b, "qty": 1, "unit_price": 3},
             {"product_id": c, "qty": 3, "unit_price": 12}]
    pv = admin.post("/api/offers/preview", json={"items": items, "where": "puesto"}).get_json()
    # 4 llaveros/imanes: el pack coge los 3 más caros (4+4+4=12 → 10) y deja el imán; macetas: la 2ª al 50 % (−6)
    assert pv["subtotal"] == 51 and [d["amount"] for d in pv["discounts"]] == [2, 6] and pv["total"] == 43
    pv = admin.post("/api/offers/preview", json={"items": items, "where": "pedidos"}).get_json()
    assert [d["amount"] for d in pv["discounts"]] == [2]                  # la de macetas es solo para puestos
    s = admin.post("/api/sales", json={"items": [{"product_id": c, "qty": 2}]}).get_json()
    assert s["total"] == 18 and any(i["offer_id"] for i in s["items"])
    o = admin.get("/api/offers").get_json()
    assert o[1]["text"] == "la 2ª al 50 %" and o[0]["text"] == "3 por 10 €"
    admin.post("/api/offers", json={"name": "Black Friday", "kind": "pct", "pct": 10})
    pv = admin.post("/api/offers/preview", json={"items": [{"product_id": c, "qty": 1, "unit_price": 12}], "where": "pedidos"}).get_json()
    assert pv["total"] == 10.8


def test_spool_qr_labels(admin):
    m = add_material(admin)
    sid = admin.post("/api/spools", json={"material_id": m, "brand": "Sunlu", "color_name": "Rojo", "net_g": 1000, "tare_g": 180}).get_json()
    sid = (sid[0] if isinstance(sid, list) else sid)["id"]
    r = admin.get(f"/api/spools/{sid}/qr.svg")
    assert r.status_code == 200 and r.mimetype == "image/svg+xml" and b"<svg" in r.data
    r = admin.get(f"/labels/spools?ids={sid}&size=62x29")
    assert r.status_code == 200 and b"Sunlu" in r.data and b"62mm 29mm" in r.data and b"<svg" in r.data


def test_manyfold_search_and_import(admin, app, monkeypatch, tmp_path):
    admin.put("/api/settings", json={"manyfold_url": "http://manyfold.lan:3214"})
    pages = {"/models": {"totalItems": 1, "member": [{"@id": "/models/abc", "name": "Granada M67"}]},
             "/models/abc": {"@id": "http://manyfold.lan:3214/models/abc", "name": "Granada M67",
                             "hasPart": [{"@id": "/models/abc/model_files/f1", "name": "cuerpo", "encodingFormat": "model/stl"}]},
             "/models/abc/model_files/f1": {"name": "Saiga12 Buffer 1.5", "contentUrl": "https://3d.dominio-publico.example/models/abc/model_files/cuerpo.stl?download=true"}}
    monkeypatch.setattr(appmod, "mf_get_json", lambda path, params=None: pages[path])

    def fake_dl(url, dest, limit=0):
        assert url == "/models/abc/model_files/cuerpo.stl?download=true"   # misma ruta, en el servidor configurado
        open(dest, "wb").write(b"solid x")
        return 7, "h"
    monkeypatch.setattr(appmod, "mf_download", fake_dl)
    r = admin.get("/api/manyfold/search?q=granada").get_json()
    assert r["models"][0] == {"id": "/models/abc", "name": "Granada M67", "url": "http://manyfold.lan:3214/models/abc"}
    md = admin.get("/api/manyfold/model?id=/models/abc").get_json()
    assert md["files"][0]["id"] == "/models/abc/model_files/f1"
    pid = admin.post("/api/products", json={"name": "Granada", "calc_json": {}}).get_json()["id"]
    imp = admin.post("/api/manyfold/import", json={"product_id": pid, "model_id": "/models/abc", "file_ids": [md["files"][0]["id"]]}).get_json()
    assert imp["imported"][0]["name"] == "Saiga12 Buffer 1.5.stl" and imp["imported"][0]["note"] == "de Manyfold"
    assert next(x for x in admin.get("/api/products").get_json() if x["id"] == pid)["manyfold_id"] == "/models/abc"
    with app.test_request_context():
        appmod.get_db  # noqa: B018
    # no deja salir a otro servidor
    with app.app_context():
        import pytest as _pt
        with _pt.raises(appmod.ManyfoldError):
            appmod._mf_url("http://evil.example/x")
    assert "manyfold_client_secret" in appmod.SECRET_SETTINGS


def test_filament_forecast(admin, app):
    p, m = add_printer(admin), add_material(admin)
    admin.put(f"/api/materials/{m}", json={"track_stock": 1, "low_stock": 100})
    admin.post("/api/spools", json={"material_id": m, "brand": "X", "net_g": 1000, "tare_g": 200})
    inp = {"printer_id": p, "hours": 1, "units": 1, "materials": [{"material_id": m, "amount": 300}]}
    r = admin.post("/api/calc", json=inp).get_json()
    done = admin.post("/api/orders", json={"client": "A", "status": "entregado", "items": [
        {"description": "x", "qty": 2, "unit_price": 1, "calc_json": inp, "calc_result": r}]}).get_json()
    assert done
    admin.post("/api/orders", json={"client": "B", "status": "recibido", "items": [
        {"description": "y", "qty": 2, "unit_price": 1, "calc_json": inp, "calc_result": r}]})
    fc = next(x for x in admin.get("/api/forecast").get_json()["materials"] if x["id"] == m)
    assert fc["stock"] == 400 and fc["pending"] == 600 and fc["left"] == -200 and fc["status"] == "falta"
    assert fc["rate_day"] == 10 and fc["buy_units"] >= 1
    with app.app_context():
        sent = appmod.run_notifications(send=lambda x: None)
    assert any("No llega" in x for x in sent)
    d = admin.get("/api/dashboard").get_json()
    assert d["forecast"][0]["id"] == m


def test_prices_history_and_shopping_list(admin):
    p, m = add_printer(admin), add_material(admin)
    admin.put(f"/api/materials/{m}", json={"qty": 1000, "price": 20})
    admin.post("/api/spools", json={"material_id": m, "brand": "Sunlu", "net_g": 1000, "tare_g": 160, "count": 2,
                                    "paid_total": 36, "supplier": "Amazon"})
    admin.post("/api/spools", json={"material_id": m, "brand": "eSun", "net_g": 1000, "tare_g": 200, "count": 1,
                                    "paid_total": 21, "supplier": "Filamentos.es", "update_price": False})
    pr = admin.get(f"/api/materials/{m}/prices").get_json()
    assert [h["per_kg"] for h in pr["history"]] == [21, 18] and pr["min"] == 18 and pr["suppliers"][0] == {"supplier": "Amazon", "best_per_kg": 18}
    assert next(x for x in admin.get("/api/materials").get_json() if x["id"] == m)["price"] == 18   # la 2ª no tocó el precio
    assert set(admin.get("/api/suppliers").get_json()) == {"Amazon", "Filamentos.es"}
    # un pedido pendiente que no cabe en el stock → sugerencia en la lista de la compra
    inp = {"printer_id": p, "hours": 1, "units": 1, "materials": [{"material_id": m, "amount": 2000}]}
    r = admin.post("/api/calc", json=inp).get_json()
    admin.post("/api/orders", json={"client": "A", "status": "recibido", "items": [{"description": "x", "qty": 2, "unit_price": 1,
                                                                                  "calc_json": inp, "calc_result": r}]})
    sh = admin.get("/api/shopping").get_json()
    sg = sh["suggestions"][0]
    assert sg["material_id"] == m and sg["units"] >= 1 and sg["supplier"] == "Filamentos.es" and sg["est_price"] == 21
    it = admin.post("/api/shopping", json={"material_id": m, "units": 2}).get_json()
    assert it["supplier"] == "Filamentos.es" and it["est_price"] == 21 and it["total"] == 42
    admin.post("/api/shopping", json={"text": "Boquillas 0.4", "units": 3, "est_price": 2, "supplier": "AliExpress"})
    sh = admin.get("/api/shopping").get_json()
    assert sh["total"] == 48 and not sh["suggestions"]
    # comprado al añadir las bobinas desde la lista
    admin.post("/api/spools", json={"material_id": m, "brand": "eSun", "net_g": 1000, "count": 2, "paid_total": 40,
                                    "supplier": "Filamentos.es", "shopping_id": it["id"]})
    sh = admin.get("/api/shopping").get_json()
    assert len(sh["items"]) == 1 and sh["done"][0]["id"] == it["id"]
    assert admin.post("/api/shopping", json={}).status_code == 400


def test_recurring_expenses(admin, app):
    from datetime import date as D
    today = D.today()
    start = f"{today.year - 1:04d}-{today.month:02d}"
    r = admin.post("/api/recurring", json={"concept": "Cuota de autónomo", "amount": 86.43, "category": "Autónomo",
                                           "person": "Ana", "every": "mensual", "day": 1, "start": start}).get_json()
    assert r["booked"] == 13                                 # de hace un año a este mes, ambos incluidos
    admin.post("/api/recurring", json={"concept": "Dominio", "amount": 12, "every": "anual", "day": 28, "start": start})
    lst = admin.get("/api/recurring").get_json()
    cuota = next(x for x in lst["items"] if x["concept"] == "Cuota de autónomo")
    assert cuota["booked"]["n"] == 13 and cuota["next"] > today.isoformat() and lst["per_month"] == 86.43 + 1
    mv = [x for x in admin.get("/api/movements").get_json() if x.get("recurring_id") == cuota["id"]]
    assert len(mv) == 13 and all(x["kind"] == "gasto" and x["category"] == "Autónomo" for x in mv)
    with app.app_context():
        assert appmod.run_recurring() == 0                      # no se duplica
        assert appmod.run_recurring(D(today.year + 1, today.month, 28)) >= 12   # al pasar el tiempo se apuntan solos
    admin.put(f"/api/recurring/{cuota['id']}", json={"active": False})
    assert admin.post("/api/recurring", json={"concept": "", "amount": 5}).status_code == 400
    admin.delete(f"/api/recurring/{cuota['id']}")
    assert len([x for x in admin.get("/api/movements").get_json() if x["concept"] == "Cuota de autónomo"]) >= 13   # lo apuntado se queda


def test_global_search(admin):
    m = add_material(admin)
    o = admin.post("/api/orders", json={"client": "Lucía Pérez", "items": [{"description": "Soporte de auriculares", "qty": 1, "unit_price": 9}]}).get_json()
    pid = admin.post("/api/products", json={"name": "Llavero dragón", "calc_json": {}, "sku": "LL-01"}).get_json()["id"]
    admin.put(f"/api/products/{pid}/variants", json={"variants": [{"name": "Fosforito"}]})
    sp = admin.post("/api/spools", json={"material_id": m, "brand": "Sunlu", "color_name": "Rojo fuego", "net_g": 1000}).get_json()
    sp = (sp[0] if isinstance(sp, list) else sp)["id"]
    t = lambda q: [(x["type"], x["id"]) for x in admin.get("/api/search?q=" + q).get_json()["results"]]  # noqa: E731
    assert ("order", o["id"]) in t("auriculares") and ("client", o["client_id"]) in t("lucía")
    assert ("product", pid) in t("fosforito") and ("product", pid) in t("ll-01")
    assert ("spool", sp) in t("rojo fuego") and ("order", o["id"]) in t(f"%23{o['id']}")
    assert admin.get("/api/search?q=").get_json()["results"] == []


def test_spools_create_material_on_the_fly(admin):
    client = admin
    r = client.post("/api/spools", json={"material_id": "new", "new_material": {"name": "PLA verde", "kind": "PLA"},
                                         "brand": "Sunlu", "color_name": "Verde", "net_g": 1000, "count": 2, "paid_total": 36})
    assert r.status_code == 201 and len(r.get_json()) == 2
    mid = int(r.headers["X-Material-Created"])
    m = [x for x in client.get("/api/materials").get_json() if x["id"] == mid][0]
    assert m["name"] == "PLA verde" and m["price"] == 18 and m["unit"] == "g" and m["track_stock"] == 1
    # mismo nombre: se reutiliza, no se duplica
    r = client.post("/api/spools", json={"material_id": "new", "new_material": {"name": "pla verde"}, "count": 1})
    assert r.status_code == 201 and "X-Material-Created" not in r.headers and r.get_json()[0]["material_id"] == mid
    r = client.post("/api/spools", json={"material_id": "new", "new_material": {"name": "Resina gris", "kind": "Resina"}, "net_g": 500})
    m = [x for x in client.get("/api/materials").get_json() if x["name"] == "Resina gris"][0]
    assert m["unit"] == "ml" and m["qty"] == 500
    assert client.post("/api/spools", json={"material_id": "new", "new_material": {"name": ""}}).status_code == 400


def test_parse_spool_titles(admin, monkeypatch):
    import app as A
    r = admin.post("/api/spools/parse", json={"text": "SUNLU Filamento PLA 1.75mm 4kg, Bobina de 1kg, Pack de 4, Negro+Blanco+Gris+Rojo 59,99 €"}).get_json()
    assert r["brand"] == "Sunlu" and r["kind"] == "PLA" and r["count"] == 4 and r["net_g"] == 1000 and r["price"] == 59.99
    assert r["colors"] == ["Negro", "Blanco", "Gris", "Rojo"]
    r = admin.post("/api/spools/parse", json={"text": "ELEGOO PLA Plus Filament 1.75mm 2KG, 2 x 1kg, Black"}).get_json()
    assert r["kind"] == "PLA+" and r["count"] == 2 and r["net_g"] == 1000 and r["color_name"] == "Negro"
    r = admin.post("/api/spools/parse", json={"text": "Filamento PETG 1,75 mm, Jayo PETG 1,1 kg, azul marino"}).get_json()
    assert r["brand"] == "Jayo" and r["kind"] == "PETG" and r["net_g"] == 1100 and r["colors"] == ["Azul marino"]
    assert admin.post("/api/spools/parse", json={"text": "ANYCUBIC Resina Standard Gris 1000g"}).get_json()["unit"] == "ml"
    assert admin.post("/api/spools/parse", json={"text": "ZIROTECH PLA 1kg rojo"}).get_json()["brand"] == "Zirotech"

    # enlace de Amazon que no se deja leer: se saca del propio enlace
    def boom(*a, **k):
        raise A.urllib.error.URLError("captcha")
    monkeypatch.setattr(A, "fetch_shop", boom)
    r = admin.post("/api/spools/parse", json={"text": "https://www.amazon.es/SUNLU-Filamento-PETG-1-75mm-Blanco/dp/B07XG3R6KC/ref=sr_1_3"}).get_json()
    assert r["brand"] == "Sunlu" and r["kind"] == "PETG" and r["color_name"] == "Blanco" and r["supplier"] == "Amazon" and r["note"]
    # nada de pedir direcciones internas
    called = []
    monkeypatch.setattr(A, "fetch_shop", lambda *a, **k: called.append(a))
    r = admin.post("/api/spools/parse", json={"text": "http://192.168.1.10/admin PLA negro"}).get_json()
    assert not called and r["kind"] == "PLA" and "Amazon" in r["note"]
    assert not A._shop_url_ok("https://amazon.es.evil.com/x") and A._shop_url_ok("https://amzn.eu/d/abc")


def test_components_locations_bom_needs(admin):
    m = add_material(admin)
    # ubicaciones anidadas
    shelf = admin.post("/api/locations", json={"name": "Estantería taller", "kind": "estantería"}).get_json()["id"]
    box = admin.post("/api/locations", json={"name": "Caja tornillería", "kind": "caja", "parent_id": shelf}).get_json()
    assert box["path"] == "Estantería taller › Caja tornillería"
    assert admin.put(f"/api/locations/{shelf}", json={"parent_id": box["id"]}).status_code == 400   # sin ciclos
    # componente: coste por unidad desde el pack, stock inicial, compra con gasto, recuento
    c = admin.post("/api/components", json={"name": "Tornillo M3x10", "pack_qty": 100, "pack_price": 5, "stock": 40,
                                            "min_stock": 20, "location_id": box["id"]}).get_json()
    assert c["unit_cost"] == 0.05 and c["stock"] == 40 and c["location"].endswith("Caja tornillería")
    sp = admin.post("/api/components", json={"name": "Muelle 0.8", "unit_cost": 0.2, "stock": 3}).get_json()
    c = admin.post(f"/api/components/{c['id']}/stock", json={"mode": "compra", "packs": 1, "paid": 6}).get_json()
    assert c["stock"] == 140 and c["unit_cost"] == 0.06
    c = admin.post(f"/api/components/{c['id']}/stock", json={"mode": "ajuste", "qty": 130}).get_json()
    assert c["stock"] == 130
    # receta en una pieza: 4 tornillos + 2 muelles → el coste del producto los incluye
    pid = admin.post("/api/products", json={"name": "Grip", "calc_json": json.dumps({"hours": 1, "materials": [{"material_id": m, "amount": 50}]})}).get_json()["id"]
    k = admin.put(f"/api/products/{pid}/kit", json={"parts": [{"component_id": c["id"], "qty": 4}, {"component_id": sp["id"], "qty": 2},
                                                             {"name": "Pegamento", "qty": 1, "unit_cost": 0.1}]}).get_json()
    assert round(k["parts_cost"], 2) == round(4 * 0.06 + 2 * 0.2 + 0.1, 2)
    prod = [p for p in admin.get("/api/products").get_json() if p["id"] == pid][0]
    assert prod["kind"] != "conjunto"
    base = admin.post("/api/calc", json={"hours": 1, "materials": [{"material_id": m, "amount": 50}]}).get_json()["cost_unit"]
    assert abs(prod["unit_cost"] - (base + k["parts_cost"])) < 0.02
    # ¿qué me falta para 5? muelles: 10 hacen falta, hay 3
    nd = admin.get(f"/api/products/{pid}/needs?qty=5").get_json()
    muelle = [x for x in nd["lines"] if x["type"] == "component" and x["id"] == sp["id"]][0]
    assert muelle["need"] == 10 and muelle["missing"] == 7 and not nd["ok"]
    assert any(x["type"] == "material" and x["need"] == 250 for x in nd["lines"])
    r = admin.post(f"/api/products/{pid}/needs/shop", json={"qty": 5}).get_json()
    assert "Muelle 0.8" in r["added"]
    shop = admin.get("/api/shopping").get_json()
    assert any(i["component_id"] == sp["id"] and i["material"] == "Muelle 0.8" for i in shop["items"])
    # fabricar para stock: al imprimir se gastan los componentes; al cancelar vuelven
    o = admin.post(f"/api/products/{pid}/make", json={"qty": 2}).get_json()
    admin.put(f"/api/orders/{o['id']}", json={"status": "imprimiendo"})
    comps = {x["id"]: x for x in admin.get("/api/components").get_json()}
    assert comps[c["id"]]["stock"] == 130 - 8 and comps[sp["id"]]["stock"] == 3 - 4
    admin.put(f"/api/orders/{o['id']}", json={"status": "cancelado"})
    comps = {x["id"]: x for x in admin.get("/api/components").get_json()}
    assert comps[c["id"]]["stock"] == 130
    # ventas de puesto no gastan componentes
    admin.put(f"/api/products/{pid}", json={"stock": 5, "min_stock": 8, "location_id": box["id"]})
    admin.post("/api/sales", json={"items": [{"product_id": pid, "qty": 1}]})
    comps = {x["id"]: x for x in admin.get("/api/components").get_json()}
    assert comps[c["id"]]["stock"] == 130
    # reposición: hay 4 y el mínimo es 8
    rs = admin.get("/api/restock").get_json()
    assert rs[0]["id"] == pid and rs[0]["make"] == 4
    # contenido de la caja y buscador «dónde está»
    det = admin.get(f"/api/locations/{box['id']}").get_json()
    assert [x["name"] for x in det["components"]] == ["Tornillo M3x10"] and det["products"][0]["id"] == pid
    res = admin.get("/api/search?q=m3x").get_json()["results"]
    assert res[0]["type"] == "component" and "Caja tornillería" in res[0]["sub"]
    assert admin.get(f"/labels/locations?ids={box['id']}").status_code == 200
    # borrar la estantería: la caja sube de nivel; borrar el componente: la receta conserva el nombre
    admin.delete(f"/api/locations/{shelf}")
    assert admin.get(f"/api/locations/{box['id']}").get_json()["path"] == "Caja tornillería"
    admin.delete(f"/api/components/{c['id']}")
    parts = admin.get(f"/api/products/{pid}/kit").get_json()["parts"]
    assert any(p["name"] == "Tornillo M3x10" and p["component_id"] is None for p in parts)


def test_component_parse(admin):
    r = admin.post("/api/components/parse", json={"text": "Tornillos M3 x 10 mm DIN912 acero inoxidable, 100 piezas, 7,99 €"}).get_json()
    assert r["pieces"] == 100 and r["price"] == 7.99 and r["name"].startswith("Tornillos M3")
    r = admin.post("/api/components/parse", json={"text": "Imanes de neodimio 6x2 mm, pack de 50"}).get_json()
    assert r["pieces"] == 50
