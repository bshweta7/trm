"""Streamlit interface for the TRM calculation engine.

Run with:  streamlit run src/trm_ui/streamlit_app.py

Presentation only: inputs come from ``trm_engine.input_variables``, results and
validation from ``trm_engine.calculate``. No TRM formulas, values, defaults or
input rules are defined here.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from trm_engine import (
    ApplicationNotImplementedError,
    CalculationResult,
    InputValidationError,
    calculate,
    default_registry,
    input_variables,
)
from trm_engine.models import Measure
from trm_ui import presentation as p


def render_header(header: p.MeasureHeader) -> None:
    st.subheader(header.title)
    st.caption(f"{header.trm} · measure code {header.measure_code} · source {header.pages}")
    if header.is_draft:
        st.warning(
            f"Values come from a **{header.source_status}** TRM ([source document]({header.source_url})). "
            "They may change in the final version."
        )
    if not header.human_reviewed:
        st.warning(
            "**Not reviewed by an energy efficiency expert.** Results follow the implementation's current "
            "interpretation of the TRM; see the validation issues below."
        )


def render_field(field: p.FormField, key: str) -> Any:
    label = field.label + ("" if field.required else " (optional)")
    if field.kind == "choice":
        names = dict(field.options)
        return st.selectbox(
            label,
            options=list(names),
            index=None,
            format_func=names.get,
            placeholder="Select…",
            help=field.help or None,
            key=key,
        )
    return st.number_input(
        label,
        value=None,
        placeholder=field.placeholder or ("Required" if field.required else None),
        help=field.help or None,
        key=key,
    )


def render_result(result: CalculationResult, measure: Measure) -> None:
    st.subheader("Savings")
    st.dataframe(p.output_rows(result), hide_index=True)

    for note in p.interpretation_notes(result):
        st.info(
            f"**Implementation interpretation** ({note['outputs']}): {note['interpretation']}\n\n"
            f"Implemented equation: `{note['equation'].strip()}`\n\nIssues: {note['issues']}"
        )

    for row in p.not_applicable_rows(result, measure):
        st.caption(f"Not applicable: {row['Outputs']} — {row['Reason']}.")

    for w in p.warning_items(result):
        checked = f"\n\nChecked: {w['checked']}" if w["checked"] else ""
        st.warning(f"**Warning `{w['code']}`:** {w['message']}{checked}\n\nIssues: {w['issues']}")

    with st.expander("Where every value came from"):
        st.dataframe(p.provenance_rows(result), hide_index=True)


def render_issues(issue_ids: list[str]) -> None:
    st.subheader("Validation issues")
    st.markdown(
        "Open questions about the TRM that affect this measure. Their review status is recorded in the "
        f"[validation register]({p.VALIDATION_REGISTER_URL})."
    )
    st.markdown("\n".join(f"- [{issue_id}]({url})" for issue_id, url in p.issue_links(issue_ids)))


def main() -> None:
    st.set_page_config(page_title="Delaware TRM Calculator", layout="wide")
    st.title("Delaware TRM Calculator")

    registry = default_registry()
    names = {e.id: e.name for e in registry.entries()}
    measure_id = st.sidebar.selectbox("Measure", list(names), format_func=names.get, key="measure")
    measure = registry.get(measure_id)

    options = p.application_options(measure)
    app_names = {app_id: name for app_id, name, _ in options}
    application_id = st.sidebar.selectbox(
        "Application",
        [app_id for app_id, _, implemented in options if implemented],
        format_func=app_names.get,
        key=f"application:{measure_id}",
    )
    not_implemented = [name for _, name, implemented in options if not implemented]
    if not_implemented:
        st.sidebar.caption("Not implemented yet: " + ", ".join(not_implemented))

    render_header(p.measure_header(measure, measure.application(application_id)))

    fields = p.form_fields(input_variables(measure_id, application_id))
    with st.form(f"inputs:{measure_id}:{application_id}"):
        raw = {f.id: render_field(f, key=f"{measure_id}:{application_id}:{f.id}") for f in fields}
        submitted = st.form_submit_button("Calculate")

    result = None
    if submitted:
        try:
            result = calculate(measure_id, application_id, p.collect_inputs(raw))
        except InputValidationError as exc:
            labels = {f.id: f.label for f in fields}
            st.error(
                "Some inputs are not valid:\n\n"
                + "\n".join(f"- **{labels.get(d['field'], d['field'])}**: {d['message']}" for d in exc.details)
            )
        except ApplicationNotImplementedError as exc:
            st.error(f"This application is not implemented: {exc}")
        except Exception as exc:  # noqa: BLE001 - show a message instead of a traceback
            st.error(f"The calculation could not be completed: {exc}")

    if result is not None:
        render_result(result, measure)

    render_issues(p.related_issue_ids(measure, application_id, result))


if __name__ == "__main__":
    main()
