#!/usr/bin/env python3
"""Rellena una instalación vacía con datos de ejemplo (para capturas o para probar).
   MT_DATA_DIR=/tmp/demo python3 tools/demo_data.py      → usuario demo / demo1234
"""
import os
import sys
import random
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import app as A  # noqa: E402

random.seed(3)
c = A.app.test_client()
with A.app.app_context():
    tok = A.setup_token(create=True)
r = c.post("/api/setup", json={
    "token": tok, "admin": {"username": "demo", "password": "demo1234"}, "shop_name": "Filamento & Co.",
    "people": ["Ana", "Luis"], "kwh_price": 0.19, "margin_pct": 60, "apply_vat": True, "vat_pct": 21,
    "printers": [{"name": "Prusa MK4", "watts": 120, "cost": 1100}, {"name": "Bambu P1S", "watts": 150, "cost": 800},
                 {"name": "Elegoo Saturn", "watts": 70, "cost": 350}],
    "materials": [{"name": "PLA negro", "kind": "PLA", "color": "Negro", "price": 19, "qty": 1000},
                  {"name": "PLA blanco", "kind": "PLA", "color": "Blanco", "price": 19, "qty": 1000},
                  {"name": "PETG naranja", "kind": "PETG", "color": "Naranja", "price": 22, "qty": 1000},
                  {"name": "Resina gris", "kind": "Resina", "price": 32, "qty": 1000, "unit": "ml"}]})
assert r.status_code == 200, r.get_json()
c.put("/api/settings", json={"shop_tagline": "Piezas impresas a medida", "min_price": 2, "rounding": "0.50"})
P = {p["name"]: p["id"] for p in c.get("/api/printers").get_json()}
M = {m["name"]: m["id"] for m in c.get("/api/materials").get_json()}
for name, amt in [("PLA negro", 2600), ("PLA blanco", 340), ("PETG naranja", 1800), ("Resina gris", 900)]:
    c.post(f"/api/materials/{M[name]}/stock", json={"mode": "ajuste", "amount": amt})
c.put(f"/api/materials/{M['PLA blanco']}", json={"low_stock": 400})

items = [("Soporte de auriculares", "Prusa MK4", 4.2, [("PLA negro", 96)], 1, 10, 10),
         ("Maceta geométrica", "Bambu P1S", 3.1, [("PLA blanco", 74)], 1, 5, 5),
         ("Llavero personalizado", "Bambu P1S", 1.5, [("PETG naranja", 28)], 8, 10, 5),
         ("Miniatura 32 mm", "Elegoo Saturn", 2.5, [("Resina gris", 18)], 6, 10, 20),
         ("Organizador de cajón", "Prusa MK4", 6.8, [("PETG naranja", 210)], 1, 5, 5)]
prods = []
for name, pr, h, mats, units, prep, post in items:
    inp = {"printer_id": P[pr], "hours": int(h), "minutes": round(h % 1 * 60), "units": units, "prep_min": prep,
           "post_min": post, "materials": [{"material_id": M[m], "amount": a} for m, a in mats]}
    res = c.post("/api/calc", json=inp).get_json()
    pid = c.post("/api/products", json={"name": name, "calc_json": inp, "unit_price": res["unit"]["price"],
                                        "unit_cost": res["cost_unit"], "category": "Hogar" if "Miniatura" not in name else "Juegos",
                                        "print_info": {"printer": pr, "layer_height": "0.2" if pr != "Elegoo Saturn" else "0.05"}}).get_json()["id"]
    prods.append((name, inp, res, pid))

clients = ["Marta G.", "Taller Robles", "Javi", "Lucía P.", "Club de rol", "Sergio", "Carmen", "Pablo R."]
channels = ["Wallapop", "Instagram", "Directo", "Etsy"]
today = date.today()
db_dates = []
for i in range(26):
    name, inp, res, pid = random.choice(prods)
    qty = random.choice([1, 1, 2, res["units"]])
    status = random.choice(["entregado"] * 4 + ["listo", "imprimiendo", "recibido"])
    o = c.post("/api/orders", json={"client": random.choice(clients), "channel": random.choice(channels), "status": status,
                                    "assigned": random.choice(["Ana", "Luis"]),
                                    "items": [{"description": name, "qty": qty, "unit_price": res["unit"]["price"],
                                               "unit_cost": res["cost_unit"], "calc_json": inp, "calc_result": res,
                                               "product_id": pid}]}).get_json()
    d = today - timedelta(days=random.randint(0, 150))
    db_dates.append((o["id"], d))
    if status == "entregado":
        c.put(f"/api/orders/{o['id']}", json={"paid": True, "paid_to": random.choice(["Ana", "Luis"]), "paid_date": d.isoformat()})
with A.app.app_context():
    db = A.get_db()
    for oid, d in db_dates:
        db.execute("UPDATE orders SET created=? WHERE id=?", (d.isoformat() + "T12:00:00", oid))
        db.execute("UPDATE movements SET date=? WHERE order_id=?", (d.isoformat(), oid))
    db.commit()
for i, (cat, concept, amt) in enumerate([("Filamento", "4 bobinas PLA", 76), ("Embalaje", "Cajas y bolsas", 23.5),
                                         ("Repuestos", "Boquillas 0.4", 18), ("Resina", "Resina gris 1 L", 32),
                                         ("Envíos", "Correos", 14.9)]):
    c.post("/api/movements", json={"date": (today - timedelta(days=20 * i + 3)).isoformat(), "kind": "gasto",
                                   "category": cat, "concept": concept, "amount": amt, "person": ["Ana", "Luis"][i % 2]})
# almacén de bobinas
for mat, brand, cname, hexc, n, loc in [("PLA negro", "Sunlu", "Negro", "#1a1a1a", 2, "Estante 1"), ("PLA blanco", "Sunlu", "Blanco", "#f4f4f0", 1, "Estante 1"),
                                        ("PLA negro", "eSun", "Gris", "#8a8d8f", 1, "Estante 2"), ("PETG naranja", "Bambu", "Naranja", "#e8572a", 2, "Estante 2"),
                                        ("PLA blanco", "Sunlu", "Rojo", "#c62828", 1, "Caja A"), ("PLA blanco", "eSun", "Verde oliva", "#556b2f", 1, "Caja A"),
                                        ("Resina gris", "Elegoo", "Gris", "#9e9e9e", 1, "Armario")]:
    c.post("/api/spools", json={"material_id": M[mat], "brand": brand, "color_name": cname, "color_hex": hexc, "count": n,
                                "net_g": 1000, "location": loc, "tare_g": {"Sunlu": 160, "eSun": 225, "Bambu": 250}.get(brand)})
sps = c.get("/api/spools").get_json()
c.post(f"/api/spools/{sps[0]['id']}/weigh", json={"gross": 540})
c.post(f"/api/spools/{sps[2]['id']}/weigh", json={"gross": 380})
# conjunto: granada de airsoft
gr = []
for name, g, h in [("Cuerpo granada", 85, 3.2), ("Tapa granada", 18, 0.8), ("Anilla y seguro", 6, 0.4)]:
    inp = {"printer_id": P["Bambu P1S"], "hours": int(h), "minutes": round(h % 1 * 60), "units": 1,
           "materials": [{"material_id": M["PLA blanco"], "amount": g}]}
    res = c.post("/api/calc", json=inp).get_json()
    gr.append(c.post("/api/products", json={"name": name, "calc_json": inp, "unit_price": res["unit"]["price"], "unit_cost": res["cost_unit"],
                                            "category": "Airsoft", "print_info": {"layer_height": "0.2", "infill": "40%"}}).get_json()["id"])
kit = c.post("/api/products", json={"name": "Granada de airsoft M67", "calc_json": {}, "kind": "conjunto", "category": "Airsoft",
                                    "instructions": "1. Imprime el cuerpo de pie, sin soportes.\n2. Inserta el muelle en la tapa.\n3. Pega la anilla con cianoacrilato."}).get_json()["id"]
k = c.put(f"/api/products/{kit}/kit", json={"items": [{"product_id": gr[0], "qty": 1}, {"product_id": gr[1], "qty": 1, "notes": "mismo color"},
                                                        {"product_id": gr[2], "qty": 1, "notes": "en rojo"}],
                                              "parts": [{"name": "Muelle 0,8 × 20 mm", "qty": 1, "unit_cost": 0.35}, {"name": "Tornillo M3 × 12", "qty": 2, "unit_cost": 0.05}]}).get_json()
c.put(f"/api/products/{kit}", json={"unit_price": k["suggested_price"]})
# estados variados y un fallo
os_ = c.get("/api/orders").get_json()
for o, st in zip([o for o in os_ if o["status"] in ("recibido", "imprimiendo")][:4], ["programado", "postprocesado", "programado", "recibido"]):
    c.put(f"/api/orders/{o['id']}", json={"status": st})
pr = next((o for o in c.get("/api/orders").get_json() if o["status"] == "imprimiendo" and o["items"][0].get("calc_result")), None)
if pr:
    c.post(f"/api/orders/{pr['id']}/failures", json={"item_index": 0, "pct": 35, "cause": "se despegó de la cama"})
c.put("/api/settings", json={"status_limits_h": {"recibido": 24, "programado": 72, "imprimiendo": 48, "postprocesado": 48, "listo": 72, "presupuesto": 168}})
# mantenimiento: perfiles de fabricante; la última revisión hace un tiempo
c.put(f"/api/printers/{P['Prusa MK4']}/maint", json={"profile": "prusa_mk4", "last_done": (today - timedelta(days=70)).isoformat() + "T00:00:00"})
c.put(f"/api/printers/{P['Bambu P1S']}/maint", json={"profile": "bambu_xp", "last_done": (today - timedelta(days=80)).isoformat() + "T00:00:00"})
c.post(f"/api/printers/{P['Prusa MK4']}/maint/adjust", json={"hours": 168, "at": (today - timedelta(days=60)).isoformat() + "T12:00:00",
                                                           "note": "lo que llevaba antes de usar MiTallercito"})
c.post(f"/api/printers/{P['Bambu P1S']}/maint/adjust", json={"hours": 640, "at": (today - timedelta(days=60)).isoformat() + "T12:00:00"})
# stock de producto y un puesto en un mercadillo
prods = {p["name"]: p for p in c.get("/api/products").get_json()}
for name, n in (("Llavero personalizado", 25), ("Maceta geométrica", 8), ("Miniatura 32 mm", 12), ("Granada de airsoft M67", 6)):
    if name in prods:
        c.put(f"/api/products/{prods[name]['id']}", json={"stock": n, "public_price": round(prods[name]["unit_price"] * 1.2, 1)})
# variantes y ofertas
if "Llavero personalizado" in prods:
    lid = prods["Llavero personalizado"]["id"]
    c.put(f"/api/products/{lid}/variants", json={"variants": [{"name": "Negro", "color_hex": "#222222", "stock": 9},
        {"name": "Blanco", "color_hex": "#f2f2f2", "stock": 7}, {"name": "Verde", "color_hex": "#3fae6a", "stock": 6},
        {"name": "Brilla en la oscuridad", "color_hex": "#c8f7a6", "stock": 3, "price": 4.5}]})
    prods = {p["name"]: p for p in c.get("/api/products").get_json()}
c.post("/api/offers", json={"name": "Llaveros", "kind": "pack", "qty": 3, "price": 6, "product_id": prods.get("Llavero personalizado", {}).get("id")})
c.post("/api/offers", json={"name": "Macetas", "kind": "nth", "qty": 2, "pct": 50, "product_id": prods.get("Maceta geométrica", {}).get("id"),
                            "applies": "puesto"})
ev = c.post("/api/events", json={"name": "Mercadillo medieval", "date": today.isoformat(), "place": "Plaza Mayor",
                                 "stand_cost": 15, "cash_start": 40}).get_json()
c.put(f"/api/events/{ev['id']}/stock", json={"items": [{"product_id": prods[n]["id"], "qty": q} for n, q in
                                                        (("Llavero personalizado", 20), ("Maceta geométrica", 6), ("Miniatura 32 mm", 10)) if n in prods]})
for items, pay in ((["Llavero personalizado", "Llavero personalizado"], "efectivo"), (["Miniatura 32 mm"], "bizum"),
                   (["Maceta geométrica", "Llavero personalizado"], "tarjeta"), (["Miniatura 32 mm", "Miniatura 32 mm"], "efectivo"), (["Maceta geométrica", "Maceta geométrica"], "bizum"), (["Llavero personalizado"] * 4, "efectivo")):
    c.post("/api/sales", json={"event_id": ev["id"], "pay_method": pay, "paid_to": random.choice(["Ana", "Luis"]),
                               "items": [{"product_id": prods[n]["id"], "qty": 1,
                                         "variant_id": (random.choice(prods[n]["variants"])["id"] if prods[n].get("variants") else None)}
                                        for n in items if n in prods]})
# organización de casa: ubicaciones, componentes y recetas
shelf = c.post("/api/locations", json={"name": "Estantería del taller", "kind": "estantería"}).get_json()["id"]
draw = c.post("/api/locations", json={"name": "Cajonera azul", "kind": "cajonera", "parent_id": shelf}).get_json()["id"]
d1 = c.post("/api/locations", json={"name": "Cajón 1 · tornillería", "kind": "cajón", "parent_id": draw}).get_json()["id"]
d2 = c.post("/api/locations", json={"name": "Cajón 2 · muelles e imanes", "kind": "cajón", "parent_id": draw}).get_json()["id"]
dry = c.post("/api/locations", json={"name": "Caja seca de filamento", "kind": "caja", "parent_id": shelf}).get_json()["id"]
fin = c.post("/api/locations", json={"name": "Caja de producto terminado", "kind": "caja"}).get_json()["id"]
CP = {}
for name, cat, pq, pp, st, mn, loc in (("Tornillo M3 × 12 DIN912", "Tornillería", 100, 6.5, 64, 30, d1), ("Tornillo M3 × 8", "Tornillería", 100, 5.9, 12, 30, d1),
                                       ("Inserto térmico M3", "Tornillería", 100, 8.99, 150, 40, d1), ("Muelle 0,8 × 20 mm", "Muelles", 50, 9.5, 4, 10, d2),
                                       ("Imán neodimio 6 × 2 mm", "Imanes", 100, 7.99, 86, 20, d2), ("Anilla metálica 25 mm", "Llaveros", 200, 6.0, 140, 50, d2),
                                       ("Bolsa zip 8 × 12", "Embalaje", 500, 7.5, 320, 100, fin)):
    CP[name] = c.post("/api/components", json={"name": name, "category": cat, "pack_qty": pq, "pack_price": pp, "stock": st,
                                               "min_stock": mn, "location_id": loc, "supplier": "Amazon"}).get_json()["id"]
for sp in c.get("/api/spools").get_json()[:4]:
    c.put(f"/api/spools/{sp['id']}/location", json={"location_id": dry})
prods = {p["name"]: p for p in c.get("/api/products").get_json()}
if "Granada de airsoft M67" in prods:
    gid = prods["Granada de airsoft M67"]["id"]
    kk = c.get(f"/api/products/{gid}/kit").get_json()
    c.put(f"/api/products/{gid}/kit", json={"items": [{"product_id": i["product_id"], "qty": i["qty"], "notes": i["notes"]} for i in kk["items"]],
                                            "parts": [{"component_id": CP["Muelle 0,8 × 20 mm"], "qty": 1}, {"component_id": CP["Tornillo M3 × 12 DIN912"], "qty": 2},
                                                      {"component_id": CP["Bolsa zip 8 × 12"], "qty": 1}, {"name": "Cianoacrilato", "qty": 0.05, "unit_cost": 4}]})
    c.put(f"/api/products/{gid}", json={"min_stock": 10, "location_id": fin})
for name, parts, mn in (("Llavero personalizado", [("Anilla metálica 25 mm", 1), ("Bolsa zip 8 × 12", 1)], 30),
                        ("Soporte de auriculares", [("Inserto térmico M3", 2), ("Tornillo M3 × 8", 2), ("Imán neodimio 6 × 2 mm", 4)], 3)):
    if name in prods:
        c.put(f"/api/products/{prods[name]['id']}/kit", json={"parts": [{"component_id": CP[n], "qty": q} for n, q in parts]})
        c.put(f"/api/products/{prods[name]['id']}", json={"min_stock": mn, "location_id": fin})
print("Datos de ejemplo creados. Usuario: demo / demo1234")
