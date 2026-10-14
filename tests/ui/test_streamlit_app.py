"""Headless tests of the Streamlit app with streamlit.testing (no server).

Skipped when Streamlit is not installed (install the ``ui`` extra).
"""

from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

APP = Path(__file__).resolve().parents[2] / "src" / "trm_ui" / "streamlit_app.py"
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
STALE_NOTICE = "Inputs changed since the last calculation"
PREVIOUS_NOTICE = "They do not correspond to the inputs you just submitted"


def start(measure_id=ASHP, application=None):
    at = AppTest.from_file(str(APP), default_timeout=30).run()
    if measure_id != ASHP:
        at.selectbox(key="measure").set_value(measure_id).run()
    if application:
        at.selectbox(key=f"application:{measure_id}").set_value(application).run()
    assert not at.exception
    return at


def fill(at, measure_id, application, inputs):
    prefix = f"{measure_id}:{application}:"
    for field, value in inputs.items():
        widget = (at.selectbox if isinstance(value, str) else at.number_input)(key=prefix + field)
        widget.set_value(value)
    return at


def submit(at, measure_id, application, inputs):
    fill(at, measure_id, application, inputs)
    at.button(key="calculate").click().run()
    assert not at.exception
    return at


def metrics(at):
    return {m.label: m.value for m in at.metric}


def text(elements):
    return "\n".join(e.value for e in elements)


# --- Layout --------------------------------------------------------------------


def test_layout_has_no_sidebar_and_one_compact_notice():
    at = start()
    assert len(at.sidebar.children) == 0
    assert at.title[0].value == "Delaware TRM Calculator"
    assert at.selectbox(key="measure").options == ["Air Source Heat Pump", "Low Flow Shower Head"]
    assert at.selectbox(key=f"application:{ASHP}").options == ["Time of Sale"]
    assert "Not implemented yet: Early Replacement" in text(at.caption)
    assert [w.value for w in at.warning] == [
        "Based on the **draft** DE TRM 5.0. Calculations have not been independently validated."
    ]
    assert "DE TRM 5.0" in text(at.caption)
    assert not at.metric  # nothing calculated yet
    assert "Report a bug" in text(at.caption)


def test_fields_are_grouped_from_metadata():
    at = start(SHOWER)
    headings = [m.value for m in at.markdown if m.value.startswith("**")]
    assert headings == [
        "**Selections**",
        "**Required values**",
        "**Optional — leave blank to use the TRM default**",
    ]


def test_validation_issues_are_in_a_collapsed_expander():
    at = start()
    [issues] = [e for e in at.expander if e.label.startswith("Related validation issues")]
    assert issues.proto.expanded is False
    assert "validation_register.md#vr-025" in text(issues.markdown)


# --- Results -------------------------------------------------------------------


def test_ashp_metrics_interpretation_warning_and_collapsed_details():
    at = submit(start(), ASHP, "time_of_sale", ASHP_INPUTS)
    values = metrics(at)
    assert values["Annual electric savings"] == "192.8 kWh/year"
    assert values["Summer system peak demand savings †"] == "0.1087 kW"
    assert len(values) == 5
    assert "VR-001" in text(at.caption)  # † note
    assert "efficient_equipment_eligibility_not_verified" in text(at.warning)
    details = {e.label: e for e in at.expander}
    assert details["Output details"].proto.expanded is False
    provenance = details["Where every value came from"]
    assert provenance.proto.expanded is False
    assert "TRM table lookup" in set(provenance.dataframe[0].value["Origin"])


@pytest.mark.parametrize("application", ["direct_install", "time_of_sale"])
def test_shower_electric_uses_trm_defaults(application):
    at = submit(start(SHOWER, application), SHOWER, application, {"water_heater_fuel": "electric", "gpm_low": 2.0})
    values = metrics(at)
    assert values["Annual electric savings"] == "182 kWh/year"
    assert "Annual fossil fuel savings" not in values
    provenance = {e.label: e for e in at.expander}["Where every value came from"].dataframe[0].value
    assert dict(zip(provenance["Name"], provenance["Origin"]))["Baseline flow rate"] == "TRM default"


def test_shower_fossil_fuel_shows_only_applicable_outputs():
    at = submit(start(SHOWER), SHOWER, "direct_install", {"water_heater_fuel": "fossil_fuel", "gpm_low": 2.0})
    assert list(metrics(at)) == [
        "Annual fossil fuel savings",
        "Annual water savings",
        "Electric savings from water reduction",
    ]
    assert "Not applicable: Annual electric savings, Summer peak demand savings" in text(at.caption)


def test_shower_flow_warning():
    at = submit(
        start(SHOWER), SHOWER, "direct_install", {"water_heater_fuel": "electric", "gpm_base": 1.8, "gpm_low": 2.0}
    )
    assert metrics(at)["Annual electric savings"] == "-72.78 kWh/year"
    assert "no_positive_water_savings" in text(at.warning)


# --- Persistence and freshness ---------------------------------------------------


def test_result_survives_reruns():
    at = submit(start(), ASHP, "time_of_sale", ASHP_INPUTS)
    at.run()
    assert metrics(at)["Annual electric savings"] == "192.8 kWh/year"


def test_changed_inputs_hide_the_result_until_recalculated():
    at = submit(start(), ASHP, "time_of_sale", ASHP_INPUTS)
    fill(at, ASHP, "time_of_sale", {"seer_efficient": 18}).run()
    assert not at.metric
    assert STALE_NOTICE in text(at.info)
    at.button(key="calculate").click().run()
    assert metrics(at)["Annual electric savings"] != "192.8 kWh/year"
    assert STALE_NOTICE not in text(at.info)


def test_switching_measure_never_shows_the_other_measures_result():
    at = submit(start(), ASHP, "time_of_sale", ASHP_INPUTS)
    at.selectbox(key="measure").set_value(SHOWER).run()
    assert not at.metric
    assert STALE_NOTICE not in text(at.info)


def test_failed_calculation_keeps_previous_result_clearly_labelled():
    at = submit(start(SHOWER), SHOWER, "direct_install", {"water_heater_fuel": "electric", "gpm_low": 2.0})
    submit(at, SHOWER, "direct_install", {"gpm_low": 2.5})
    errors = text(at.error)
    assert "Could not calculate" in errors
    assert "Low flow rate (GPMlow) [gal/min]: Input should be less than or equal to 2" in errors
    assert PREVIOUS_NOTICE in text(at.info)
    assert at.subheader[0].value == "Previous result"
    assert metrics(at)["Annual electric savings"] == "182 kWh/year"

    # Editing the inputs again clears the error and hides the previous numbers.
    fill(at, SHOWER, "direct_install", {"gpm_low": 1.5}).run()
    assert not at.error and not at.metric
    assert STALE_NOTICE in text(at.info)


def test_failed_first_calculation_shows_friendly_errors_only():
    at = submit(start(SHOWER), SHOWER, "direct_install", {"gpm_low": 2.5})
    errors = text(at.error)
    assert "Water heater fuel: This field is required." in errors
    assert "Traceback" not in errors and "ValidationError" not in errors
    assert not at.metric
    assert PREVIOUS_NOTICE not in text(at.info)


def test_unexpected_error_is_logged_not_shown(monkeypatch, caplog):
    import trm_engine

    def broken(*args, **kwargs):
        raise RuntimeError("internal detail: secret path /srv/x")

    monkeypatch.setattr(trm_engine, "calculate", broken)
    at = submit(start(SHOWER), SHOWER, "direct_install", {"water_heater_fuel": "electric", "gpm_low": 2.0})
    errors = text(at.error)
    assert "Something went wrong while calculating" in errors
    assert "internal detail" not in errors and "RuntimeError" not in errors
    assert not at.metric
    assert "internal detail" in caplog.text  # logged for the operator



# --- Show calculation ---------------------------------------------------------------


def calculation_expanders(at):
    return {e.label.removeprefix("Show calculation: "): e for e in at.expander if e.label.startswith("Show calculation: ")}


def test_one_collapsed_show_calculation_per_output_and_cards_unchanged():
    at = submit(start(), ASHP, "time_of_sale", ASHP_INPUTS)
    expanders = calculation_expanders(at)
    assert list(expanders) == [label.removesuffix(" †") for label in metrics(at)]
    assert all(e.proto.expanded is False for e in expanders.values())
    assert metrics(at)["Annual electric savings"] == "192.8 kWh/year"


def test_show_calculation_contents_are_documentation_not_substitution():
    at = submit(start(), ASHP, "time_of_sale", ASHP_INPUTS)
    kw = calculation_expanders(at)["Summer system peak demand savings"]
    assert kw.markdown[0].value == "**Result:** 0.1087429644 kW"
    assert [c.value for c in kw.code] == [
        "ΔkW = ((BTUHCexist × 1/EERbase) − (BTUHCee × 1/EERee)) / 1000 × CF",
        "ΔkW = ((BTUHCexist × 1/EERbase) − (BTUHCee × 1/EERee)) / (1000 × CF)",
    ]
    assert "not executed or independently verified" in text(kw.caption)
    assert "multiplies by CF" in text(kw.info)
    values = kw.dataframe[0].value
    assert dict(zip(values["Symbol"], values["Value"]))["EERbase"] == "12.3"
    assert "VR-001" in text(kw.markdown)
    # No equation with values substituted in is displayed.
    assert not any("36000" in c.value or "12.3" in c.value for c in kw.code)


def test_show_calculation_lists_derived_values_for_shower():
    at = submit(start(SHOWER), SHOWER, "direct_install", {"water_heater_fuel": "electric", "gpm_low": 2.0})
    kwh = calculation_expanders(at)["Annual electric savings"]
    assert "Hours = TimeShower × # people × ShowersPerson / 60 × days/year" in text(kwh.code)
    names = list(kwh.dataframe[0].value["Name"])
    assert names[0] == "Annual water saved" and names[1] == "↳ Baseline flow rate"
    assert "also produces: Summer peak demand savings" in text(kwh.caption)


def test_previous_result_also_has_show_calculation():
    at = submit(start(SHOWER), SHOWER, "direct_install", {"water_heater_fuel": "electric", "gpm_low": 2.0})
    submit(at, SHOWER, "direct_install", {"gpm_low": 2.5})
    assert at.subheader[0].value == "Previous result"
    assert "Annual electric savings" in calculation_expanders(at)
