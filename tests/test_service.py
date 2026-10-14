"""Input validation, value resolution, dispatch, and provenance, using the
synthetic demo measure and stub calculation functions."""

import math

import pytest

from conftest import DEMO_MEASURE_ID, DEMO_VERSION_DIR
from trm_engine import ApplicationNotImplementedError, InputValidationError, calculate, input_variables
from trm_engine.inputs import user_inputs_for
from trm_engine.measures import IMPLEMENTATIONS
from trm_engine.registry import MeasureRegistry
from trm_engine.service import ValueOrigin


def unit_hours(quantity, hours):
    return quantity * hours


def electric(unit_hours, rate, zone_factor):
    return {"kwh_savings": unit_hours * rate * zone_factor}


def gas(unit_hours, rate):
    return {"therm_savings": unit_hours * rate / 100}


def large_quantity(quantity):
    return quantity > 5


@pytest.fixture
def registry(monkeypatch):
    monkeypatch.setitem(
        IMPLEMENTATIONS,
        DEMO_MEASURE_ID,
        {"unit_hours": unit_hours, "electric": electric, "gas": gas, "large_quantity": large_quantity},
    )
    return MeasureRegistry(DEMO_VERSION_DIR)


@pytest.fixture
def run(registry):
    def run(inputs, application="time_of_sale"):
        return calculate(DEMO_MEASURE_ID, application, inputs, registry=registry)

    return run


ELECTRIC_NORTH = {"fuel": "electric", "zone": "north", "quantity": 2}


def test_electric_with_defaults(run):
    # 2 widgets x 1000 h (default) x 0.5 x 1.2 (north) = 1200 kWh
    result = run(ELECTRIC_NORTH)
    assert {k: v.value for k, v in result.outputs.items()} == {"kwh_savings": pytest.approx(1200)}
    assert result.outputs["kwh_savings"].unit == "kWh/year"
    assert result.outputs["kwh_savings"].interpretation is None


def test_inapplicable_calculation_is_omitted_not_zero(run):
    result = run(ELECTRIC_NORTH)
    assert "therm_savings" not in result.outputs
    [skipped] = result.not_applicable
    assert (skipped.calculation, skipped.outputs) == ("gas", ["therm_savings"])
    assert skipped.reason == "applies only when fuel = gas"


def test_gas_carries_interpretation_and_issues(run):
    # 2 x 1000 x 0.5 / 100 = 10 therms
    result = run({"fuel": "gas", "zone": "south", "quantity": 2})
    therms = result.outputs["therm_savings"]
    assert therms.value == pytest.approx(10)
    assert therms.interpretation == "Divisor assumed to be 100."
    assert therms.issues == ["VR-000"]
    assert [na.calculation for na in result.not_applicable] == ["electric"]


def test_provenance(run):
    v = run(ELECTRIC_NORTH).variables
    assert v["quantity"].origin is ValueOrigin.USER_INPUT
    assert (v["hours"].value, v["hours"].origin, v["hours"].citation.page) == (1000, ValueOrigin.TRM_DEFAULT, 1)
    assert (v["rate"].value, v["rate"].origin) == (0.5, ValueOrigin.DEEMED)
    assert (v["zone_factor"].value, v["zone_factor"].origin) == (1.2, ValueOrigin.LOOKUP)
    assert v["zone_factor"].lookup == "zone_factors"
    assert v["zone_factor"].citation.table == "Zone factors"  # the lookup table's citation
    assert (v["unit_hours"].value, v["unit_hours"].origin) == (2000, ValueOrigin.DERIVED)


def test_user_value_replaces_default(run):
    result = run(ELECTRIC_NORTH | {"hours": 500})
    assert result.variables["hours"].origin is ValueOrigin.USER_INPUT
    assert result.outputs["kwh_savings"].value == pytest.approx(600)


def test_result_metadata(run):
    result = run(ELECTRIC_NORTH)
    assert (result.measure_id, result.application, result.measure_code) == (
        DEMO_MEASURE_ID,
        "time_of_sale",
        "DEMO_TOS",
    )
    assert result.source_document.status == "fixture"
    assert result.status.human_reviewed is False


def test_user_inputs_for_application(registry):
    measure = registry.get(DEMO_MEASURE_ID)
    assert [v.id for v in user_inputs_for(measure, "time_of_sale")] == ["fuel", "zone", "quantity", "hours"]


@pytest.mark.parametrize(
    ("inputs", "field"),
    [
        ({"zone": "north", "quantity": 2}, "fuel"),  # missing required
        (ELECTRIC_NORTH | {"zone": "east"}, "zone"),
        (ELECTRIC_NORTH | {"quantity": 0}, "quantity"),
        (ELECTRIC_NORTH | {"quantity": 11}, "quantity"),
        (ELECTRIC_NORTH | {"quantity": "2"}, "quantity"),
        (ELECTRIC_NORTH | {"quantity": True}, "quantity"),
        (ELECTRIC_NORTH | {"quantity": math.nan}, "quantity"),
        (ELECTRIC_NORTH | {"hours": -1}, "hours"),
        (ELECTRIC_NORTH | {"rate": 0.7}, "rate"),  # deemed values cannot be overridden
        (ELECTRIC_NORTH | {"colour": "blue"}, "colour"),
    ],
)
def test_invalid_inputs(run, inputs, field):
    with pytest.raises(InputValidationError, match=field) as exc:
        run(inputs)
    assert exc.value.errors


def test_unconditional_warning_is_always_returned(run):
    [warning] = run(ELECTRIC_NORTH).warnings
    assert warning.model_dump() == {
        "code": "always_shown",
        "message": "Shown on every Time of Sale result.",
        "issues": ["VR-000"],
        "variables": {},
    }


def test_conditional_warning_reports_the_values_it_checked(run):
    result = run(ELECTRIC_NORTH | {"quantity": 6})
    assert [w.code for w in result.warnings] == ["always_shown", "large_quantity"]
    assert result.warnings[1].variables == {"quantity": 6}
    # Warnings never change outputs: 6 x 1000 x 0.5 x 1.2
    assert result.outputs["kwh_savings"].value == pytest.approx(3600)


def test_warnings_are_separate_from_issue_references(run):
    result = run({"fuel": "gas", "zone": "south", "quantity": 2})
    assert result.outputs["therm_savings"].issues == ["VR-000"]
    assert [w.code for w in result.warnings] == ["always_shown"]


def test_warning_check_must_return_bool(run, monkeypatch):
    monkeypatch.setitem(IMPLEMENTATIONS[DEMO_MEASURE_ID], "large_quantity", lambda quantity: quantity)
    with pytest.raises(RuntimeError, match="bool"):
        run(ELECTRIC_NORTH)


def test_input_variables_public_metadata(registry):
    variables = input_variables(DEMO_MEASURE_ID, "time_of_sale", registry=registry)
    assert [v.id for v in variables] == ["fuel", "zone", "quantity", "hours"]
    hours = variables[3]
    assert (hours.required, hours.default, hours.unit, hours.citation.page) == (False, 1000, "hours/year", 1)
    assert [c.id for c in variables[0].choices] == ["electric", "gas"]


def test_input_variables_for_unimplemented_or_unknown_application(registry):
    with pytest.raises(ApplicationNotImplementedError):
        input_variables(DEMO_MEASURE_ID, "retrofit", registry=registry)
    with pytest.raises(KeyError):
        input_variables(DEMO_MEASURE_ID, "new_construction", registry=registry)


def test_validation_error_details_are_structured(run):
    with pytest.raises(InputValidationError) as exc:
        run({"zone": "east", "quantity": 2, "colour": "blue"})
    details = {d["field"]: d["message"] for d in exc.value.details}
    assert set(details) == {"fuel", "zone", "colour"}
    assert details["fuel"] == "Field required"
    assert details["colour"] == "Extra inputs are not permitted"
    assert exc.value.errors == [f"{d['field']}: {d['message']}" for d in exc.value.details]


def test_unimplemented_application(run):
    with pytest.raises(ApplicationNotImplementedError):
        run(ELECTRIC_NORTH, application="retrofit")


def test_unknown_application(run):
    with pytest.raises(KeyError):
        run(ELECTRIC_NORTH, application="new_construction")


def test_function_returning_wrong_outputs_is_an_error(run, monkeypatch):
    monkeypatch.setitem(IMPLEMENTATIONS[DEMO_MEASURE_ID], "electric", lambda **_: {"kwh": 1.0})
    with pytest.raises(RuntimeError, match="expected"):
        run(ELECTRIC_NORTH)
