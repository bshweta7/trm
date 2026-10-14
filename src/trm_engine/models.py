"""Pydantic schema for TRM reference data (measure YAML files and manifests).

These models validate structure and internal consistency only. Passing
validation does not mean a measure is technically correct; that is tracked by
``Status`` and docs/validation_register.md.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

IssueId = Annotated[str, StringConstraints(pattern=r"^VR-\d{3}$")]
Identifier = Annotated[str, StringConstraints(pattern=r"^[a-z0-9][a-z0-9_]*$")]


class StrictModel(BaseModel):
    """Reject unknown keys so typos and invented fields fail loudly."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class VariableSource(StrEnum):
    """Where a variable's value originates (architecture.md section 8)."""

    USER_INPUT = "user_input"
    DEEMED = "deemed"
    LOOKUP = "lookup"
    DERIVED = "derived"
    CONDITIONAL = "conditional"


class VariableType(StrEnum):
    NUMBER = "number"
    CHOICE = "choice"


class Citation(StrictModel):
    """Location of a value, table, or equation in the source TRM."""

    page: int | None = None
    pages: list[int] | None = None
    section: str | None = None
    table: str | None = None
    footnote: int | None = None
    note: str | None = None


class SourceDocument(StrictModel):
    document: str
    version: str
    status: str
    url: str
    page_start: int
    page_end: int
    section: str | None = None


class Classification(StrictModel):
    market_sector: str
    category: str
    name: str


class TrmIdentifiers(StrictModel):
    measure_codes: list[str]
    section: str | None = None


class Choice(StrictModel):
    id: Identifier
    name: str


class Variable(StrictModel):
    id: Identifier
    symbol: str | None = None
    name: str
    description: str | None = None
    unit: str | None = None
    type: VariableType = VariableType.NUMBER
    source: VariableSource

    # user_input
    required: bool = False
    default: float | None = None
    choices: list[Choice] | None = None
    exclusive_minimum: float | None = None
    minimum: float | None = None
    maximum: float | None = None

    # deemed
    value: float | None = None

    # lookup
    lookup: Identifier | None = None
    lookup_key: Identifier | None = None

    # derived
    function: Identifier | None = None
    variables: list[Identifier] = Field(default_factory=list)

    citation: Citation | None = None
    issues: list[IssueId] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_source_fields(self) -> Self:
        s = self.source
        if s is VariableSource.USER_INPUT:
            if self.required and self.default is not None:
                raise ValueError(f"{self.id}: a required input cannot also have a default")
            if not self.required and self.default is None:
                raise ValueError(f"{self.id}: an optional input needs a TRM default")
            if self.default is not None and self.citation is None:
                raise ValueError(f"{self.id}: a TRM default must have a citation")
        elif s is VariableSource.DEEMED:
            if self.value is None:
                raise ValueError(f"{self.id}: deemed variables need a value")
        elif s is VariableSource.LOOKUP:
            if not (self.lookup and self.lookup_key):
                raise ValueError(f"{self.id}: lookup variables need lookup and lookup_key")
        elif s is VariableSource.DERIVED:
            if not (self.function and self.variables):
                raise ValueError(f"{self.id}: derived variables need function and variables")
        elif s is VariableSource.CONDITIONAL:
            raise ValueError(f"{self.id}: conditional variables are not supported yet")

        if s is not VariableSource.USER_INPUT and (self.required or self.default is not None):
            raise ValueError(f"{self.id}: required/default only apply to user_input variables")
        if (self.type is VariableType.CHOICE) != (self.choices is not None):
            raise ValueError(f"{self.id}: choices must be given exactly when type is choice")
        return self


class Lookup(StrictModel):
    description: str
    unit: str | None = None
    values: dict[Identifier, float]
    source: Citation
    issues: list[IssueId] = Field(default_factory=list)


class Output(StrictModel):
    id: Identifier
    name: str
    unit: str
    description: str | None = None


class Implementation(StrictModel):
    function: Identifier


class Calculation(StrictModel):
    id: Identifier
    name: str
    applications: list[Identifier]
    outputs: list[Identifier]
    variables: list[Identifier]
    # Calculation runs only when every listed variable equals the given choice.
    applies_when: dict[Identifier, Identifier] = Field(default_factory=dict)
    # Equation as implemented. Documentation only; never executed.
    equation_display: str
    # Only present when the TRM's printed equation differs from what is implemented.
    equation_as_printed: str | None = None
    # Any implementation decision not explicitly stated by the TRM.
    interpretation: str | None = None
    implementation: Implementation
    source: Citation
    issues: list[IssueId] = Field(default_factory=list)

    @model_validator(mode="after")
    def _interpretation_is_traceable(self) -> Self:
        if (self.equation_as_printed or self.interpretation) and not self.issues:
            raise ValueError(f"{self.id}: interpretations must reference validation-register issues")
        return self


class WarningRule(StrictModel):
    """A warning returned with results. Not an error: outputs are still calculated.

    Emitted on every calculation for the listed applications, or, when
    ``function`` is given, only when that function returns True for ``variables``.
    """

    id: Identifier
    applications: list[Identifier]
    message: str
    function: Identifier | None = None
    variables: list[Identifier] = Field(default_factory=list)
    issues: list[IssueId] = Field(default_factory=list)

    @model_validator(mode="after")
    def _function_needs_variables(self) -> Self:
        if (self.function is None) != (not self.variables):
            raise ValueError(f"warning {self.id}: function and variables must be given together")
        return self


class Status(StrictModel):
    """Implementation and validation status (architecture.md section 18)."""

    metadata_extracted: bool
    variables_extracted: bool
    equations_extracted: bool
    calculation_implemented: bool
    automated_tests: bool
    human_reviewed: bool


class Review(StrictModel):
    reviewed_by: str | None = None
    reviewed_date: str | None = None
    notes: list[str] = Field(default_factory=list)


class Baseline(StrictModel):
    type: str
    description: str


class Application(StrictModel):
    id: Identifier
    name: str
    measure_code: str
    description: str | None = None
    baseline: Baseline
    status: Status
    source: Citation
    issues: list[IssueId] = Field(default_factory=list)


class MeasureLife(StrictModel):
    value: float
    unit: str
    source: Citation


class Measure(StrictModel):
    id: Annotated[str, StringConstraints(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$")]
    jurisdiction: str
    trm_version: str
    classification: Classification
    trm_identifiers: TrmIdentifiers
    # The TRM gives some effective dates to month precision only (e.g. "May 2018").
    effective_date: Annotated[str, StringConstraints(pattern=r"^\d{4}-\d{2}(-\d{2})?$")]
    end_date: str | None = None
    source: SourceDocument
    description: str
    applications: list[Application]
    variables: list[Variable]
    lookups: dict[Identifier, Lookup] = Field(default_factory=dict)
    outputs: list[Output]
    calculations: list[Calculation]
    warnings: list[WarningRule] = Field(default_factory=list)
    measure_life: MeasureLife | None = None
    status: Status
    review: Review = Review()
    issues: list[IssueId] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_references(self) -> Self:
        errors: list[str] = []
        variables = {v.id: v for v in self.variables}
        outputs = {o.id for o in self.outputs}
        applications = {a.id for a in self.applications}

        for kind, ids in (
            ("variable", [v.id for v in self.variables]),
            ("output", [o.id for o in self.outputs]),
            ("application", [a.id for a in self.applications]),
            ("calculation", [c.id for c in self.calculations]),
            ("warning", [w.id for w in self.warnings]),
        ):
            if len(ids) != len(set(ids)):
                errors.append(f"duplicate {kind} ids")

        for v in self.variables:
            for dep in v.variables:
                if dep not in variables:
                    errors.append(f"variable {v.id}: unknown variable {dep!r}")
            if v.source is VariableSource.LOOKUP:
                table = self.lookups.get(v.lookup or "")
                key = variables.get(v.lookup_key or "")
                if table is None:
                    errors.append(f"variable {v.id}: unknown lookup {v.lookup!r}")
                elif key is None or key.choices is None:
                    errors.append(f"variable {v.id}: lookup_key must be a choice variable")
                elif set(table.values) != {c.id for c in key.choices}:
                    errors.append(f"lookup {v.lookup}: keys must match choices of {key.id}")

        produced: dict[str, set[str]] = {}
        for c in self.calculations:
            for app in c.applications:
                if app not in applications:
                    errors.append(f"calculation {c.id}: unknown application {app!r}")
                for out in c.outputs:
                    if out in produced.setdefault(app, set()):
                        errors.append(f"output {out} produced twice for application {app}")
                    produced[app].add(out)
            for out in c.outputs:
                if out not in outputs:
                    errors.append(f"calculation {c.id}: unknown output {out!r}")
            for dep in c.variables:
                if dep not in variables:
                    errors.append(f"calculation {c.id}: unknown variable {dep!r}")
            for var_id, choice in c.applies_when.items():
                var = variables.get(var_id)
                if var is None or var.choices is None or choice not in {ch.id for ch in var.choices}:
                    errors.append(f"calculation {c.id}: invalid applies_when {var_id}={choice}")

        for w in self.warnings:
            for app in w.applications:
                if app not in applications:
                    errors.append(f"warning {w.id}: unknown application {app!r}")
            for dep in w.variables:
                if dep not in variables:
                    errors.append(f"warning {w.id}: unknown variable {dep!r}")

        for app in self.applications:
            if app.status.calculation_implemented and app.id not in produced:
                errors.append(f"application {app.id} is marked implemented but has no calculations")
            if not app.status.calculation_implemented and app.id in produced:
                errors.append(f"application {app.id} has calculations but is marked not implemented")

        for status in [self.status, *(a.status for a in self.applications)]:
            if status.human_reviewed and not (self.review.reviewed_by and self.review.reviewed_date):
                errors.append("human_reviewed requires review.reviewed_by and review.reviewed_date")

        if errors:
            raise ValueError("; ".join(errors))
        return self

    def variable(self, variable_id: str) -> Variable:
        for v in self.variables:
            if v.id == variable_id:
                return v
        raise KeyError(variable_id)

    def output(self, output_id: str) -> Output:
        for o in self.outputs:
            if o.id == output_id:
                return o
        raise KeyError(output_id)

    def application(self, application_id: str) -> Application:
        for a in self.applications:
            if a.id == application_id:
                return a
        raise KeyError(application_id)

    def calculations_for(self, application_id: str) -> list[Calculation]:
        return [c for c in self.calculations if application_id in c.applications]

    def warnings_for(self, application_id: str) -> list[WarningRule]:
        return [w for w in self.warnings if application_id in w.applications]


class ManifestEntry(StrictModel):
    id: str
    sector: str
    category: str
    name: str
    file: str


class Manifest(StrictModel):
    jurisdiction: str
    version: str
    measures: list[ManifestEntry]

    @model_validator(mode="after")
    def _unique_ids(self) -> Self:
        ids = [m.id for m in self.measures]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate measure ids in manifest")
        return self
