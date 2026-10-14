"""UI view models: no Streamlit required."""

import pytest

from trm_engine import calculate, default_registry, input_variables
from trm_ui.presentation import (
    VALIDATION_REGISTER_URL,
    application_options,
    collect_inputs,
    form_fields,
    format_citation,
    format_value,
    interpretation_notes,
    issue_links,
    measure_header,
    not_applicable_rows,
    output_rows,
    provenance_rows,
    related_issue_ids,
    warning_items,
)

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


def measure(measure_id):
    return default_registry().get(measure_id)


@pytest.mark.parametrize(
    ("value", "text"),
    [(0.0, "0"), (192.85, "192.8"), (0.009851992966, "0.009852"), (1477.7757, "1,478"), (36_000, "36,000"),
     (-72.7825, "-72.78"), ("wilmington_de", "wilmington_de")],
)
def test_format_value(value, text):
    assert format_value(value) == text


def test_format_citation():
    m = measure(SHOWER)
    assert format_citation(m.variable("gpm_base").citation) == "p. 174; footnote 460; EPAct 1992 maximum flow rate"
    assert format_citation(None) == ""


def test_issue_links_point_to_register_anchors():
    assert issue_links(["VR-020", "VR-008", "VR-020"]) == [
        ("VR-008", f"{VALIDATION_REGISTER_URL}#vr-008"),
        ("VR-020", f"{VALIDATION_REGISTER_URL}#vr-020"),
    ]


def test_measure_header_shows_draft_and_review_status():
    m = measure(ASHP)
    header = measure_header(m, m.application("time_of_sale"))
    assert header.trm == "DE TRM 5.0"
    assert header.is_draft and header.source_status == "draft"
    assert header.human_reviewed is False
    assert header.measure_code == "RS_HV_TOS_ASHP_0518"
    assert header.pages == "pp. 71–81"


def test_application_options_mark_unimplemented():
    assert application_options(measure(ASHP)) == [
        ("time_of_sale", "Time of Sale", True),
        ("early_replacement", "Early Replacement", False),
    ]


def test_form_fields_come_from_engine_metadata():
    fields = {f.id: f for f in form_fields(input_variables(SHOWER, "direct_install"))}
    assert list(fields) == ["water_heater_fuel", "gpm_base", "gpm_low", "people_per_household"]

    fuel = fields["water_heater_fuel"]
    assert (fuel.kind, fuel.required) == ("choice", True)
    assert fuel.options == (("electric", "Electric"), ("fossil_fuel", "Fossil fuel"))

    gpm_base = fields["gpm_base"]
    assert gpm_base.label == "Baseline flow rate (GPMbase) [gal/min]"
    assert (gpm_base.kind, gpm_base.required, gpm_base.placeholder) == ("number", False, "TRM default: 2.5 gal/min")
    assert "Source: p. 174; footnote 460" in gpm_base.help
    assert "VR-020" in gpm_base.help

    assert fields["gpm_low"].placeholder is None


def test_collect_inputs_omits_empty_fields_so_engine_applies_defaults():
    raw = {"water_heater_fuel": "electric", "gpm_base": None, "gpm_low": 2.0, "people_per_household": None}
    inputs = collect_inputs(raw)
    assert inputs == {"water_heater_fuel": "electric", "gpm_low": 2.0}
    result = calculate(SHOWER, "direct_install", inputs)
    assert result.variables["gpm_base"].origin.value == "trm_default"


def test_output_rows_and_interpretations():
    result = calculate(ASHP, "time_of_sale", ASHP_INPUTS)
    rows = {r["Output"]: r for r in output_rows(result)}
    assert rows["Annual electric savings"]["Value"] == "192.8"
    assert rows["Annual electric savings"]["Unit"] == "kWh/year"
    assert rows["Summer system peak demand savings"]["Interpretation"] == "Yes"
    assert rows["Annual electric savings"]["Interpretation"] == ""
    [note] = interpretation_notes(result)
    assert note["outputs"] == "Summer system peak demand savings, PJM summer peak demand savings"
    assert "VR-001" in note["issues"]


def test_not_applicable_rows_use_output_names():
    m = measure(SHOWER)
    result = calculate(SHOWER, "direct_install", {"water_heater_fuel": "fossil_fuel", "gpm_low": 1.5})
    assert not_applicable_rows(result, m) == [
        {"Outputs": "Annual electric savings, Summer peak demand savings",
         "Reason": "applies only when water_heater_fuel = electric"}
    ]


def test_warning_items():
    result = calculate(SHOWER, "direct_install", {"water_heater_fuel": "electric", "gpm_base": 1.8, "gpm_low": 2.0})
    assert warning_items(result) == [
        {
            "code": "no_positive_water_savings",
            "message": result.warnings[0].message,
            "issues": "VR-020, VR-026",
            "checked": "gpm_base = 1.8, gpm_low = 2",
        }
    ]


def test_provenance_rows_keep_full_precision_and_origin():
    result = calculate(ASHP, "time_of_sale", ASHP_INPUTS)
    rows = {r["Name"]: r for r in provenance_rows(result)}
    hours = rows["Cooling full-load hours"]
    assert (hours["Value"], hours["Origin"]) == ("719.0", "TRM table lookup")
    assert hours["Source"].startswith("cooling_full_load_hours_by_location (p. 74")
    assert rows["Baseline SEER"]["Origin"] == "Deemed (TRM)"
    assert rows["Efficient SEER"]["Origin"] == "User input"


def test_related_issue_ids():
    m = measure(SHOWER)
    before = related_issue_ids(m, "direct_install")
    assert {"VR-017", "VR-025", "VR-020", "VR-026"} <= set(before)
    result = calculate(SHOWER, "direct_install", {"water_heater_fuel": "electric", "gpm_low": 2.0})
    after = related_issue_ids(m, "direct_install", result)
    assert set(before) <= set(after)
    assert after == sorted(after)
    assert "VR-018" in after  # from the shower temperature variable used in the result
