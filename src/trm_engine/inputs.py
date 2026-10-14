"""Validate user inputs against the variable specifications in measure YAML.

The YAML is the single source of truth for which inputs an application accepts
and their constraints, so a future UI can generate forms from the same data.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, create_model

from trm_engine.models import Measure, Variable, VariableSource, VariableType


class InputValidationError(ValueError):
    """Inputs failed validation. No result is produced.

    ``details`` lists one ``{"field": ..., "message": ...}`` dict per problem,
    for callers that display or serialize errors per field. ``errors`` holds the
    same information as ``"field: message"`` strings.
    """

    def __init__(self, details: list[dict[str, str]]):
        self.details = details
        self.errors = [f"{d['field']}: {d['message']}" for d in details]
        super().__init__("invalid inputs: " + "; ".join(self.errors))


def user_inputs_for(measure: Measure, application_id: str) -> list[Variable]:
    """User-input variables that the given application's calculations depend on."""
    needed: set[str] = set()
    pending: list[str] = []
    for calc in measure.calculations_for(application_id):
        pending.extend(calc.variables)
        pending.extend(calc.applies_when)
    for rule in measure.warnings_for(application_id):
        pending.extend(rule.variables)
    while pending:
        var_id = pending.pop()
        if var_id in needed:
            continue
        needed.add(var_id)
        var = measure.variable(var_id)
        pending.extend(var.variables)
        if var.lookup_key:
            pending.append(var.lookup_key)
    return [v for v in measure.variables if v.id in needed and v.source is VariableSource.USER_INPUT]


def _field(var: Variable) -> tuple[Any, Any]:
    if var.type is VariableType.CHOICE:
        annotation: Any = Literal[tuple(c.id for c in var.choices or [])]
        constraints: dict[str, Any] = {}
    else:
        annotation = float
        constraints = {
            "strict": True,
            "allow_inf_nan": False,
            "gt": var.exclusive_minimum,
            "ge": var.minimum,
            "le": var.maximum,
        }
    if not var.required:
        annotation = annotation | None
    default = ... if var.required else None
    return annotation, Field(default, description=var.name, **constraints)


def validate_inputs(
    measure: Measure, application_id: str, inputs: Mapping[str, Any]
) -> dict[str, float | str]:
    """Return only the inputs the user supplied, validated. Defaults are applied later."""
    variables = user_inputs_for(measure, application_id)
    model: type[BaseModel] = create_model(
        f"{measure.id}:{application_id}:inputs",
        __config__=ConfigDict(extra="forbid"),
        **{v.id: _field(v) for v in variables},
    )
    try:
        validated = model.model_validate(dict(inputs))
    except ValidationError as exc:
        raise InputValidationError(
            [{"field": ".".join(map(str, e["loc"])) or "<root>", "message": e["msg"]} for e in exc.errors()]
        ) from None
    return {k: v for k, v in validated.model_dump(exclude_unset=True).items() if v is not None}
