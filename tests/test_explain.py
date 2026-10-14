"""explain(): generic behaviour on the synthetic demo measure."""

import pytest

from conftest import DEMO_MEASURE_ID, DEMO_VERSION_DIR
from trm_engine import calculate, explain
from trm_engine.explain import EQUATION_NOTE
from trm_engine.measures import IMPLEMENTATIONS
from trm_engine.registry import MeasureRegistry
from trm_engine.service import ValueOrigin


@pytest.fixture
def registry(monkeypatch):
    monkeypatch.setitem(
        IMPLEMENTATIONS,
        DEMO_MEASURE_ID,
        {
            "unit_hours": lambda quantity, hours: quantity * hours,
            "electric": lambda unit_hours, rate, zone_factor: {"kwh_savings": unit_hours * rate * zone_factor},
            "gas": lambda unit_hours, rate: {"therm_savings": unit_hours * rate / 100},
            "large_quantity": lambda quantity: quantity > 5,
        },
    )
    return MeasureRegistry(DEMO_VERSION_DIR)


def run(registry, fuel):
    result = calculate(DEMO_MEASURE_ID, "time_of_sale", {"fuel": fuel, "zone": "north", "quantity": 2}, registry=registry)
    return result, explain(result, registry=registry)


def test_one_explanation_per_applicable_output(registry):
    _, explanations = run(registry, "electric")
    assert [e.output_id for e in explanations] == ["kwh_savings"]  # therm_savings did not apply


def test_documented_equation_is_labelled_as_documentation(registry):
    [e] = run(registry, "electric")[1]
    assert e.documented_equation == "kWh = widget-hours × rate × zone factor"
    assert e.equation_note == EQUATION_NOTE
    assert "not executed or independently verified" in e.equation_note
    assert (e.calculation_id, e.calculation_name, e.calculation_outputs) == ("electric", "Electric savings", ["kwh_savings"])


def test_result_and_units_come_from_the_result(registry):
    result, [e] = run(registry, "electric")
    assert (e.name, e.value, e.unit) == ("Electric savings", result.outputs["kwh_savings"].value, "kWh/year")
    assert e.source.page == 1


def test_variables_include_derived_inputs_with_provenance(registry):
    result, [e] = run(registry, "electric")
    assert [(v.id, v.depth) for v in e.variables] == [
        ("unit_hours", 0),
        ("quantity", 1),
        ("hours", 1),
        ("rate", 0),
        ("zone_factor", 0),
    ]
    by_id = {v.id: v for v in e.variables}
    assert by_id["unit_hours"].derived_from == ["quantity", "hours"]
    assert by_id["unit_hours"].origin is ValueOrigin.DERIVED
    assert by_id["hours"].origin is ValueOrigin.TRM_DEFAULT and by_id["hours"].citation.page == 1
    assert by_id["zone_factor"].lookup == "zone_factors" and by_id["zone_factor"].citation.table == "Zone factors"
    assert by_id["rate"].documented_formula is None
    # Values are exactly the ones resolved during the calculation; nothing is recalculated.
    for v in e.variables:
        assert v.value == result.variables[v.id].value


def test_interpretation_and_issues(registry):
    [e] = run(registry, "gas")[1]
    assert e.interpretation == "Divisor assumed to be 100."
    assert e.issues == ["VR-000"] and e.all_issues == ["VR-000"]
    assert e.equation_as_printed is None


def test_explain_does_not_change_the_result_and_is_serializable(registry):
    result, explanations = run(registry, "electric")
    before = result.model_dump()
    explain(result, registry=registry)
    assert result.model_dump() == before
    assert '"documented_equation"' in explanations[0].model_dump_json()
