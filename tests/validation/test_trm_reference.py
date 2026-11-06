"""Checks on the engine-free reference calculator itself.

These compare trm_reference against the values worked out in
docs/validation_plan.md (by matrix ID), not against the engine, so that the
reference can be trusted before engine tests rely on it.
"""

import ast
import subprocess
import sys
from fractions import Fraction as F
from pathlib import Path

import pytest

import trm_reference as ref

REFERENCE_SRC = Path(ref.__file__)


def test_reference_source_does_not_import_engine():
    roots = set()
    for node in ast.walk(ast.parse(REFERENCE_SRC.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            roots.add((node.module or "").split(".")[0])
    assert roots == {"fractions"}


def test_importing_reference_loads_no_engine():
    script = (
        f"import sys; sys.path.insert(0, {str(REFERENCE_SRC.parent)!r}); import trm_reference;"
        "print(sorted(m for m in sys.modules if m.split('.')[0] == 'trm_engine'))"
    )
    out = subprocess.run([sys.executable, "-c", script], check=True, capture_output=True, text=True)
    assert out.stdout.strip() == "[]"


def floats(outputs):
    return {k: float(v) for k, v in outputs.items()}


# --- ASHP (validation plan §3) ----------------------------------------------

A_I1 = dict(
    location="wilmington_de",
    cooling_capacity_existing=36_000,
    cooling_capacity_efficient=36_000,
    heating_capacity_existing=36_000,
    heating_capacity_efficient=36_000,
    seer_efficient=16,
    hspf_efficient=9,
    eer_efficient=13,
)


def test_a_i1():
    out = ref.ashp_time_of_sale(**A_I1)
    assert out["kwh_cooling_savings"] == F("107.85")
    assert out["kwh_heating_savings"] == 85
    assert out["kwh_savings"] == F("192.85")
    assert float(out["kw_ssp_savings"]) == pytest.approx(0.1087429644, rel=1e-9)
    assert float(out["kw_pjm_savings"]) == pytest.approx(0.1040150094, rel=1e-9)


def test_a_i3_baltimore():
    out = ref.ashp_time_of_sale(
        location="baltimore_md",
        cooling_capacity_existing=42_000,
        cooling_capacity_efficient=36_000,
        heating_capacity_existing=40_000,
        heating_capacity_efficient=35_000,
        seer_efficient=17,
        hspf_efficient=9.5,
        eer_efficient=13,
    )
    assert floats(out) == pytest.approx(
        {
            "kwh_cooling_savings": 507.6706,
            "kwh_heating_savings": 745.8373,
            "kwh_savings": 1253.5079,
            "kw_ssp_savings": 0.4453283302,
            "kw_pjm_savings": 0.4259662289,
        },
        rel=1e-7,
    )


@pytest.mark.parametrize(
    "location, total",
    [("wilmington_de", F("192.85")), ("baltimore_md", F("190.3273")), ("washington_dc", F("214.9773"))],
)
def test_a_l1_locations(location, total):
    out = ref.ashp_time_of_sale(**A_I1 | {"location": location})
    assert float(out["kwh_savings"]) == pytest.approx(float(total), rel=1e-6)


def test_a_z1_baseline_equipment_gives_zero():
    out = ref.ashp_time_of_sale(**A_I1 | {"seer_efficient": 15, "hspf_efficient": "8.8", "eer_efficient": "12.3"})
    assert all(v == 0 for v in out.values())


def test_a_m3_linear_in_capacity_and_a_m4_cf_ratio():
    base = ref.ashp_time_of_sale(**A_I1)
    doubled = ref.ashp_time_of_sale(
        **A_I1 | {k: 72_000 for k in A_I1 if k.endswith(("_existing", "_efficient")) and "capacity" in k}
    )
    assert doubled == {k: 2 * v for k, v in base.items()}
    assert base["kw_pjm_savings"] / base["kw_ssp_savings"] == F(22, 23)


@pytest.mark.trm_issue("VR-002")
def test_a_p1_published_tos_kwh():
    # p. 77 example uses SEERbase 14 / HSPFbase 7.7: 509 kWh.
    kwh = ref.ashp_cooling_kwh(744, 36_000, 14, 36_000, 15) + ref.ashp_heating_kwh(866, 36_000, "7.7", 36_000, "8.5")
    assert float(kwh) == pytest.approx(509, abs=0.5)


@pytest.mark.trm_issue("VR-010")
@pytest.mark.parametrize("seer_base, hspf_base, published", [(11, "3.41", 7942), (14, "3.41", 7420)])
def test_a_p5_a_p6_published_er_kwh(seer_base, hspf_base, published):
    kwh = ref.ashp_cooling_kwh(744, 36_000, seer_base, 24_000, 15) + ref.ashp_heating_kwh(
        866, 36_000, hspf_base, 24_000, "8.5"
    )
    assert float(kwh) == pytest.approx(published, abs=0.5)


@pytest.mark.trm_issue("VR-011")
def test_a_p7_wassmer_eer():
    assert ref.wassmer_eer(15) == ref.ASHP_EER_BASE
    assert float(ref.wassmer_eer(14)) == pytest.approx(11.8, abs=0.05)


# --- Low Flow Shower Head (validation plan §4) ------------------------------


@pytest.mark.parametrize(
    "inputs, expected",
    [
        pytest.param(
            {"water_heater_fuel": "electric", "gpm_low": 2.0},
            {"kwh_savings": 181.9564581, "kw_savings": 0.009851992966,
             "water_savings_ccf": 2.222205882, "kwh_water_savings": 4.599966176},
            id="S-I1e",
        ),
        pytest.param(
            {"water_heater_fuel": "fossil_fuel", "gpm_low": 2.0},
            {"mmbtu_savings": 0.760523407875, "water_savings_ccf": 2.222205882, "kwh_water_savings": 4.599966176},
            id="S-I1g",
        ),
        pytest.param(
            {"water_heater_fuel": "electric", "gpm_low": 1.5},
            {"kwh_savings": 363.9129162, "kw_savings": 0.01970398593,
             "water_savings_ccf": 4.444411765, "kwh_water_savings": 9.199932353},
            id="S-I2e",
        ),
        pytest.param(
            {"water_heater_fuel": "electric", "gpm_low": 1.5, "gpm_base": 2.8, "people_per_household": 4},
            {"kwh_savings": 747.963306, "kw_savings": 0.02561518171,
             "water_savings_ccf": 9.134759358, "kwh_water_savings": 18.90895187},
            id="S-I3e",
        ),
        pytest.param(
            {"water_heater_fuel": "fossil_fuel", "gpm_low": 1.5, "gpm_base": 2.8, "people_per_household": 4},
            {"mmbtu_savings": 3.12626223, "water_savings_ccf": 9.134759358, "kwh_water_savings": 18.90895187},
            id="S-I3g",
        ),
    ],
)
def test_shower_reference_cases(inputs, expected):
    assert floats(ref.low_flow_shower_head(**inputs)) == pytest.approx(expected, rel=1e-8)


def test_shower_hours_s_p3():
    assert float(ref.shower_hours(ref.SHOWER_PEOPLE_DEFAULT)) == pytest.approx(72.0291, rel=1e-9)


@pytest.mark.trm_issue("VR-020", "VR-026")
def test_s_z1_equal_flows_give_zero():
    for fuel in ("electric", "fossil_fuel"):
        assert all(v == 0 for v in ref.low_flow_shower_head(water_heater_fuel=fuel, gpm_low=2.0, gpm_base=2.0).values())


def test_s_m2_linear_in_flow_difference():
    for fuel in ("electric", "fossil_fuel"):
        half = ref.low_flow_shower_head(water_heater_fuel=fuel, gpm_low="2.0")
        full = ref.low_flow_shower_head(water_heater_fuel=fuel, gpm_low="1.5")
        assert full == {k: 2 * v for k, v in half.items()}


@pytest.mark.trm_issue("VR-022")
def test_s_m1_kw_independent_of_household_size():
    default = ref.low_flow_shower_head(water_heater_fuel="electric", gpm_low="2.0")
    four = ref.low_flow_shower_head(water_heater_fuel="electric", gpm_low="2.0", people_per_household=4)
    assert four["kwh_savings"] / default["kwh_savings"] == F(4) / F("2.53")
    assert four["kw_savings"] == default["kw_savings"]


def test_unknown_fuel_is_rejected():
    with pytest.raises(ValueError):
        ref.low_flow_shower_head(water_heater_fuel="solar", gpm_low=2.0)
