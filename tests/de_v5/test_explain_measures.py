"""explain() on the Delaware TRM v5 measures."""

import pytest

from trm_engine import calculate, explain

ASHP = "de-res-hvac-air-source-heat-pump"
SHOWER = "de-res-water-heating-low-flow-shower-head"
ASHP_INPUTS = dict(
    location="wilmington_de",
    cooling_capacity_existing=36_000,
    cooling_capacity_efficient=36_000,
    heating_capacity_existing=36_000,
    heating_capacity_efficient=36_000,
    seer_efficient=16,
    hspf_efficient=9,
    eer_efficient=13,
)


def by_output(explanations):
    return {e.output_id: e for e in explanations}


def test_ashp_energy_outputs_share_the_documented_calculation():
    e = by_output(explain(calculate(ASHP, "time_of_sale", ASHP_INPUTS)))
    cooling = e["kwh_cooling_savings"]
    assert cooling.calculation_outputs == ["kwh_cooling_savings", "kwh_heating_savings", "kwh_savings"]
    assert cooling.documented_equation.startswith("ΔkWh = EFLHcool ×")
    hours = {v.id: v for v in cooling.variables}["cooling_full_load_hours"]
    assert (hours.symbol, hours.value, hours.origin.value, hours.lookup) == (
        "EFLHcool", 719, "lookup", "cooling_full_load_hours_by_location"
    )
    assert hours.citation.page == 74


@pytest.mark.trm_issue("VR-001")
def test_ashp_peak_kw_shows_printed_equation_and_interpretation():
    kw = by_output(explain(calculate(ASHP, "time_of_sale", ASHP_INPUTS)))["kw_ssp_savings"]
    assert kw.documented_equation == "ΔkW = ((BTUHCexist × 1/EERbase) − (BTUHCee × 1/EERee)) / 1000 × CF"
    assert kw.equation_as_printed == "ΔkW = ((BTUHCexist × 1/EERbase) − (BTUHCee × 1/EERee)) / (1000 × CF)"
    assert "multiplies by CF" in kw.interpretation
    assert {"VR-001", "VR-006"} <= set(kw.all_issues)


def test_shower_electric_lists_derived_values_and_their_inputs():
    result = calculate(SHOWER, "direct_install", {"water_heater_fuel": "electric", "gpm_low": 2.0})
    kwh = by_output(explain(result))["kwh_savings"]
    variables = {v.id: v for v in kwh.variables}
    gallons = variables["water_saved_gallons"]
    assert gallons.depth == 0 and gallons.origin.value == "derived"
    assert gallons.derived_from == [
        "gpm_base", "gpm_low", "shower_minutes", "people_per_household",
        "showers_per_person_per_day", "days_per_year", "showerheads_per_home",
    ]
    assert gallons.documented_formula.startswith("(GPMbase − GPMlow) × TimeShower")
    assert variables["gpm_base"].depth == 1 and variables["gpm_base"].origin.value == "trm_default"
    assert variables["gpm_low"].origin.value == "user_input"
    assert variables["shower_temperature"].citation.page == 175
    assert len(kwh.variables) == len(variables)  # each value listed once
    assert {"VR-015", "VR-018", "VR-022"} <= set(kwh.all_issues)


def test_shower_fossil_fuel_explains_only_applicable_outputs():
    result = calculate(SHOWER, "time_of_sale", {"water_heater_fuel": "fossil_fuel", "gpm_low": 2.0})
    assert [e.output_id for e in explain(result)] == ["mmbtu_savings", "water_savings_ccf", "kwh_water_savings"]


@pytest.mark.parametrize(
    ("measure_id", "application", "inputs"),
    [
        (ASHP, "time_of_sale", ASHP_INPUTS),
        (SHOWER, "direct_install", {"water_heater_fuel": "electric", "gpm_base": 1.8, "gpm_low": 2.0}),
        (SHOWER, "direct_install", {"water_heater_fuel": "fossil_fuel", "gpm_low": 1.5, "people_per_household": 4}),
    ],
)
def test_explanations_match_results_exactly(measure_id, application, inputs):
    result = calculate(measure_id, application, inputs)
    for e in explain(result):
        assert e.value == result.outputs[e.output_id].value
        assert e.unit == result.outputs[e.output_id].unit
        for v in e.variables:
            assert v.value == result.variables[v.id].value
            assert v.origin == result.variables[v.id].origin
