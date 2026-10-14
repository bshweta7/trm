"""UI view models: no Streamlit required."""

import pytest

from trm_engine import calculate, default_registry, input_variables
from urllib.parse import parse_qs, urlparse

from trm_engine import InputValidationError, explain
from trm_ui.presentation import (
    REQUIRED_MESSAGE,
    VALIDATION_REGISTER_URL,
    MeasureHeader,
    application_options,
    bug_report_url,
    collect_inputs,
    current_failure,
    derived_formulas,
    explanation_rows,
    form_fields,
    format_citation,
    format_precise,
    format_value,
    group_fields,
    interpretation_notes,
    issue_links,
    measure_header,
    not_applicable_rows,
    output_metrics,
    output_rows,
    provenance_rows,
    related_issue_ids,
    result_status,
    shared_calculation_note,
    status_notice,
    validation_messages,
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


# --- Layout, notices, and result freshness -----------------------------------


def test_group_fields_uses_metadata_and_keeps_definition_order():
    groups = group_fields(form_fields(input_variables(SHOWER, "direct_install")))
    assert [(title, [f.id for f in fields]) for title, fields in groups] == [
        ("Selections", ["water_heater_fuel"]),
        ("Required values", ["gpm_low"]),
        ("Optional — leave blank to use the TRM default", ["gpm_base", "people_per_household"]),
    ]


def test_group_fields_omits_empty_groups():
    groups = group_fields(form_fields(input_variables(ASHP, "time_of_sale")))
    assert [title for title, _ in groups] == ["Selections", "Required values"]
    # Definition order keeps existing/efficient pairs adjacent for a two-column grid.
    assert [f.id for f in groups[1][1]][:4] == [
        "cooling_capacity_existing",
        "cooling_capacity_efficient",
        "heating_capacity_existing",
        "heating_capacity_efficient",
    ]


def make_header(is_draft, human_reviewed):
    return MeasureHeader("t", "DE TRM 5.0", is_draft, "draft" if is_draft else "final", "u", "p", "c", human_reviewed)


def test_status_notice():
    m = measure(ASHP)
    assert status_notice(measure_header(m, m.application("time_of_sale"))) == (
        "Based on the **draft** DE TRM 5.0. Calculations have not been independently validated."
    )
    assert status_notice(make_header(False, False)) == "Calculations have not been independently validated."
    assert status_notice(make_header(False, True)) is None


def test_output_metrics_show_every_output_with_units():
    result = calculate(ASHP, "time_of_sale", ASHP_INPUTS)
    metrics = output_metrics(result)
    assert [m["label"] for m in metrics] == [
        "Annual cooling electric savings",
        "Annual heating electric savings",
        "Annual electric savings",
        "Summer system peak demand savings †",
        "PJM summer peak demand savings †",
    ]
    assert metrics[2]["value"] == "192.8 kWh/year"
    assert metrics[3]["value"] == "0.1087 kW"
    assert "multiplies by CF" in metrics[3]["help"] and "VR-001" in metrics[3]["help"]


def test_output_metrics_include_only_applicable_outputs():
    result = calculate(SHOWER, "direct_install", {"water_heater_fuel": "fossil_fuel", "gpm_low": 2.0})
    assert [m["label"] for m in output_metrics(result)] == [
        "Annual fossil fuel savings",
        "Annual water savings",
        "Electric savings from water reduction",
    ]


def slot(inputs, measure_id=SHOWER, application="direct_install", **extra):
    return {"measure_id": measure_id, "application": application, "inputs": inputs, **extra}


A = {"water_heater_fuel": "electric", "gpm_low": 2.0}
B = {"water_heater_fuel": "electric", "gpm_low": 1.5}


@pytest.mark.parametrize(
    ("stored", "failure", "measure_id", "application", "inputs", "expected"),
    [
        (None, None, SHOWER, "direct_install", A, "none"),
        (slot(A), None, SHOWER, "direct_install", A, "current"),
        (slot(A), None, SHOWER, "direct_install", B, "stale"),
        (slot(A), None, SHOWER, "time_of_sale", A, "none"),  # other application
        (slot(A), None, ASHP, "time_of_sale", A, "none"),  # other measure
        (slot(A), slot(B, messages=["x"]), SHOWER, "direct_install", B, "previous"),  # failed on B
        (slot(A), slot(B, messages=["x"]), SHOWER, "direct_install", {"gpm_low": 1.0}, "stale"),
        (slot(A), slot(B, messages=["x"]), SHOWER, "direct_install", A, "current"),
    ],
)
def test_result_status(stored, failure, measure_id, application, inputs, expected):
    assert result_status(stored, failure, measure_id, application, inputs) == expected


def test_current_failure_only_for_the_failed_inputs():
    failure = slot(B, messages=["Low flow rate: too high"])
    assert current_failure(failure, SHOWER, "direct_install", B) == ["Low flow rate: too high"]
    assert current_failure(failure, SHOWER, "direct_install", A) is None
    assert current_failure(None, SHOWER, "direct_install", B) is None


def test_validation_messages_use_labels_and_friendly_wording():
    fields = form_fields(input_variables(SHOWER, "direct_install"))
    with pytest.raises(InputValidationError) as exc:
        calculate(SHOWER, "direct_install", {"gpm_low": 2.5})
    assert validation_messages(exc.value.details, fields) == [
        f"Water heater fuel: {REQUIRED_MESSAGE}",
        "Low flow rate (GPMlow) [gal/min]: Input should be less than or equal to 2",
    ]


def test_bug_report_url_prefills_context_but_no_inputs():
    m = measure(SHOWER)
    url = urlparse(bug_report_url(m, m.application("direct_install")))
    assert (url.netloc, url.path) == ("github.com", "/bshweta7/trm/issues/new")
    query = parse_qs(url.query)
    assert query["title"] == ["Bug: Low Flow Shower Head — Direct Install"]
    assert "Measure: de-res-water-heating-low-flow-shower-head" in query["body"][0]
    assert "TRM: DE 5.0 (draft)" in query["body"][0]
    assert bug_report_url() == "https://github.com/bshweta7/trm/issues/new"


# --- Calculation explanations ---------------------------------------------------


def shower_kwh_explanation():
    result = calculate(SHOWER, "direct_install", {"water_heater_fuel": "electric", "gpm_low": 2.0})
    return next(e for e in explain(result) if e.output_id == "kwh_savings")


@pytest.mark.parametrize(("value", "text"), [(181.95645808909730, "181.9564581"), (719.0, "719"), ("electric", "electric")])
def test_format_precise(value, text):
    assert format_precise(value) == text


def test_explanation_rows_indent_derived_inputs_and_show_provenance():
    rows = explanation_rows(shower_kwh_explanation())
    names = [r["Name"] for r in rows]
    assert names[:3] == ["Annual water saved", "↳ Baseline flow rate", "↳ Low flow rate"]
    by_name = {r["Name"].removeprefix("↳ "): r for r in rows}
    assert by_name["Baseline flow rate"]["Origin"] == "TRM default"
    assert by_name["Baseline flow rate"]["Source"].startswith("p. 174; footnote 460")
    assert by_name["Shower water temperature"] == {
        "Symbol": "TEMPsh",
        "Name": "Shower water temperature",
        "Value": "105",
        "Unit": "°F",
        "Origin": "Deemed (TRM)",
        "Source": "p. 175; No source footnote given",
        "Issues": "VR-015, VR-018",
    }


def test_derived_formulas_are_documented_text():
    assert derived_formulas(shower_kwh_explanation()) == [
        "Annual water saved = (GPMbase − GPMlow) × TimeShower × # people × ShowersPerson × days/year / ShowerHeads/home",
        "Hours = TimeShower × # people × ShowersPerson / 60 × days/year",
    ]


def test_shared_calculation_note():
    m = measure(ASHP)
    explanations = {e.output_id: e for e in explain(calculate(ASHP, "time_of_sale", ASHP_INPUTS))}
    note = shared_calculation_note(explanations["kwh_savings"], m)
    assert "also produces: Annual cooling electric savings, Annual heating electric savings" in note
    water = next(e for e in explain(calculate(SHOWER, "direct_install", {"water_heater_fuel": "electric", "gpm_low": 2.0}))
                 if e.output_id == "water_savings_ccf")
    assert "Electric savings from water reduction" in shared_calculation_note(water, measure(SHOWER))
