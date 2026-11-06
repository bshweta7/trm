"""One mixed batch built from validation-matrix cases, checked against the
engine-free reference calculator (docs/validation_plan.md §3–§4).

This is the end-to-end check that batch results match independently derived
values, not just calculate().
"""

from fractions import Fraction as F

import pytest

import trm_reference as ref
from trm_engine import calculate_batch

ASHP = "de-res-hvac-air-source-heat-pump"
SHOWER = "de-res-water-heating-low-flow-shower-head"
A_I1 = dict(
    cooling_capacity_existing=36_000,
    cooling_capacity_efficient=36_000,
    heating_capacity_existing=36_000,
    heating_capacity_efficient=36_000,
    seer_efficient=16,
    hspf_efficient=9,
    eer_efficient=13,
)
A_I3 = dict(
    location="baltimore_md",
    cooling_capacity_existing=42_000,
    cooling_capacity_efficient=36_000,
    heating_capacity_existing=40_000,
    heating_capacity_efficient=35_000,
    seer_efficient=17,
    hspf_efficient="9.5",
    eer_efficient=13,
)

# (matrix ID, measure, application, inputs with exact decimals as strings, reference)
CASES = [
    ("A-I3", ASHP, "time_of_sale", A_I3, lambda i: ref.ashp_time_of_sale(**i)),
    *[
        (f"A-L1-{loc}", ASHP, "time_of_sale", A_I1 | {"location": loc}, lambda i: ref.ashp_time_of_sale(**i))
        for loc in ("wilmington_de", "baltimore_md", "washington_dc")
    ],
    ("S-I1e", SHOWER, "direct_install", {"water_heater_fuel": "electric", "gpm_low": "2.0"}, None),
    ("S-I2g", SHOWER, "time_of_sale", {"water_heater_fuel": "fossil_fuel", "gpm_low": "1.5"}, None),
    ("S-I3g", SHOWER, "direct_install",
     {"water_heater_fuel": "fossil_fuel", "gpm_base": "2.8", "gpm_low": "1.5", "people_per_household": 4}, None),
    ("S-Z2e", SHOWER, "direct_install", {"water_heater_fuel": "electric", "gpm_base": "1.8", "gpm_low": "2.0"}, None),
]


def engine_inputs(inputs):
    choices = {"location", "water_heater_fuel"}
    return {k: v if k in choices else float(v) for k, v in inputs.items()}


def reference(measure, inputs, fn):
    if fn is not None:
        return fn(inputs)
    return ref.low_flow_shower_head(**{k: v if k == "water_heater_fuel" else F(v) for k, v in inputs.items()})


@pytest.mark.trm_issue("VR-001", "VR-003", "VR-015", "VR-016", "VR-026")
def test_mixed_matrix_batch_matches_reference():
    rows = [
        {"row_id": mid, "measure_id": m, "application": a, "inputs": engine_inputs(i)}
        for mid, m, a, i, _ in CASES
    ]
    batch = calculate_batch(rows)
    assert batch.error_count == 0
    for (mid, measure, _, inputs, fn), outcome in zip(CASES, batch.rows, strict=True):
        assert outcome.row_id == mid
        actual = {k: o.value for k, o in outcome.result.outputs.items()}
        expected = {k: float(v) for k, v in reference(measure, inputs, fn).items()}
        assert actual == pytest.approx(expected, rel=1e-12, abs=1e-12), mid
