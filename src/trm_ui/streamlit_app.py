"""Streamlit interface for the TRM calculation engine.

Run with:  streamlit run src/trm_ui/streamlit_app.py

Presentation only: inputs come from ``trm_engine.input_variables``, results and
validation from ``trm_engine.calculate``. No TRM formulas, values, defaults or
input rules are defined here.
"""

from __future__ import annotations

import logging
from typing import Any

import streamlit as st

from trm_engine import (
    ApplicationNotImplementedError,
    CalculationResult,
    InputValidationError,
    OutputExplanation,
    calculate,
    default_registry,
    explain,
    input_variables,
)
from trm_engine.models import Measure
from trm_ui import presentation as p

logger = logging.getLogger(__name__)

RESULT_KEY = "last_result"  # last successful calculation
FAILURE_KEY = "last_failure"  # last failed calculation


def render_field(field: p.FormField, key: str) -> Any:
    if field.kind == "choice":
        names = dict(field.options)
        return st.selectbox(
            field.label,
            options=list(names),
            index=None,
            format_func=names.get,
            placeholder="Select…",
            help=field.help or None,
            key=key,
        )
    return st.number_input(
        field.label,
        value=None,
        placeholder=field.placeholder or ("Required" if field.required else None),
        help=field.help or None,
        key=key,
    )


def render_form(fields: list[p.FormField], key_prefix: str) -> dict[str, Any]:
    raw: dict[str, Any] = {}
    for title, group in p.group_fields(fields):
        st.markdown(f"**{title}**")
        columns = st.columns(2)
        for i, field in enumerate(group):
            with columns[i % 2]:
                raw[field.id] = render_field(field, key=f"{key_prefix}:{field.id}")
    return raw


def render_explanation(explanation: OutputExplanation, measure: Measure) -> None:
    st.markdown(f"**Result:** {p.format_precise(explanation.value)} {explanation.unit}")

    st.markdown("**Documented equation**")
    st.code(explanation.documented_equation, language=None, wrap_lines=True)
    st.caption(explanation.equation_note)
    note = p.shared_calculation_note(explanation, measure)
    if note:
        st.caption(note)
    if explanation.equation_as_printed:
        st.markdown("**Equation as printed in the TRM**")
        st.code(explanation.equation_as_printed, language=None, wrap_lines=True)
    if explanation.interpretation:
        st.info(f"**Implementation interpretation:** {explanation.interpretation}")

    formulas = p.derived_formulas(explanation)
    if formulas:
        st.markdown("**Derived values** (documented formulas)")
        st.code("\n".join(formulas), language=None, wrap_lines=True)

    st.markdown("**Values used**")
    st.dataframe(p.explanation_rows(explanation), hide_index=True)
    if explanation.all_issues:
        st.markdown(
            "**Validation issues:** "
            + " · ".join(f"[{issue_id}]({url})" for issue_id, url in p.issue_links(explanation.all_issues))
        )


def render_result(result: CalculationResult, measure: Measure, *, previous: bool) -> None:
    st.subheader("Previous result" if previous else "Savings")
    metrics = p.output_metrics(result)
    for start in range(0, len(metrics), 2):
        columns = st.columns(2)
        for column, metric in zip(columns, metrics[start : start + 2]):
            column.metric(metric["label"], metric["value"], help=metric["help"], border=True)

    for note in p.interpretation_notes(result):
        st.caption(f"† {note['interpretation']} (Issues: {note['issues']})")
    for row in p.not_applicable_rows(result, measure):
        st.caption(f"Not applicable: {row['Outputs']} — {row['Reason']}.")
    for w in p.warning_items(result):
        checked = f" Checked: {w['checked']}." if w["checked"] else ""
        st.warning(f"**{w['code']}**: {w['message']}{checked} (Issues: {w['issues']})")

    for explanation in explain(result):
        with st.expander(f"Show calculation: {explanation.name}"):
            render_explanation(explanation, measure)

    with st.expander("Output details"):
        st.dataframe(p.output_rows(result), hide_index=True)
    with st.expander("Where every value came from"):
        st.dataframe(p.provenance_rows(result), hide_index=True)


def render_issues(issue_ids: list[str]) -> None:
    with st.expander(f"Related validation issues ({len(issue_ids)})"):
        st.markdown(
            "These are open questions about how the TRM should be applied to this measure. "
            f"Each is described, with its review status, in the [validation register]({p.VALIDATION_REGISTER_URL})."
        )
        st.markdown(" · ".join(f"[{issue_id}]({url})" for issue_id, url in p.issue_links(issue_ids)))


def run_calculation(measure_id: str, application_id: str, inputs: dict[str, Any], fields: list[p.FormField]) -> None:
    """Calculate and store the outcome in session state for this and later reruns."""
    attempt = {"measure_id": measure_id, "application": application_id, "inputs": inputs}
    try:
        result = calculate(measure_id, application_id, inputs)
    except InputValidationError as exc:
        messages = p.validation_messages(exc.details, fields)
    except ApplicationNotImplementedError:
        messages = [p.NOT_AVAILABLE_MESSAGE]
    except Exception:
        logger.exception("Calculation failed for %s / %s", measure_id, application_id)
        messages = [p.UNEXPECTED_ERROR_MESSAGE]
    else:
        st.session_state[RESULT_KEY] = {**attempt, "result": result}
        st.session_state.pop(FAILURE_KEY, None)
        return
    st.session_state[FAILURE_KEY] = {**attempt, "messages": messages}


def main() -> None:
    st.set_page_config(page_title="Delaware TRM Calculator", layout="centered")
    st.title("Delaware TRM Calculator")

    registry = default_registry()
    names = {e.id: e.name for e in registry.entries()}
    measure_column, application_column = st.columns(2)
    measure_id = measure_column.selectbox("Measure", list(names), format_func=names.get, key="measure")
    measure = registry.get(measure_id)

    options = p.application_options(measure)
    app_names = {app_id: name for app_id, name, _ in options}
    application_id = application_column.selectbox(
        "Application",
        [app_id for app_id, _, implemented in options if implemented],
        format_func=app_names.get,
        key=f"application:{measure_id}",
    )
    not_implemented = [name for _, name, implemented in options if not implemented]
    if not_implemented:
        st.caption("Not implemented yet: " + ", ".join(not_implemented))

    application = measure.application(application_id)
    header = p.measure_header(measure, application)
    st.caption(
        f"{header.trm} · measure code {header.measure_code} · "
        f"[source document]({header.source_url}) {header.pages}"
    )
    notice = p.status_notice(header)
    if notice:
        st.warning(notice, icon="⚠️")

    fields = p.form_fields(input_variables(measure_id, application_id))
    inputs = p.collect_inputs(render_form(fields, key_prefix=f"{measure_id}:{application_id}"))

    if st.button("Calculate", type="primary", key="calculate"):
        run_calculation(measure_id, application_id, inputs, fields)

    failure = p.current_failure(st.session_state.get(FAILURE_KEY), measure_id, application_id, inputs)
    if failure:
        st.error("**Could not calculate.**\n\n" + "\n".join(f"- {m}" for m in failure))

    stored = st.session_state.get(RESULT_KEY)
    status = p.result_status(stored, st.session_state.get(FAILURE_KEY), measure_id, application_id, inputs)
    if status == "current":
        render_result(stored["result"], measure, previous=False)
    elif status == "previous":
        st.info(
            "The values below are from an earlier calculation. "
            "They do not correspond to the inputs you just submitted."
        )
        render_result(stored["result"], measure, previous=True)
    elif status == "stale":
        st.info("Inputs changed since the last calculation. Press **Calculate** to update the results.")

    result = stored["result"] if status == "current" else None
    render_issues(p.related_issue_ids(measure, application_id, result))
    st.caption(f"Found a problem? [Report a bug]({p.bug_report_url(measure, application)})")


if __name__ == "__main__":
    main()
