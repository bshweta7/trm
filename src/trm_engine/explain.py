"""Explain how each output of a calculation result was obtained.

Built only from existing measure metadata and the values resolved during the
calculation. Nothing is recalculated. The documented equation is the measure
definition's ``equation_display`` text: documentation of the methodology, not
an expression that was executed or independently verified against the Python
implementation.
"""

from __future__ import annotations

from pydantic import BaseModel

from trm_engine.models import Citation, Measure, VariableSource
from trm_engine.registry import MeasureRegistry, default_registry
from trm_engine.service import CalculationResult, ValueOrigin

EQUATION_NOTE = (
    "Documented equation from the measure definition. It describes the methodology but is not "
    "executed or independently verified against the calculation code."
)


class ExplainedVariable(BaseModel):
    id: str
    symbol: str | None
    name: str
    value: float | str
    unit: str | None
    origin: ValueOrigin
    citation: Citation | None
    lookup: str | None
    issues: list[str]
    # 0: used directly by the calculation; 1+: an input to a derived value.
    depth: int
    # For derived values: the variables they were derived from, and their
    # documented formula (description text, not executed).
    derived_from: list[str]
    documented_formula: str | None


class OutputExplanation(BaseModel):
    output_id: str
    name: str
    value: float
    unit: str
    calculation_id: str
    calculation_name: str
    # Every output the same calculation (and documented equation) produces.
    calculation_outputs: list[str]
    documented_equation: str
    equation_note: str
    equation_as_printed: str | None
    interpretation: str | None
    source: Citation
    # Values used by the calculation, in definition order, each followed by the
    # inputs of any derived value. A calculation with several outputs lists the
    # values for all of them.
    variables: list[ExplainedVariable]
    # Issues attached to the calculation itself.
    issues: list[str]
    # Calculation issues plus issues on every listed variable.
    all_issues: list[str]


def _variables(measure: Measure, result: CalculationResult, roots: list[str]) -> list[ExplainedVariable]:
    explained: list[ExplainedVariable] = []
    seen: set[str] = set()

    def visit(var_id: str, depth: int) -> None:
        if var_id in seen:
            return
        seen.add(var_id)
        resolved = result.variables[var_id]
        definition = measure.variable(var_id)
        derived = definition.source is VariableSource.DERIVED
        explained.append(
            ExplainedVariable(
                **resolved.model_dump(),
                depth=depth,
                derived_from=list(definition.variables) if derived else [],
                documented_formula=definition.description.strip() if derived and definition.description else None,
            )
        )
        for dependency in definition.variables:
            visit(dependency, depth + 1)

    for var_id in roots:
        visit(var_id, 0)
    return explained


def explain(result: CalculationResult, registry: MeasureRegistry | None = None) -> list[OutputExplanation]:
    """One explanation per output in ``result``, in output order.

    Outputs that did not apply are not in ``result`` and are not explained.
    """
    measure = (registry or default_registry()).get(result.measure_id)
    explanations = []
    for output in result.outputs.values():
        calc = next(c for c in measure.calculations if c.id == output.calculation)
        variables = _variables(measure, result, calc.variables)
        explanations.append(
            OutputExplanation(
                output_id=output.id,
                name=output.name,
                value=output.value,
                unit=output.unit,
                calculation_id=calc.id,
                calculation_name=calc.name,
                calculation_outputs=list(calc.outputs),
                documented_equation=calc.equation_display.strip(),
                equation_note=EQUATION_NOTE,
                equation_as_printed=calc.equation_as_printed.strip() if calc.equation_as_printed else None,
                interpretation=output.interpretation,
                source=output.source,
                variables=variables,
                issues=list(output.issues),
                all_issues=sorted(set(output.issues).union(*(v.issues for v in variables))),
            )
        )
    return explanations
