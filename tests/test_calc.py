"""La calculadora es lo más delicado: estos tests fijan las fórmulas."""
import pytest

from conftest import add_material, add_printer

BASE = {"waste_pct": 0, "fail_pct": 0, "margin_pct": 0, "commission_pct": 0, "commission_fixed": 0,
        "min_price": 0, "rounding": "none", "apply_vat": False}


@pytest.fixture()
def setup(admin):
    admin.put("/api/settings", json={"kwh_price": 0.25, "prep_rate": 12, "post_rate": 12})
    return admin, add_printer(admin), add_material(admin)


def calc(c, **d):
    return c.post("/api/calc", json={**BASE, **d}).get_json()


def test_material_cost(setup):
    c, p, m = setup
    r = calc(c, materials=[{"material_id": m, "amount": 100}])   # 100 g a 20 €/kg
    assert r["breakdown"]["material"] == pytest.approx(2.0)
    assert r["cost"] == pytest.approx(2.0)


def test_electricity_and_machine(setup):
    c, p, m = setup
    r = calc(c, printer_id=p, hours=2)
    b = r["breakdown"]
    assert b["electricidad"] == pytest.approx(0.2 * 2 * 0.25)            # 200 W · 2 h · 0,25 €/kWh
    assert b["amortizacion"] == pytest.approx(1000 / (10 * 30 * 10) * 2, abs=1e-3)  # vida útil 3000 h
    assert b["mantenimiento"] == pytest.approx(30 / (30 * 10) * 2, abs=1e-3)


def test_labor(setup):
    c, p, m = setup
    r = calc(c, prep_min=30, post_min=15)
    assert r["breakdown"]["preparacion"] == pytest.approx(6)
    assert r["breakdown"]["postprocesado"] == pytest.approx(3)


def test_margin_and_units(setup):
    c, p, m = setup
    r = calc(c, materials=[{"material_id": m, "amount": 100}], margin_pct=50, units=4)
    assert r["unit"]["price"] == pytest.approx(0.75)                     # (2 € · 1,5) / 4
    assert r["cost_unit"] == pytest.approx(0.5)


def test_vat_b2c_included_and_b2b_apart(setup):
    c, p, m = setup
    b2c = calc(c, materials=[{"material_id": m, "amount": 500}], apply_vat=True, vat_pct=21, sale_type="B2C")
    assert b2c["unit"]["price"] == pytest.approx(12.1)
    assert b2c["unit"]["price_ex_vat"] == pytest.approx(10)
    b2b = calc(c, materials=[{"material_id": m, "amount": 500}], apply_vat=True, vat_pct=21, sale_type="B2B")
    assert b2b["unit"]["price"] == pytest.approx(10)
    assert b2b["unit"]["price_inc_vat"] == pytest.approx(12.1)


@pytest.mark.parametrize("mode,expected", [("none", 2.34), ("0.99", 2.99), ("0.50", 2.5), ("1.00", 3.0)])
def test_rounding(setup, mode, expected):
    c, p, m = setup
    r = calc(c, materials=[{"material_id": m, "amount": 117}], rounding=mode)
    assert r["unit"]["price"] == pytest.approx(expected)


def test_min_price_flagged(setup):
    c, p, m = setup
    r = calc(c, materials=[{"material_id": m, "amount": 10}], min_price=3)
    assert r["unit"]["price"] == 3
    assert r["unit"]["min_applied"] is True
    assert r["unit"]["raw"] == pytest.approx(0.2)


def test_commission_keeps_net(setup):
    c, p, m = setup
    r = calc(c, materials=[{"material_id": m, "amount": 500}], commission_pct=10, commission_fixed=1)
    net = r["unit"]["price"] * (1 - 0.10) - 1
    assert net == pytest.approx(10, abs=0.01)                             # tras la comisión queda el coste+margen


def test_direct_mode_uses_slicer_cost_and_keeps_grams(setup):
    c, p, m = setup
    r = calc(c, material_mode="direct", material_cost=3.5, waste_pct=50, materials=[{"material_id": m, "amount": 80}])
    assert r["breakdown"]["material"] == pytest.approx(3.5)
    assert r["breakdown"]["merma"] == 0                                    # el laminador ya cuenta purgas
    assert r["materials"][0]["amount"] == 80 and r["materials"][0]["material_id"] == m


def test_waste_and_failure(setup):
    c, p, m = setup
    r = calc(c, materials=[{"material_id": m, "amount": 100}], waste_pct=10, fail_pct=5)
    assert r["breakdown"]["merma"] == pytest.approx(0.2)
    assert r["breakdown"]["riesgo_fallo"] == pytest.approx(2.2 * 0.05)
