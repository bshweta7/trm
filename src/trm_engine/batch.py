"""Calculate many installed measures in one call.

A thin loop over ``calculate()``: every row is validated and calculated
independently, by its standardized measure ID and application, with the same
code path as a single calculation. No formulas, defaults or TRM values live
here. A row that fails produces structured errors for that row only; the other
rows are still calculated. See docs/batch_plan.md.
"""

from __future__ import annotations

import logging
from collections import Counter
from collections.abc import Iterable, Mapping
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, computed_field, field_validator

from trm_engine.inputs import InputValidationError
from trm_engine.models import ApplicationNotFoundError
from trm_engine.registry import MeasureNotFoundError, MeasureRegistry, default_registry
from trm_engine.service import ApplicationNotImplementedError, CalculationResult, calculate

logger = logging.getLogger(__name__)


class BatchRow(BaseModel):
    """One installed measure: which calculation to run, and its inputs.

    ``inputs`` are typed as for ``calculate()``; they are validated against the
    measure's YAML when the row is calculated. Without a ``row_id``, the row is
    identified by its 1-based position in the batch.
    """

    model_config = ConfigDict(extra="forbid")

    row_id: str | None = Field(default=None, min_length=1)
    measure_id: str
    application: str
    inputs: dict[str, Any] = Field(default_factory=dict)

    @field_validator("row_id", mode="before")
    @classmethod
    def _integer_ids_as_text(cls, value: Any) -> Any:
        # Row IDs are labels; accept integers (e.g. from JSON) but compare as text.
        if isinstance(value, int) and not isinstance(value, bool):
            return str(value)
        return value


class RowErrorCode(StrEnum):
    INVALID_ROW = "invalid_row"  # the row itself is malformed (missing measure_id, …)
    DUPLICATE_ROW_ID = "duplicate_row_id"
    UNKNOWN_MEASURE = "unknown_measure"
    UNKNOWN_APPLICATION = "unknown_application"
    APPLICATION_NOT_IMPLEMENTED = "application_not_implemented"
    INVALID_INPUT = "invalid_input"  # an input failed the measure's validation
    INTERNAL_ERROR = "internal_error"  # unexpected failure; logged with the row ID


class RowError(BaseModel):
    code: RowErrorCode
    field: str | None  # the row field or input the error is about, if any
    message: str


class RowOutcome(BaseModel):
    """The result or the errors for one row; exactly one of the two is present."""

    row_id: str
    measure_id: str | None
    application: str | None
    status: Literal["ok", "error"]
    result: CalculationResult | None
    errors: list[RowError]


class BatchResult(BaseModel):
    rows: list[RowOutcome]  # in input order

    @computed_field
    @property
    def ok_count(self) -> int:
        return sum(r.status == "ok" for r in self.rows)

    @computed_field
    @property
    def error_count(self) -> int:
        return sum(r.status == "error" for r in self.rows)

    @computed_field
    @property
    def warning_count(self) -> int:
        """Rows that calculated but carry at least one warning."""
        return sum(bool(r.result and r.result.warnings) for r in self.rows)


def calculate_batch(
    rows: Iterable[BatchRow | Mapping[str, Any]],
    registry: MeasureRegistry | None = None,
) -> BatchResult:
    """Calculate every row independently and return one outcome per row, in order.

    Rows may mix measures and applications. Each row's result is identical to
    ``calculate()`` for the same measure, application and inputs. Row IDs must
    be unique: every row that shares an ID gets a ``duplicate_row_id`` error and
    gets no result, because its results could not be told apart; its other
    errors, if any, are still reported.
    """
    registry = registry or default_registry()
    parsed = [_parse(row, position) for position, row in enumerate(rows, start=1)]
    counts = Counter(row_id for row_id, _, _ in parsed)

    outcomes = []
    for row_id, row, errors in parsed:
        result = None
        if row is not None:
            # Still calculated when its ID is duplicated, so that every problem
            # with the row is reported in one pass; the result is then dropped.
            result, errors = _calculate(row_id, row, registry)
        if counts[row_id] > 1:
            result = None
            errors = errors + [
                RowError(
                    code=RowErrorCode.DUPLICATE_ROW_ID,
                    field="row_id",
                    message=f"row_id {row_id!r} is used by {counts[row_id]} rows",
                )
            ]
        outcomes.append(
            RowOutcome(
                row_id=row_id,
                measure_id=row.measure_id if row else None,
                application=row.application if row else None,
                status="ok" if result is not None else "error",
                result=result,
                errors=errors,
            )
        )
    return BatchResult(rows=outcomes)


def _parse(row: Any, position: int) -> tuple[str, BatchRow | None, list[RowError]]:
    """Validate the row's shape. Returns its ID, the row (if valid) and any errors."""
    default_id = str(position)
    if isinstance(row, BatchRow):
        return row.row_id or default_id, row, []
    if not isinstance(row, Mapping):
        message = f"expected a mapping with measure_id, application and inputs, got {type(row).__name__}"
        return default_id, None, [RowError(code=RowErrorCode.INVALID_ROW, field=None, message=message)]
    try:
        parsed = BatchRow.model_validate(dict(row))
    except ValidationError as exc:
        errors = [
            RowError(
                code=RowErrorCode.INVALID_ROW,
                field=".".join(map(str, e["loc"])) or None,
                message=e["msg"],
            )
            for e in exc.errors()
        ]
        row_id = row.get("row_id")
        usable_id = isinstance(row_id, (str, int)) and not isinstance(row_id, bool) and str(row_id) != ""
        return str(row_id) if usable_id else default_id, None, errors
    return parsed.row_id or default_id, parsed, []


def _calculate(
    row_id: str, row: BatchRow, registry: MeasureRegistry
) -> tuple[CalculationResult | None, list[RowError]]:
    def error(code: RowErrorCode, message: str, field: str | None = None):
        return None, [RowError(code=code, field=field, message=message)]

    try:
        return calculate(row.measure_id, row.application, row.inputs, registry=registry), []
    except MeasureNotFoundError:
        return error(RowErrorCode.UNKNOWN_MEASURE, f"unknown measure_id {row.measure_id!r}", "measure_id")
    except ApplicationNotFoundError:
        return error(
            RowErrorCode.UNKNOWN_APPLICATION,
            f"{row.measure_id} has no application {row.application!r}",
            "application",
        )
    except ApplicationNotImplementedError:
        return error(
            RowErrorCode.APPLICATION_NOT_IMPLEMENTED,
            f"{row.measure_id}: application {row.application!r} is not implemented",
            "application",
        )
    except InputValidationError as exc:
        return None, [
            RowError(
                code=RowErrorCode.INVALID_INPUT,
                field=None if d["field"] == "<root>" else d["field"],
                message=d["message"],
            )
            for d in exc.details
        ]
    except Exception:
        # An engine bug must not lose the rest of the batch. The details go to the
        # log; the row reports that it failed without exposing internals.
        logger.exception("batch row %r (%s / %s) failed", row_id, row.measure_id, row.application)
        return error(RowErrorCode.INTERNAL_ERROR, "unexpected error while calculating this row; see the log")
