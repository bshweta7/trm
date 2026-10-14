"""Checks across every Delaware TRM v5 measure in the manifest."""

import inspect

import pytest

from trm_engine.measures import IMPLEMENTATIONS
from trm_engine.models import VariableSource
from trm_engine.registry import default_registry


def all_measures():
    registry = default_registry()
    return [registry.get(entry.id) for entry in registry.entries()]


def test_manifest_lists_implemented_measures():
    ids = {e.id for e in default_registry().entries()}
    assert ids == {"de-res-hvac-air-source-heat-pump", "de-res-water-heating-low-flow-shower-head"}


@pytest.mark.parametrize("measure", all_measures(), ids=lambda m: m.id)
def test_no_measure_is_marked_human_reviewed(measure):
    assert not measure.status.human_reviewed
    assert not any(a.status.human_reviewed for a in measure.applications)
    assert measure.review.reviewed_by is None


@pytest.mark.parametrize("measure", all_measures(), ids=lambda m: m.id)
def test_source_is_the_draft_trm(measure):
    assert (measure.jurisdiction, measure.trm_version, measure.source.status) == ("DE", "5.0", "draft")


@pytest.mark.parametrize("measure", all_measures(), ids=lambda m: m.id)
def test_yaml_functions_match_python_implementations(measure):
    """Every function named in YAML exists and takes exactly the listed variables."""
    functions = IMPLEMENTATIONS[measure.id]
    named = [(c.implementation.function, c.variables) for c in measure.calculations] + [
        (v.function, v.variables) for v in measure.variables if v.source is VariableSource.DERIVED
    ]
    for name, variables in named:
        assert list(inspect.signature(functions[name]).parameters) == variables, name
