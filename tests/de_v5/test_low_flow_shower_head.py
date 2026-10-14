"""Delaware TRM v5 — Low Flow Shower Head (pp. 174–178).

Expected values were calculated independently of the implementation (exact
rational arithmetic, shown in each test) from the TRM variable definitions.
The published illustrative examples are inconsistent with those definitions;
see VR-015 and VR-016 in docs/validation_register.md.
"""

import pytest

from trm_engine import InputValidationError, calculate
from trm_engine.measures.de_v5.low_flow_shower_head import (
    electric_savings,
    fossil_fuel_savings,
    shower_hours_per_year,
    water_saved_gallons,
    water_savings,
)
from trm_engine.service import ValueOrigin

MEASURE = "de-res-water-heating-low-flow-shower-head"


def values(result):
    return {k: v.value for k, v in result.outputs.items()}


# --- Independently calculated cases using TRM defaults ----------------------
# Defaults: GPMbase 2.5, # people 2.53, TimeShower 7.8, ShowersPerson 0.6,
# days 365, ShowerHeads/home 1.3, TEMPsh 105, TEMPin 60.9, 8.3 lb/gal.
# gallons = (2.5 - 2.0) x 7.8 x 2.53 x 0.6 x 365 / 1.3   = 1662.21
# hours   = 7.8 x 2.53 x 0.6 / 60 x 365                  = 72.0291

DEFAULT_WATER = {"water_savings_ccf": 2.222205882352941, "kwh_water_savings": 4.599966176470589}


@pytest.mark.trm_issue("VR-015", "VR-019")
@pytest.mark.parametrize("application", ["direct_install", "time_of_sale"])
def test_electric_defaults(application):
    # kWh = 1662.21 x 8.3 x (105 - 60.9) / 0.98 / 3412       = 181.9564...
    # kW  = kWh / 72.0291 x 0.0039                           = 0.0098519...
    result = calculate(MEASURE, application, {"water_heater_fuel": "electric", "gpm_low": 2.0})
    assert values(result) == pytest.approx(
        {"kwh_savings": 181.9564580890973, "kw_savings": 0.009851992966002344} | DEFAULT_WATER,
        rel=1e-12,
    )


@pytest.mark.trm_issue("VR-016", "VR-019")
def test_fossil_fuel_defaults():
    # MMBtu = 1662.21 x 8.3 x (105 - 60.9) / 0.80 / 10^6     = 0.760523...
    result = calculate(MEASURE, "direct_install", {"water_heater_fuel": "fossil_fuel", "gpm_low": 2.0})
    assert values(result) == pytest.approx(
        {"mmbtu_savings": 0.760523407875} | DEFAULT_WATER, rel=1e-12
    )


def test_measured_flow_and_known_household_size():
    # Measured GPMbase 2.8, GPMlow 1.5, 4 people.
    # gallons = 1.3 x 7.8 x 4 x 0.6 x 365 / 1.3              = 6832.8
    # kWh     = 6832.8 x 8.3 x 44.1 / 0.98 / 3412            = 747.9633...
    # hours   = 7.8 x 4 x 0.6 / 60 x 365                     = 113.88
    # kW      = 747.9633 / 113.88 x 0.0039                   = 0.0256151...
    # CCF     = 6832.8 / 748 = 9.134759...; kWh_water = 2.07 x CCF = 18.908951...
    result = calculate(
        MEASURE,
        "direct_install",
        {"water_heater_fuel": "electric", "gpm_base": 2.8, "gpm_low": 1.5, "people_per_household": 4},
    )
    assert values(result) == pytest.approx(
        {
            "kwh_savings": 747.963305978898,
            "kw_savings": 0.025615181711606098,
            "water_savings_ccf": 9.13475935828877,
            "kwh_water_savings": 18.908951871657752,
        },
        rel=1e-12,
    )
    assert result.variables["shower_hours_per_year"].value == pytest.approx(113.88)
    assert result.variables["gpm_base"].origin is ValueOrigin.USER_INPUT


# --- Fuel type determines applicable outputs ---------------------------------


@pytest.mark.parametrize(
    ("fuel", "present", "absent", "skipped"),
    [
        ("electric", {"kwh_savings", "kw_savings"}, {"mmbtu_savings"}, "fossil_fuel_savings"),
        ("fossil_fuel", {"mmbtu_savings"}, {"kwh_savings", "kw_savings"}, "electric_savings"),
    ],
)
def test_fuel_type_selects_outputs(fuel, present, absent, skipped):
    result = calculate(MEASURE, "direct_install", {"water_heater_fuel": fuel, "gpm_low": 1.5})
    assert present | {"water_savings_ccf", "kwh_water_savings"} == set(result.outputs)
    assert not absent & set(result.outputs)  # omitted, never reported as zero
    assert [na.calculation for na in result.not_applicable] == [skipped]
    assert set(result.not_applicable[0].outputs) == absent


# --- Published TRM illustrative examples --------------------------------------
# Each example states its own inputs. They are reproduced here by calling the
# equation functions with exactly those inputs; none of them can be reproduced
# with the TRM's defined defaults.

# p. 175: ((2.5 - 2.0) x 7.8 x 2.53 x 365 / 1.3) — ShowersPerson is absent,
# which is arithmetically the same as ShowersPerson = 1.
EXAMPLE_GALLONS = water_saved_gallons(
    gpm_base=2.5,
    gpm_low=2.0,
    shower_minutes=7.8,
    people_per_household=2.53,
    showers_per_person_per_day=1,
    days_per_year=365,
    showerheads_per_home=1.3,
)


@pytest.mark.trm_issue("VR-015")
def test_published_kwh_example_uses_inputs_inconsistent_with_defaults():
    # p. 175 publishes 276 kWh, using TEMPsh 101 and no ShowersPerson factor.
    # With the defined values (0.6 showers/person/day, 105 °F) the result is 182 kWh.
    example = electric_savings(
        water_saved_gallons=EXAMPLE_GALLONS,
        pounds_per_gallon=8.3,
        shower_temperature=101,
        inlet_temperature=60.9,
        electric_recovery_efficiency=0.98,
        btu_per_kwh=3412,
        shower_hours_per_year=72,
        coincidence_factor=0.0039,
    )
    assert round(example["kwh_savings"]) == 276
    defaults = calculate(MEASURE, "time_of_sale", {"water_heater_fuel": "electric", "gpm_low": 2.0})
    assert round(defaults.outputs["kwh_savings"].value) == 182


@pytest.mark.trm_issue("VR-015")
def test_published_kw_example():
    # p. 176: 276 / 72 x 0.0039 = 0.015 kW. The 276 kWh omits ShowersPerson but
    # the 72 hours includes it, so no single consistent input set reproduces it.
    assert round(276 / shower_hours_per_year(7.8, 2.53, 0.6, 365) * 0.0039, 3) == 0.015


@pytest.mark.trm_issue("VR-015", "VR-016")
def test_published_mmbtu_example_requires_unstated_efficiency():
    # p. 177 publishes 1.23 MMBtu and prints "/ .80", but 1.23 is only reached
    # with a 0.75 recovery efficiency (VR-016). With the printed 0.80 the
    # example's other inputs give 1.15.
    def mmbtu(efficiency):
        return fossil_fuel_savings(
            water_saved_gallons=EXAMPLE_GALLONS,
            pounds_per_gallon=8.3,
            shower_temperature=101,
            inlet_temperature=60.9,
            fossil_recovery_efficiency=efficiency,
            btu_per_mmbtu=1e6,
        )["mmbtu_savings"]

    assert round(mmbtu(0.80), 2) == 1.15
    assert round(mmbtu(0.75), 2) == 1.23


@pytest.mark.trm_issue("VR-015", "VR-024")
def test_published_water_examples():
    # p. 177: 3.7 CCF; p. 178: 2.07 x 3.7 = 7.7 kWh (computed from the rounded 3.7 CCF).
    result = water_savings(EXAMPLE_GALLONS, gallons_per_ccf=748, kwh_per_ccf_water=2.07)
    assert round(result["water_savings_ccf"], 1) == 3.7
    assert round(result["kwh_water_savings"], 1) == 7.7


def test_published_hours():
    # p. 176: 7.8 x 2.53 x 0.6 / 60 x 365 = 72 hours.
    assert round(shower_hours_per_year(7.8, 2.53, 0.6, 365)) == 72


# --- Defaults, provenance, and validation -------------------------------------


def test_defaults_are_reported_with_provenance():
    result = calculate(MEASURE, "direct_install", {"water_heater_fuel": "electric", "gpm_low": 2.0})
    gpm_base = result.variables["gpm_base"]
    assert (gpm_base.value, gpm_base.origin, gpm_base.citation.footnote) == (
        2.5,
        ValueOrigin.TRM_DEFAULT,
        460,
    )
    assert result.variables["people_per_household"].origin is ValueOrigin.TRM_DEFAULT
    assert result.variables["shower_temperature"].origin is ValueOrigin.DEEMED
    assert result.variables["water_saved_gallons"].origin is ValueOrigin.DERIVED
    assert result.measure_code == "RS_WT_DI_SHWRHD_0519"
    assert result.status.human_reviewed is False


@pytest.mark.trm_issue("VR-021")
def test_eligibility_maximum_flow_rate():
    calculate(MEASURE, "direct_install", {"water_heater_fuel": "electric", "gpm_low": 2.0})
    with pytest.raises(InputValidationError, match="gpm_low"):
        calculate(MEASURE, "direct_install", {"water_heater_fuel": "electric", "gpm_low": 2.01})


@pytest.mark.parametrize(
    "inputs",
    [
        {"gpm_low": 2.0},  # fuel is required
        {"water_heater_fuel": "propane", "gpm_low": 2.0},
        {"water_heater_fuel": "electric"},
        {"water_heater_fuel": "electric", "gpm_low": 0},
        {"water_heater_fuel": "electric", "gpm_low": 2.0, "people_per_household": 0},
        {"water_heater_fuel": "electric", "gpm_low": 2.0, "shower_temperature": 101},
        {"water_heater_fuel": "electric", "gpm_low": True},
        {"water_heater_fuel": "electric", "gpm_low": float("nan")},
    ],
)
def test_invalid_inputs_are_rejected(inputs):
    with pytest.raises(InputValidationError):
        calculate(MEASURE, "direct_install", inputs)


# --- Installations with no flow reduction ------------------------------------
# The TRM does not say how to treat these (VR-020, VR-026). Results are returned
# unchanged with a warning.


def test_no_warning_when_flow_is_reduced():
    result = calculate(MEASURE, "direct_install", {"water_heater_fuel": "electric", "gpm_low": 2.0})
    assert result.warnings == []
    measured = calculate(
        MEASURE, "direct_install", {"water_heater_fuel": "electric", "gpm_base": 2.0, "gpm_low": 1.99}
    )
    assert measured.warnings == []


@pytest.mark.trm_issue("VR-020", "VR-026")
def test_equal_flow_rates_warn_and_give_zero_savings():
    result = calculate(
        MEASURE, "direct_install", {"water_heater_fuel": "electric", "gpm_base": 2.0, "gpm_low": 2.0}
    )
    [warning] = result.warnings
    assert warning.code == "no_positive_water_savings"
    assert warning.issues == ["VR-020", "VR-026"]
    assert warning.variables == {"gpm_base": 2.0, "gpm_low": 2.0}
    assert values(result) == {
        "kwh_savings": 0.0,
        "kw_savings": 0.0,
        "water_savings_ccf": 0.0,
        "kwh_water_savings": 0.0,
    }


@pytest.mark.trm_issue("VR-020", "VR-026")
@pytest.mark.parametrize(
    ("fuel", "expected"),
    [
        # gallons = (1.8 - 2.0) x 7.8 x 2.53 x 0.6 x 365 / 1.3 = -664.884
        # i.e. -0.4 x the 2.5 -> 2.0 GPM default case.
        ("electric", {"kwh_savings": -72.78258323563892, "kw_savings": -0.0039407971864009374}),
        ("fossil_fuel", {"mmbtu_savings": -0.30420936315}),
    ],
)
def test_installed_flow_above_baseline_warns_and_keeps_negative_result(fuel, expected):
    result = calculate(
        MEASURE, "time_of_sale", {"water_heater_fuel": fuel, "gpm_base": 1.8, "gpm_low": 2.0}
    )
    assert [w.code for w in result.warnings] == ["no_positive_water_savings"]
    assert result.warnings[0].variables == {"gpm_base": 1.8, "gpm_low": 2.0}
    assert values(result) == pytest.approx(
        expected | {"water_savings_ccf": -0.8888823529411765, "kwh_water_savings": -1.8399864705882354},
        rel=1e-12,
    )
