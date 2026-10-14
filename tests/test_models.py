"""Schema validation: malformed or inconsistent reference data must fail loudly."""

import pytest
import yaml
from pydantic import ValidationError

from conftest import DEMO_VERSION_DIR
from trm_engine.models import Manifest, Measure


def variable(data, var_id):
    return next(v for v in data["variables"] if v["id"] == var_id)


def calculation(data, calc_id):
    return next(c for c in data["calculations"] if c["id"] == calc_id)


def test_demo_measure_is_valid(demo_measure_data):
    measure = Measure.model_validate(demo_measure_data)
    assert [c.id for c in measure.calculations_for("time_of_sale")] == ["electric", "gas"]
    assert measure.calculations_for("retrofit") == []


def mutations():
    def unknown_source(d):
        variable(d, "rate")["source"] = "probably_from_table"

    def unknown_field(d):
        variable(d, "rate")["confidence"] = "high"

    def deemed_without_value(d):
        del variable(d, "rate")["value"]

    def optional_input_without_default(d):
        del variable(d, "hours")["default"]

    def default_without_citation(d):
        del variable(d, "hours")["citation"]

    def required_with_default(d):
        variable(d, "quantity")["default"] = 1

    def deemed_with_default(d):
        variable(d, "rate")["default"] = 1

    def choice_without_choices(d):
        del variable(d, "zone")["choices"]

    def derived_without_function(d):
        del variable(d, "unit_hours")["function"]

    def conditional_source_not_supported(d):
        variable(d, "rate")["source"] = "conditional"

    def unknown_variable_in_calculation(d):
        calculation(d, "electric")["variables"].append("nope")

    def unknown_variable_in_derivation(d):
        variable(d, "unit_hours")["variables"].append("nope")

    def unknown_output(d):
        calculation(d, "electric")["outputs"].append("steam_savings")

    def unknown_application(d):
        calculation(d, "electric")["applications"].append("new_construction")

    def bad_applies_when(d):
        calculation(d, "electric")["applies_when"] = {"fuel": "solar"}

    def output_produced_twice(d):
        calculation(d, "gas")["applies_when"] = {}
        calculation(d, "gas")["outputs"] = ["kwh_savings"]

    def interpretation_without_issue(d):
        calculation(d, "gas")["issues"] = []

    def human_reviewed_without_reviewer(d):
        d["status"]["human_reviewed"] = True

    def implemented_flag_without_calculations(d):
        d["applications"][1]["status"]["calculation_implemented"] = True

    def calculations_for_unimplemented_application(d):
        calculation(d, "electric")["applications"].append("retrofit")

    def malformed_issue_id(d):
        d["issues"] = ["issue-17"]

    def malformed_effective_date(d):
        d["effective_date"] = "June 2019"

    def duplicate_variable(d):
        d["variables"].append(dict(variable(d, "rate")))

    return [
        unknown_source,
        unknown_field,
        deemed_without_value,
        optional_input_without_default,
        default_without_citation,
        required_with_default,
        deemed_with_default,
        choice_without_choices,
        derived_without_function,
        conditional_source_not_supported,
        unknown_variable_in_calculation,
        unknown_variable_in_derivation,
        unknown_output,
        unknown_application,
        bad_applies_when,
        output_produced_twice,
        interpretation_without_issue,
        human_reviewed_without_reviewer,
        implemented_flag_without_calculations,
        calculations_for_unimplemented_application,
        malformed_issue_id,
        malformed_effective_date,
        duplicate_variable,
    ]


@pytest.mark.parametrize("mutate", mutations(), ids=lambda f: f.__name__)
def test_invalid_measure_definitions_are_rejected(demo_measure_data, mutate):
    mutate(demo_measure_data)
    with pytest.raises(ValidationError):
        Measure.model_validate(demo_measure_data)


def test_lookup_keys_must_match_choices(demo_measure_data):
    del demo_measure_data["lookups"]["zone_factors"]["values"]["south"]
    with pytest.raises(ValidationError, match="keys must match choices"):
        Measure.model_validate(demo_measure_data)


def test_lookup_variable_requires_known_table(demo_measure_data):
    variable(demo_measure_data, "zone_factor")["lookup"] = "zone_factors_by_county"
    with pytest.raises(ValidationError, match="unknown lookup"):
        Measure.model_validate(demo_measure_data)


def test_human_review_requires_reviewer_and_date(demo_measure_data):
    demo_measure_data["status"]["human_reviewed"] = True
    demo_measure_data["review"] = {"reviewed_by": "A Reviewer", "reviewed_date": "2026-01-01"}
    assert Measure.model_validate(demo_measure_data).status.human_reviewed


def test_manifest_rejects_duplicate_ids():
    data = yaml.safe_load((DEMO_VERSION_DIR / "manifest.yaml").read_text())
    data["measures"].append(data["measures"][0])
    with pytest.raises(ValidationError, match="duplicate"):
        Manifest.model_validate(data)
