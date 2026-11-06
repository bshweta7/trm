"""calculate_batch(): mixed measures, per-row validation, partial success, reproducibility.

The batch layer adds no calculations, so expected results are "whatever
calculate() returns for the same row". Independently derived values for batch
rows are checked in tests/validation/test_batch_reference.py.
"""

import logging

import pytest

from trm_engine import BatchRow, RowErrorCode, calculate, calculate_batch
from trm_engine.measures import IMPLEMENTATIONS

ASHP = "de-res-hvac-air-source-heat-pump"
SHOWER = "de-res-water-heating-low-flow-shower-head"
ASHP_INPUTS = dict(
    location="baltimore_md",
    cooling_capacity_existing=36_000,
    cooling_capacity_efficient=36_000,
    heating_capacity_existing=36_000,
    heating_capacity_efficient=36_000,
    seer_efficient=16,
    hspf_efficient=9,
    eer_efficient=13,
)

MIXED = [
    {"row_id": "A1", "measure_id": ASHP, "application": "time_of_sale", "inputs": ASHP_INPUTS},
    {"row_id": "S1", "measure_id": SHOWER, "application": "direct_install",
     "inputs": {"water_heater_fuel": "electric", "gpm_low": 1.5}},
    {"row_id": "S2", "measure_id": SHOWER, "application": "time_of_sale",
     "inputs": {"water_heater_fuel": "fossil_fuel", "gpm_base": 2.8, "gpm_low": 1.5, "people_per_household": 4}},
]


def by_id(batch):
    return {r.row_id: r for r in batch.rows}


def codes(outcome):
    return [(e.code, e.field) for e in outcome.errors]


def good(row_id="OK"):
    return {"row_id": row_id, "measure_id": SHOWER, "application": "direct_install",
            "inputs": {"water_heater_fuel": "electric", "gpm_low": 2.0}}


# --- Mixed measures -------------------------------------------------------------


def test_mixed_measures_and_applications_all_calculate_in_input_order():
    batch = calculate_batch(MIXED)
    assert [r.row_id for r in batch.rows] == ["A1", "S1", "S2"]
    assert [(r.measure_id, r.application, r.status) for r in batch.rows] == [
        (ASHP, "time_of_sale", "ok"),
        (SHOWER, "direct_install", "ok"),
        (SHOWER, "time_of_sale", "ok"),
    ]
    assert (batch.ok_count, batch.error_count, batch.warning_count) == (3, 0, 1)  # ASHP eligibility warning
    assert all(r.errors == [] for r in batch.rows)


@pytest.mark.parametrize("row", MIXED, ids=lambda r: r["row_id"])
def test_each_row_equals_a_single_calculation(row):
    """No second code path: the batch result is calculate()'s result, unchanged."""
    [outcome] = calculate_batch([row]).rows
    assert outcome.result == calculate(row["measure_id"], row["application"], row["inputs"])


def test_fuel_specific_outputs_follow_each_rows_inputs():
    rows = by_id(calculate_batch(MIXED))
    assert "kwh_savings" in rows["S1"].result.outputs and "mmbtu_savings" not in rows["S1"].result.outputs
    assert "mmbtu_savings" in rows["S2"].result.outputs and "kwh_savings" not in rows["S2"].result.outputs
    assert [n.outputs for n in rows["S2"].result.not_applicable] == [["kwh_savings", "kw_savings"]]


@pytest.mark.trm_issue("VR-001", "VR-025")
def test_results_keep_citations_versions_interpretations_and_issues():
    rows = by_id(calculate_batch(MIXED))
    ashp = rows["A1"].result
    assert (ashp.trm_version, ashp.source_document.status, ashp.measure_code) == ("5.0", "draft", "RS_HV_TOS_ASHP_0518")
    kw = ashp.outputs["kw_ssp_savings"]
    assert kw.unit == "kW" and kw.source.pages == [78, 79, 80]
    assert kw.interpretation and "VR-001" in kw.issues
    assert ashp.variables["cooling_full_load_hours"].lookup == "cooling_full_load_hours_by_location"
    shower = rows["S1"].result
    assert shower.variables["gpm_base"].origin == "trm_default"
    assert shower.variables["gpm_base"].citation.page == 174


@pytest.mark.trm_issue("VR-020", "VR-026")
def test_row_warnings_are_kept_and_do_not_make_the_row_fail():
    row = good() | {"inputs": {"water_heater_fuel": "electric", "gpm_base": 1.8, "gpm_low": 2.0}}
    batch = calculate_batch([row])
    [outcome] = batch.rows
    assert outcome.status == "ok"
    assert [w.code for w in outcome.result.warnings] == ["no_positive_water_savings"]
    assert batch.warning_count == 1


# --- Invalid rows never stop the batch ---------------------------------------------


@pytest.mark.parametrize(
    "inputs, expected",
    [
        pytest.param({"water_heater_fuel": "electric", "gpm_low": 2.5}, [("invalid_input", "gpm_low")], id="above-maximum"),
        pytest.param({"water_heater_fuel": "electric", "gpm_low": "2.0"}, [("invalid_input", "gpm_low")], id="text-number"),
        pytest.param({"water_heater_fuel": "solar", "gpm_low": 2.0}, [("invalid_input", "water_heater_fuel")], id="bad-choice"),
        pytest.param({"water_heater_fuel": "electric"}, [("invalid_input", "gpm_low")], id="missing-required-input"),
        pytest.param({"water_heater_fuel": "electric", "gpm_low": 2.0, "seer_efficient": 16},
                     [("invalid_input", "seer_efficient")], id="input-of-another-measure"),
        pytest.param({}, [("invalid_input", "water_heater_fuel"), ("invalid_input", "gpm_low")], id="no-inputs"),
    ],
)
def test_invalid_inputs_fail_only_their_row(inputs, expected):
    bad = good("BAD") | {"inputs": inputs}
    rows = by_id(calculate_batch([good("BEFORE"), bad, good("AFTER")]))
    assert codes(rows["BAD"]) == expected
    assert rows["BAD"].status == "error" and rows["BAD"].result is None
    assert all(e.message for e in rows["BAD"].errors)
    assert rows["BEFORE"].status == rows["AFTER"].status == "ok"


@pytest.mark.parametrize(
    "row, expected",
    [
        pytest.param({"row_id": "R", "application": "direct_install"}, [("invalid_row", "measure_id")], id="no-measure-id"),
        pytest.param({"row_id": "R", "measure_id": SHOWER}, [("invalid_row", "application")], id="no-application"),
        pytest.param({"row_id": "R"}, [("invalid_row", "measure_id"), ("invalid_row", "application")], id="neither"),
        pytest.param({"row_id": "R", "measure_id": SHOWER, "application": "direct_install", "input": {}},
                     [("invalid_row", "input")], id="misspelled-key"),
        pytest.param({"row_id": "R", "measure_id": SHOWER, "application": "direct_install", "inputs": [1]},
                     [("invalid_row", "inputs")], id="inputs-not-a-mapping"),
        pytest.param({"row_id": "R", "measure_id": "de-res-unknown", "application": "x"},
                     [("unknown_measure", "measure_id")], id="unknown-measure"),
        pytest.param({"row_id": "R", "measure_id": SHOWER, "application": "retrofit"},
                     [("unknown_application", "application")], id="unknown-application"),
        pytest.param({"row_id": "R", "measure_id": ASHP, "application": "early_replacement", "inputs": ASHP_INPUTS},
                     [("application_not_implemented", "application")], id="not-implemented"),
    ],
)
def test_malformed_or_unknown_rows_fail_only_their_row(row, expected):
    rows = by_id(calculate_batch([row, good()]))
    assert codes(rows["R"]) == expected
    assert rows["R"].status == "error"
    assert rows["OK"].status == "ok"


def test_row_that_is_not_a_mapping():
    batch = calculate_batch(["not a row", good()])
    assert [r.row_id for r in batch.rows] == ["1", "OK"]
    assert codes(batch.rows[0]) == [("invalid_row", None)]
    assert (batch.rows[0].measure_id, batch.rows[0].application) == (None, None)


def test_measure_and_application_are_echoed_on_error_rows():
    [outcome] = calculate_batch([good("BAD") | {"inputs": {}}]).rows
    assert (outcome.measure_id, outcome.application) == (SHOWER, "direct_install")


def test_unexpected_engine_failure_is_isolated_and_logged(monkeypatch, caplog):
    def broken(**_):
        raise ZeroDivisionError("boom")

    monkeypatch.setitem(IMPLEMENTATIONS[ASHP], "time_of_sale_energy_savings", broken)
    with caplog.at_level(logging.ERROR, logger="trm_engine.batch"):
        rows = by_id(calculate_batch(MIXED))
    assert codes(rows["A1"]) == [("internal_error", None)]
    assert "boom" not in rows["A1"].errors[0].message  # internals stay in the log
    assert "'A1'" in caplog.text and "ZeroDivisionError" in caplog.text
    assert rows["S1"].status == rows["S2"].status == "ok"


# --- Row identifiers ------------------------------------------------------------------


def test_duplicate_row_ids_fail_every_row_that_shares_them():
    rows = [good("X"), good("Y"), good("X")]
    batch = calculate_batch(rows)
    assert [(r.row_id, r.status) for r in batch.rows] == [("X", "error"), ("Y", "ok"), ("X", "error")]
    for outcome in (batch.rows[0], batch.rows[2]):
        assert codes(outcome) == [("duplicate_row_id", "row_id")]
        assert outcome.errors[0].message == "row_id 'X' is used by 2 rows"


def test_duplicate_id_is_reported_alongside_other_row_errors():
    batch = calculate_batch([good("X") | {"inputs": {}}, good("X")])
    assert [c for c, _ in codes(batch.rows[0])] == ["invalid_input", "invalid_input", "duplicate_row_id"]
    assert codes(batch.rows[1]) == [("duplicate_row_id", "row_id")]


def test_missing_row_ids_default_to_position_and_can_collide():
    unnamed = {k: v for k, v in good().items() if k != "row_id"}
    batch = calculate_batch([unnamed, unnamed, good("2")])
    assert [r.row_id for r in batch.rows] == ["1", "2", "2"]
    assert [r.status for r in batch.rows] == ["ok", "error", "error"]


@pytest.mark.parametrize("row_id, expected", [(7, "7"), ("007", "007")])
def test_row_ids_are_text(row_id, expected):
    [outcome] = calculate_batch([good() | {"row_id": row_id}]).rows
    assert outcome.row_id == expected and outcome.status == "ok"


@pytest.mark.parametrize("row_id", ["", True, 1.5, None])
def test_unusable_row_ids(row_id):
    [outcome] = calculate_batch([good() | {"row_id": row_id}]).rows
    if row_id is None:  # explicitly absent: positional default
        assert (outcome.row_id, outcome.status) == ("1", "ok")
    else:
        assert outcome.row_id == "1" and codes(outcome) == [("invalid_row", "row_id")]


# --- Inputs, outputs and reproducibility ---------------------------------------------


def test_accepts_batch_rows_dicts_and_generators():
    rows = (BatchRow(**MIXED[0]) if i == 0 else row for i, row in enumerate(MIXED))
    assert calculate_batch(rows).ok_count == 3


def test_empty_batch():
    batch = calculate_batch([])
    assert (batch.rows, batch.ok_count, batch.error_count, batch.warning_count) == ([], 0, 0, 0)


def test_counts_are_serialized():
    data = calculate_batch([good("A"), good("B") | {"inputs": {}}]).model_dump()
    assert (data["ok_count"], data["error_count"], data["warning_count"]) == (1, 1, 0)


def test_identical_batches_give_byte_identical_json():
    rows = MIXED + [good("BAD") | {"inputs": {}}, good("A1")]
    assert calculate_batch(rows).model_dump_json() == calculate_batch(rows).model_dump_json()


def test_a_rows_result_does_not_depend_on_its_neighbours_or_position():
    forward = by_id(calculate_batch(MIXED))
    backward = by_id(calculate_batch(list(reversed(MIXED)) + [good("BAD") | {"inputs": {}}]))
    for row_id in ("A1", "S1", "S2"):
        assert forward[row_id] == backward[row_id]


def test_inputs_are_not_mutated():
    rows = [good("A") | {"inputs": {"water_heater_fuel": "electric", "gpm_low": 2.0}}]
    snapshot = repr(rows)
    calculate_batch(rows)
    assert repr(rows) == snapshot


def test_an_error_code_exists_for_every_failure_the_batch_reports():
    assert {c.value for c in RowErrorCode} == {
        "invalid_row", "duplicate_row_id", "unknown_measure", "unknown_application",
        "application_not_implemented", "invalid_input", "internal_error",
    }
