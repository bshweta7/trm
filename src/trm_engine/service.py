"""Orchestrate a calculation: validate inputs, resolve variables, run the
implementation functions named in the measure YAML, and return structured,
source-cited results.
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum
from typing import Any

from pydantic import BaseModel

from trm_engine.inputs import validate_inputs
from trm_engine.measures import IMPLEMENTATIONS
from trm_engine.models import Citation, Measure, SourceDocument, Status, VariableSource
from trm_engine.registry import MeasureRegistry, default_registry


class ApplicationNotImplementedError(NotImplementedError):
    pass


class ValueOrigin(StrEnum):
    """Distinguishes values supplied by the user from values supplied by the TRM."""

    USER_INPUT = "user_input"
    TRM_DEFAULT = "trm_default"  # optional input not supplied; TRM default used
    DEEMED = "deemed"
    LOOKUP = "lookup"
    DERIVED = "derived"


class ResolvedVariable(BaseModel):
    id: str
    symbol: str | None
    name: str
    value: float | str
    unit: str | None
    origin: ValueOrigin
    citation: Citation | None
    lookup: str | None = None
    issues: list[str]


class OutputValue(BaseModel):
    id: str
    name: str
    value: float
    unit: str
    calculation: str
    equation: str
    source: Citation
    # Set when the result depends on an implementation decision the TRM does not state.
    interpretation: str | None
    issues: list[str]


class NotApplicable(BaseModel):
    calculation: str
    outputs: list[str]
    reason: str


class CalculationResult(BaseModel):
    measure_id: str
    measure_name: str
    jurisdiction: str
    trm_version: str
    source_document: SourceDocument
    application: str
    measure_code: str
    outputs: dict[str, OutputValue]
    not_applicable: list[NotApplicable]
    variables: dict[str, ResolvedVariable]
    status: Status


class _Resolver:
    def __init__(self, measure: Measure, inputs: Mapping[str, float | str]):
        self.measure = measure
        self.inputs = inputs
        self.functions = IMPLEMENTATIONS[measure.id]
        self.resolved: dict[str, ResolvedVariable] = {}
        self._in_progress: set[str] = set()

    def value(self, var_id: str) -> Any:
        return self.resolve(var_id).value

    def resolve(self, var_id: str) -> ResolvedVariable:
        if var_id in self.resolved:
            return self.resolved[var_id]
        if var_id in self._in_progress:
            raise ValueError(f"circular variable dependency at {var_id}")
        self._in_progress.add(var_id)

        var = self.measure.variable(var_id)
        lookup = None
        match var.source:
            case VariableSource.USER_INPUT if var_id in self.inputs:
                origin, value = ValueOrigin.USER_INPUT, self.inputs[var_id]
            case VariableSource.USER_INPUT:
                # Validation guarantees required inputs are present.
                origin, value = ValueOrigin.TRM_DEFAULT, var.default
            case VariableSource.DEEMED:
                origin, value = ValueOrigin.DEEMED, var.value
            case VariableSource.LOOKUP:
                origin, lookup = ValueOrigin.LOOKUP, var.lookup
                value = self.measure.lookups[var.lookup].values[self.value(var.lookup_key)]
            case VariableSource.DERIVED:
                origin = ValueOrigin.DERIVED
                value = self.functions[var.function](**{d: self.value(d) for d in var.variables})
            case _:
                raise NotImplementedError(f"variable source {var.source} for {var_id}")

        citation = var.citation
        if lookup is not None:
            citation = self.measure.lookups[lookup].source
        self.resolved[var_id] = ResolvedVariable(
            id=var.id,
            symbol=var.symbol,
            name=var.name,
            value=value,
            unit=var.unit,
            origin=origin,
            citation=citation,
            lookup=lookup,
            issues=list(var.issues) + (self.measure.lookups[lookup].issues if lookup else []),
        )
        self._in_progress.discard(var_id)
        return self.resolved[var_id]


def calculate(
    measure_id: str,
    application: str,
    inputs: Mapping[str, Any],
    registry: MeasureRegistry | None = None,
) -> CalculationResult:
    """Calculate all applicable outputs for one application of a measure."""
    measure = (registry or default_registry()).get(measure_id)
    app = measure.application(application)
    if not app.status.calculation_implemented:
        raise ApplicationNotImplementedError(f"{measure_id}: application {application!r} is not implemented")

    resolver = _Resolver(measure, validate_inputs(measure, application, inputs))
    outputs: dict[str, OutputValue] = {}
    not_applicable: list[NotApplicable] = []

    for calc in measure.calculations_for(application):
        unmet = {k: v for k, v in calc.applies_when.items() if resolver.value(k) != v}
        if unmet:
            not_applicable.append(
                NotApplicable(
                    calculation=calc.id,
                    outputs=calc.outputs,
                    reason="applies only when "
                    + ", ".join(f"{k} = {v}" for k, v in calc.applies_when.items()),
                )
            )
            continue

        function = resolver.functions[calc.implementation.function]
        values = function(**{v: resolver.value(v) for v in calc.variables})
        if set(values) != set(calc.outputs):
            raise RuntimeError(f"{calc.implementation.function} returned {sorted(values)}, expected {calc.outputs}")

        for output_id in calc.outputs:
            output = measure.output(output_id)
            outputs[output_id] = OutputValue(
                id=output_id,
                name=output.name,
                value=values[output_id],
                unit=output.unit,
                calculation=calc.id,
                equation=calc.equation_display,
                source=calc.source,
                interpretation=calc.interpretation,
                issues=calc.issues,
            )

    return CalculationResult(
        measure_id=measure.id,
        measure_name=measure.classification.name,
        jurisdiction=measure.jurisdiction,
        trm_version=measure.trm_version,
        source_document=measure.source,
        application=app.id,
        measure_code=app.measure_code,
        outputs=outputs,
        not_applicable=not_applicable,
        variables=resolver.resolved,
        status=app.status,
    )
