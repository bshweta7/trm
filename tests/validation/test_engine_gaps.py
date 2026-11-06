"""Engine tests for the coverage gaps in docs/validation_plan.md §6.

Each case is keyed by its validation-matrix ID. Expected values come from the
engine-free reference calculator (trm_reference), never from the engine.
Decimal inputs are written as strings so the reference stays exact; the engine
receives the same values as floats. A passing test shows consistency with the
interpretation recorded in docs/validation_register.md, not that it is correct.
"""

from fractions import Fraction as F

import pytest

import trm_reference as ref
from trm_engine import calculate
from trm_engine.measures.de_v5.air_source_heat_pump import time_of_sale_energy_savings

ASHP = "de-res-hvac-air-source-heat-pump"
SHOWER = "de-res-water-heating-low-flow-shower-head"
REL = 1e-12  # validation plan §1.3: exact reference vs floating point


def engine_inputs(inputs):
    choices = {"location", "water_heater_fuel"}
    return {k: v if k in choices else float(v) for k, v in inputs.items()}


def run(measure, application, inputs):
    result = calculate(measure, application, engine_inputs(inputs))
    return {k: v.value for k, v in result.outputs.items()}, [w.code for w in result.warnings]


def expected(outputs):
    return {k: float(v) for k, v in outputs.items()}


# --- ASHP, Time of Sale -------------------------------------------------------

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
A_M2 = A_I1 | {"seer_efficient": 14}
CAPACITIES = [k for k in A_I1 if "capacity" in k]

ASHP_CASES = [
    pytest.param(A_I3, id="A-I3-baltimore"),
    pytest.param(A_I1, id="A-L1-wilmington"),
    pytest.param(A_I1 | {"location": "baltimore_md"}, id="A-L1-baltimore"),
    pytest.param(A_I1 | {"location": "washington_dc"}, id="A-L1-washington-dc"),
    pytest.param(A_M2, id="A-M2-below-baseline-seer"),
]


@pytest.mark.trm_issue("VR-001", "VR-003", "VR-007")
@pytest.mark.parametrize("inputs", ASHP_CASES)
def test_ashp_reference_cases(inputs):
    outputs, _ = run(ASHP, "time_of_sale", inputs)
    assert outputs == pytest.approx(expected(ref.ashp_time_of_sale(**inputs)), rel=REL)


@pytest.mark.trm_issue("VR-003", "VR-008")
def test_a_m2_below_baseline_values_and_warning():
    # cooling = 719 x (36000/15 - 36000/14) / 1000 = -123.2571...; heating and kW as A-I1.
    outputs, warnings = run(ASHP, "time_of_sale", A_M2)
    reference = ref.ashp_time_of_sale(**A_M2)
    assert reference["kwh_cooling_savings"] == F(-862_800, 7000)
    assert outputs["kwh_cooling_savings"] < 0 < outputs["kwh_heating_savings"]
    assert outputs["kwh_savings"] == pytest.approx(float(reference["kwh_savings"]), rel=REL)
    assert warnings == ["efficient_equipment_eligibility_not_verified"]


@pytest.mark.parametrize("inputs", [p.values[0] for p in ASHP_CASES], ids=[p.id for p in ASHP_CASES])
def test_a_m3_outputs_scale_linearly_with_capacity(inputs):
    base, _ = run(ASHP, "time_of_sale", inputs)
    doubled, _ = run(ASHP, "time_of_sale", inputs | {k: 2 * inputs[k] for k in CAPACITIES})
    assert doubled == pytest.approx({k: 2 * v for k, v in base.items()}, rel=REL)


@pytest.mark.trm_issue("VR-006")
@pytest.mark.parametrize("inputs", [p.values[0] for p in ASHP_CASES], ids=[p.id for p in ASHP_CASES])
def test_a_m4_pjm_to_ssp_ratio_and_a_m5_total(inputs):
    outputs, _ = run(ASHP, "time_of_sale", inputs)
    assert outputs["kw_pjm_savings"] / outputs["kw_ssp_savings"] == pytest.approx(22 / 23, rel=REL)
    assert outputs["kwh_savings"] == pytest.approx(
        outputs["kwh_cooling_savings"] + outputs["kwh_heating_savings"], rel=REL
    )


@pytest.mark.trm_issue("VR-010")
def test_a_p5_early_replacement_remaining_life_equation_form():
    # Early Replacement is not implemented; the remaining-life kWh equation has
    # the Time of Sale form with existing-unit ratings as the baseline (pp. 77–78).
    args = dict(
        cooling_capacity_existing=36_000, cooling_capacity_efficient=24_000,
        heating_capacity_existing=36_000, heating_capacity_efficient=24_000,
        seer_baseline=11, seer_efficient=15, hspf_baseline="3.41", hspf_efficient="8.5",
        cooling_full_load_hours=744, heating_full_load_hours=866,
    )
    reference = ref.ashp_cooling_kwh(744, 36_000, 11, 24_000, 15) + ref.ashp_heating_kwh(
        866, 36_000, "3.41", 24_000, "8.5"
    )
    result = time_of_sale_energy_savings(**{k: float(v) for k, v in args.items()})
    assert result["kwh_savings"] == pytest.approx(float(reference), rel=REL)
    assert result["kwh_savings"] == pytest.approx(7942, abs=0.5)  # published, p. 77


# --- Low Flow Shower Head -------------------------------------------------------

SHOWER_CASES = [
    pytest.param({"gpm_low": "1.5"}, id="S-I2"),
    pytest.param({"gpm_low": "1.5", "gpm_base": "2.8", "people_per_household": 4}, id="S-I3"),
    pytest.param({"gpm_low": "2.0"}, id="S-I1"),
]


@pytest.mark.trm_issue("VR-015", "VR-016", "VR-019", "VR-023")
@pytest.mark.parametrize("application", ["direct_install", "time_of_sale"])
@pytest.mark.parametrize("fuel", ["electric", "fossil_fuel"])
@pytest.mark.parametrize("inputs", SHOWER_CASES)
def test_shower_reference_cases(inputs, fuel, application):
    inputs = inputs | {"water_heater_fuel": fuel}
    outputs, warnings = run(SHOWER, application, inputs)
    assert outputs == pytest.approx(expected(ref.low_flow_shower_head(**inputs)), rel=REL)
    assert warnings == []


@pytest.mark.parametrize("fuel", ["electric", "fossil_fuel"])
def test_s_m2_outputs_scale_with_flow_reduction(fuel):
    half, _ = run(SHOWER, "direct_install", {"water_heater_fuel": fuel, "gpm_low": 2.0})
    full, _ = run(SHOWER, "direct_install", {"water_heater_fuel": fuel, "gpm_low": 1.5})
    assert full == pytest.approx({k: 2 * v for k, v in half.items()}, rel=REL)


@pytest.mark.trm_issue("VR-022")
def test_s_m1_peak_kw_does_not_depend_on_household_size():
    """Records current behaviour without endorsing it: # people cancels in kWh / Hours."""
    default, _ = run(SHOWER, "direct_install", {"water_heater_fuel": "electric", "gpm_low": 2.0})
    four, _ = run(SHOWER, "direct_install", {"water_heater_fuel": "electric", "gpm_low": 2.0, "people_per_household": 4})
    assert four["kwh_savings"] == pytest.approx(default["kwh_savings"] * 4 / 2.53, rel=REL)
    assert four["kw_savings"] == pytest.approx(default["kw_savings"], rel=REL)


@pytest.mark.trm_issue("VR-019", "VR-022")
@pytest.mark.parametrize("inputs", SHOWER_CASES)
def test_s_m3_output_relations(inputs):
    inputs = inputs | {"water_heater_fuel": "electric"}
    outputs, _ = run(SHOWER, "direct_install", inputs)
    hours = float(ref.shower_hours(F(inputs.get("people_per_household", ref.SHOWER_PEOPLE_DEFAULT))))
    assert outputs["kwh_water_savings"] == pytest.approx(2.07 * outputs["water_savings_ccf"], rel=REL)
    assert outputs["kw_savings"] == pytest.approx(outputs["kwh_savings"] / hours * 0.0039, rel=REL)
