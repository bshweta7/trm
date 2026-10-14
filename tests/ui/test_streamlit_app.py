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


def start(measure_id=ASHP, application=None):
    at = AppTest.from_file(str(APP), default_timeout=30).run()
    if measure_id != ASHP:
        at.sidebar.selectbox(key="measure").set_value(measure_id).run()
    if application:
        at.sidebar.selectbox(key=f"application:{measure_id}").set_value(application).run()
    assert not at.exception
    return at


def submit(at, measure_id, application, inputs):
    prefix = f"{measure_id}:{application}:"
    for field, value in inputs.items():
        widget = (at.selectbox if isinstance(value, str) else at.number_input)(key=prefix + field)
        widget.set_value(value)
    at.button[0].click().run()
    assert not at.exception
    return at


def outputs(at):
    return dict(zip(at.dataframe[0].value["Output"], at.dataframe[0].value["Value"]))


def text(elements):
    return "\n".join(e.value for e in elements)


def test_initial_page_shows_status_and_only_implemented_applications():
    at = start()
    assert at.title[0].value == "Delaware TRM Calculator"
    assert at.sidebar.selectbox(key="measure").options == ["Air Source Heat Pump", "Low Flow Shower Head"]
    assert at.sidebar.selectbox(key=f"application:{ASHP}").options == ["Time of Sale"]
    assert "Not implemented yet: Early Replacement" in text(at.sidebar.caption)
    warnings = text(at.warning)
    assert "**draft** TRM" in warnings
    assert "Not reviewed by an energy efficiency expert" in warnings
    assert "DE TRM 5.0" in text(at.caption)
    assert not at.dataframe  # nothing calculated yet


def test_ashp_results_with_units_interpretation_warning_and_issue_links():
    at = submit(start(), ASHP, "time_of_sale", ASHP_INPUTS)
    assert outputs(at)["Annual electric savings"] == "192.8"
    assert set(at.dataframe[0].value["Unit"]) == {"kWh/year", "kW"}
    assert "VR-001" in text(at.info)  # peak kW interpretation
    assert "efficient_equipment_eligibility_not_verified" in text(at.warning)
    provenance = at.dataframe[1].value
    assert "TRM table lookup" in set(provenance["Origin"])
    assert "validation_register.md#vr-001" in text(at.markdown)


@pytest.mark.parametrize("application", ["direct_install", "time_of_sale"])
def test_shower_electric_uses_trm_defaults(application):
    at = submit(start(SHOWER, application), SHOWER, application, {"water_heater_fuel": "electric", "gpm_low": 2.0})
    values = outputs(at)
    assert values["Annual electric savings"] == "182"
    assert "Annual fossil fuel savings" not in values
    origins = dict(zip(at.dataframe[1].value["Name"], at.dataframe[1].value["Origin"]))
    assert origins["Baseline flow rate"] == "TRM default"


def test_shower_fossil_fuel_omits_electric_outputs():
    at = submit(start(SHOWER), SHOWER, "direct_install", {"water_heater_fuel": "fossil_fuel", "gpm_low": 2.0})
    values = outputs(at)
    assert values["Annual fossil fuel savings"] == "0.7605"
    assert "Annual electric savings" not in values
    assert "Not applicable: Annual electric savings, Summer peak demand savings" in text(at.caption)


def test_shower_flow_warning():
    at = submit(
        start(SHOWER), SHOWER, "direct_install", {"water_heater_fuel": "electric", "gpm_base": 1.8, "gpm_low": 2.0}
    )
    assert outputs(at)["Annual electric savings"] == "-72.78"
    assert "no_positive_water_savings" in text(at.warning)
    assert "VR-026" in text(at.markdown)


def test_validation_errors_are_shown_per_field_without_a_traceback():
    at = submit(start(SHOWER), SHOWER, "direct_install", {"gpm_low": 2.5})
    message = text(at.error)
    assert "Water heater fuel" in message and "Field required" in message
    assert "Low flow rate" in message and "less than or equal to 2" in message
    assert not at.dataframe
