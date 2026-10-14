"""Framework-independent view models for displaying TRM measures and results.

Everything here converts public ``trm_engine`` objects into plain data (labels,
rows, links). It contains no TRM formulas, values, defaults, or validation
rules, and imports no UI framework, so it is tested without Streamlit.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any, Literal
from urllib.parse import urlencode

from trm_engine import CalculationResult, ValueOrigin
from trm_engine.models import Application, Citation, Measure, Variable, VariableType

REPOSITORY_URL = "https://github.com/bshweta7/trm"
VALIDATION_REGISTER_URL = f"{REPOSITORY_URL}/blob/dev/docs/validation_register.md"

FIELD_GROUPS = {
    "selections": "Selections",
    "required": "Required values",
    "optional": "Optional — leave blank to use the TRM default",
}
REQUIRED_MESSAGE = "This field is required."
NOT_AVAILABLE_MESSAGE = "This application isn't available yet."
UNEXPECTED_ERROR_MESSAGE = (
    "Something went wrong while calculating. Please try again, and report a bug if it keeps happening."
)

ResultStatus = Literal["none", "current", "stale", "previous"]

ORIGIN_LABELS = {
    ValueOrigin.USER_INPUT: "User input",
    ValueOrigin.TRM_DEFAULT: "TRM default",
    ValueOrigin.DEEMED: "Deemed (TRM)",
    ValueOrigin.LOOKUP: "TRM table lookup",
    ValueOrigin.DERIVED: "Derived",
}


@dataclass(frozen=True)
class FormField:
    id: str
    label: str
    kind: Literal["number", "choice"]
    required: bool
    help: str
    options: tuple[tuple[str, str], ...] = ()  # (choice id, display name)
    placeholder: str | None = None


@dataclass(frozen=True)
class MeasureHeader:
    title: str
    trm: str
    is_draft: bool
    source_status: str
    source_url: str
    pages: str
    measure_code: str
    human_reviewed: bool


def format_value(value: float | str) -> str:
    """Display formatting only (about 4 significant figures); never used in calculations."""
    if isinstance(value, str):
        return value
    if value == 0:
        return "0"
    if abs(value) >= 1000:
        return f"{value:,.0f}"
    return f"{value:.4g}"


def format_citation(citation: Citation | None) -> str:
    if citation is None:
        return ""
    parts = []
    if citation.page is not None:
        parts.append(f"p. {citation.page}")
    if citation.pages:
        parts.append("pp. " + ", ".join(map(str, citation.pages)))
    if citation.section:
        parts.append(citation.section)
    if citation.table:
        parts.append(f"table: {citation.table}")
    if citation.footnote is not None:
        parts.append(f"footnote {citation.footnote}")
    if citation.note:
        parts.append(citation.note)
    return "; ".join(parts)


def issue_url(issue_id: str) -> str:
    return f"{VALIDATION_REGISTER_URL}#{issue_id.lower()}"


def issue_links(issue_ids: Iterable[str]) -> list[tuple[str, str]]:
    return [(i, issue_url(i)) for i in sorted(set(issue_ids))]


def measure_header(measure: Measure, application: Application) -> MeasureHeader:
    source = measure.source
    return MeasureHeader(
        title=f"{measure.classification.name} — {application.name}",
        trm=f"{measure.jurisdiction} TRM {measure.trm_version}",
        is_draft=source.status == "draft",
        source_status=source.status,
        source_url=source.url,
        pages=f"pp. {source.page_start}–{source.page_end}",
        measure_code=application.measure_code,
        human_reviewed=application.status.human_reviewed,
    )


def application_options(measure: Measure) -> list[tuple[str, str, bool]]:
    """(application id, display name, implemented) for every application."""
    return [(a.id, a.name, a.status.calculation_implemented) for a in measure.applications]


def _label(var: Variable) -> str:
    label = var.name
    if var.symbol and var.symbol != var.name:
        label += f" ({var.symbol})"
    if var.unit:
        label += f" [{var.unit}]"
    return label


def _help(var: Variable) -> str:
    lines = [var.description.strip()] if var.description else []
    if var.citation:
        lines.append(f"Source: {format_citation(var.citation)}")
    if var.issues:
        lines.append("Related validation issues: " + ", ".join(var.issues))
    return "\n\n".join(lines)


def form_fields(variables: Iterable[Variable]) -> list[FormField]:
    """Widget specifications for the inputs returned by ``trm_engine.input_variables``.

    Constraints are not repeated here; ``trm_engine.calculate`` validates inputs.
    """
    fields = []
    for var in variables:
        placeholder = None
        if var.default is not None:
            placeholder = f"TRM default: {format_value(var.default)}" + (f" {var.unit}" if var.unit else "")
        fields.append(
            FormField(
                id=var.id,
                label=_label(var),
                kind="choice" if var.type is VariableType.CHOICE else "number",
                required=var.required,
                help=_help(var),
                options=tuple((c.id, c.name) for c in var.choices or ()),
                placeholder=placeholder,
            )
        )
    return fields


def collect_inputs(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Drop fields the user left empty so the engine applies (and records) TRM defaults."""
    return {k: v for k, v in raw.items() if v is not None and v != ""}


def output_rows(result: CalculationResult) -> list[dict[str, str]]:
    return [
        {
            "Output": o.name,
            "Value": format_value(o.value),
            "Unit": o.unit,
            "Interpretation": "Yes" if o.interpretation else "",
            "Source": format_citation(o.source),
            "Issues": ", ".join(o.issues),
        }
        for o in result.outputs.values()
    ]


def interpretation_notes(result: CalculationResult) -> list[dict[str, str]]:
    """One note per calculation whose outputs depend on an implementation interpretation."""
    notes: dict[str, dict[str, str]] = {}
    for o in result.outputs.values():
        if o.interpretation:
            note = notes.setdefault(
                o.calculation,
                {"outputs": "", "interpretation": o.interpretation, "equation": o.equation, "issues": ", ".join(o.issues)},
            )
            note["outputs"] = ", ".join(filter(None, [note["outputs"], o.name]))
    return list(notes.values())


def not_applicable_rows(result: CalculationResult, measure: Measure) -> list[dict[str, str]]:
    return [
        {
            "Outputs": ", ".join(measure.output(o).name for o in na.outputs),
            "Reason": na.reason,
        }
        for na in result.not_applicable
    ]


def warning_items(result: CalculationResult) -> list[dict[str, str]]:
    return [
        {
            "code": w.code,
            "message": w.message,
            "issues": ", ".join(w.issues),
            "checked": ", ".join(f"{k} = {format_value(v)}" for k, v in w.variables.items()),
        }
        for w in result.warnings
    ]


def provenance_rows(result: CalculationResult) -> list[dict[str, str]]:
    """Every resolved value at full precision, with where it came from."""
    rows = []
    for v in result.variables.values():
        source = format_citation(v.citation)
        if v.lookup:
            source = f"{v.lookup} ({source})" if source else v.lookup
        rows.append(
            {
                "Symbol": v.symbol or "",
                "Name": v.name,
                "Value": str(v.value),
                "Unit": v.unit or "",
                "Origin": ORIGIN_LABELS[v.origin],
                "Source": source,
                "Issues": ", ".join(v.issues),
            }
        )
    return rows


def related_issue_ids(measure: Measure, application_id: str, result: CalculationResult | None = None) -> list[str]:
    """Validation-register issue IDs relevant to this measure application.

    Without a result: the measure, application, its calculations and warning
    rules. With a result: also every output, resolved variable, and warning.
    """
    ids = set(measure.issues) | set(measure.application(application_id).issues)
    for calc in measure.calculations_for(application_id):
        ids.update(calc.issues)
    for rule in measure.warnings_for(application_id):
        ids.update(rule.issues)
    if result is not None:
        for group in (result.outputs.values(), result.variables.values(), result.warnings):
            for item in group:
                ids.update(item.issues)
    return sorted(ids)


def group_fields(fields: Iterable[FormField]) -> list[tuple[str, list[FormField]]]:
    """Group fields by existing metadata (choice / required / has a TRM default).

    Field order within a group follows the measure definition. Empty groups
    are omitted.
    """
    groups: dict[str, list[FormField]] = {key: [] for key in FIELD_GROUPS}
    for f in fields:
        key = "selections" if f.kind == "choice" else "required" if f.required else "optional"
        groups[key].append(f)
    return [(FIELD_GROUPS[key], items) for key, items in groups.items() if items]


def status_notice(header: MeasureHeader) -> str | None:
    """One compact notice about draft source data and missing independent validation."""
    parts = []
    if header.is_draft:
        parts.append(f"Based on the **{header.source_status}** {header.trm}.")
    if not header.human_reviewed:
        parts.append("Calculations have not been independently validated.")
    return " ".join(parts) or None


def output_metrics(result: CalculationResult) -> list[dict[str, str]]:
    """Every output as a metric: label, value with unit, and help text.

    Outputs that depend on an implementation interpretation are marked with †.
    """
    metrics = []
    for o in result.outputs.values():
        help_text = f"Source: {format_citation(o.source)}"
        if o.interpretation:
            help_text = f"{o.interpretation}\n\n{help_text}"
        if o.issues:
            help_text += "\n\nRelated validation issues: " + ", ".join(o.issues)
        metrics.append(
            {
                "label": o.name + (" †" if o.interpretation else ""),
                "value": f"{format_value(o.value)} {o.unit}",
                "help": help_text,
            }
        )
    return metrics


def _matches(slot: Mapping[str, Any] | None, measure_id: str, application_id: str, inputs: Mapping[str, Any]) -> bool:
    return (
        slot is not None
        and slot["measure_id"] == measure_id
        and slot["application"] == application_id
        and slot["inputs"] == dict(inputs)
    )


def current_failure(
    failure: Mapping[str, Any] | None, measure_id: str, application_id: str, inputs: Mapping[str, Any]
) -> list[str] | None:
    """Error messages from the last failed calculation, if it was for exactly these inputs."""
    return list(failure["messages"]) if _matches(failure, measure_id, application_id, inputs) else None


def result_status(
    stored: Mapping[str, Any] | None,
    failure: Mapping[str, Any] | None,
    measure_id: str,
    application_id: str,
    inputs: Mapping[str, Any],
) -> ResultStatus:
    """How the last successful result relates to what is on screen now.

    - ``none``: no result, or it belongs to another measure or application.
    - ``current``: it was calculated from exactly the current inputs.
    - ``previous``: calculating the current inputs failed; the result is from earlier inputs.
    - ``stale``: the inputs changed and have not been calculated yet.
    """
    if stored is None or (stored["measure_id"], stored["application"]) != (measure_id, application_id):
        return "none"
    if _matches(failure, measure_id, application_id, inputs):
        return "previous"
    if stored["inputs"] == dict(inputs):
        return "current"
    return "stale"


def validation_messages(details: Iterable[Mapping[str, str]], fields: Iterable[FormField]) -> list[str]:
    """User-facing messages for ``InputValidationError.details``, using field labels."""
    labels = {f.id: f.label for f in fields}
    return [
        f"{labels.get(d['field'], d['field'])}: "
        + (REQUIRED_MESSAGE if d["message"] == "Field required" else d["message"])
        for d in details
    ]


def bug_report_url(measure: Measure | None = None, application: Application | None = None) -> str:
    """Link to a new GitHub issue, prefilled with the measure and TRM version (no user inputs)."""
    if measure is None or application is None:
        return f"{REPOSITORY_URL}/issues/new"
    title = f"Bug: {measure.classification.name} — {application.name}"
    body = (
        f"Measure: {measure.id}\n"
        f"Application: {application.id}\n"
        f"TRM: {measure.jurisdiction} {measure.trm_version} ({measure.source.status})\n\n"
        "What happened?\n\n\nWhat did you expect?\n"
    )
    return f"{REPOSITORY_URL}/issues/new?" + urlencode({"title": title, "body": body})
