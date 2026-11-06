# Batch Calculation MVP — Proposal

**Status:** proposed, not started. Nothing in this document is implemented.

The goal is to make the calculation engine, not the Streamlit UI, the primary
product. A user hands the engine many installed measures, possibly of
different types, and gets one deterministic, source-cited result per row. The
batch layer is a thin loop around the existing `calculate()`: it adds no
formulas, defaults, or TRM values, and it needs no web server or database.

## 1. What exists today

| Piece | Where | Relevant behaviour |
|---|---|---|
| `calculate(measure_id, application, inputs)` | `trm_engine/service.py` | One measure, one application. Returns `CalculationResult` with outputs (value, unit, equation, citation, interpretation, issues), warnings, not-applicable outputs, every resolved variable with its origin and citation, TRM version and source document. |
| `input_variables(measure_id, application)` | same | YAML metadata for every user input: type, unit, required, default, bounds, choices. |
| Input validation | `trm_engine/inputs.py` | Pydantic, generated from YAML. Strict: numbers must be numbers (`"2.0"` is rejected), unknown fields are rejected, errors are per field. |
| Registry | `trm_engine/registry.py` | Measures by standardized ID (`de-res-hvac-air-source-heat-pump`), from the manifest. |
| Errors | — | `MeasureNotFoundError` (unknown measure), `ApplicationNotImplementedError`, `InputValidationError` (with `details`). An unknown application ID raises a bare `KeyError` from `Measure.application()`. |

Two small gaps, both addressed in PR 1 below: an unknown application isn't
distinguishable from other `KeyError`s, and `MeasureNotFoundError` isn't
exported from `trm_engine`.

## 2. Design decisions

1. **Rows are identified, never inferred.** Each row names `measure_id` and
   `application` exactly as in the manifest and YAML. No matching on product
   descriptions, measure names, or which columns happen to be filled in. An
   unknown ID is a row error.
2. **One row, one `calculate()` call.** `calculate_batch()` loops over rows
   and calls `calculate()` with the same registry. Batch and single results
   for the same inputs are identical by construction, and a test asserts it.
3. **The engine stays strict; parsing is separate.** CSV cells are text.
   A CSV adapter converts them to typed values using `input_variables()`
   metadata, then hands typed inputs to `calculate_batch()`. `calculate()`
   and its validation don't change, so the future API gets the same strict
   contract.
4. **Partial success.** A bad row produces an error record for that row and
   never stops the batch. Results keep the input order.
5. **No new dependencies.** Standard-library `csv` only. No pandas.
6. **No rounding.** Values are written at full precision (`repr(float)`),
   as `calculate()` returns them. Rounding remains a presentation choice
   (VR-024).

## 3. Library API (`trm_engine/batch.py`)

```python
class BatchRow(BaseModel):
    row_id: str                      # caller's identifier, echoed in every output
    measure_id: str
    application: str
    inputs: dict[str, float | str]   # typed, as for calculate()

class RowError(BaseModel):
    code: Literal[
        "unknown_measure", "unknown_application", "application_not_implemented",
        "invalid_input", "parse_error", "internal_error",
    ]
    field: str | None                # input column, when the error is about one
    message: str

class RowOutcome(BaseModel):
    row_id: str
    measure_id: str
    application: str
    status: Literal["ok", "error"]
    result: CalculationResult | None # present exactly when status == "ok"
    errors: list[RowError]           # present exactly when status == "error"

class BatchResult(BaseModel):
    rows: list[RowOutcome]           # same order as the input
    # derived: ok_count, error_count, warning_count

def calculate_batch(rows: Iterable[BatchRow], registry: MeasureRegistry | None = None) -> BatchResult
```

Error mapping inside the loop:

| Exception from `calculate()` | Row error |
|---|---|
| `MeasureNotFoundError` | `unknown_measure` |
| `ApplicationNotFoundError` (new `KeyError` subclass, PR 1) | `unknown_application` |
| `ApplicationNotImplementedError` | `application_not_implemented` |
| `InputValidationError` | one `invalid_input` per entry in `details`, with `field` |
| anything else | `internal_error`. The exception is logged with the row ID; the message doesn't expose internals. An engine bug fails one row, not the batch. |

Warnings stay on `result.warnings`, so a row can be `ok` with warnings, for
example a showerhead with no flow reduction (VR-026).

## 4. CSV input schema

One file, one row per installed measure, measures mixed freely.

| Column | Required | Meaning |
|---|---|---|
| `row_id` | No | Caller's identifier. Default: the 1-based data row number. Must be unique. |
| `measure_id` | Yes | Manifest ID, e.g. `de-res-hvac-air-source-heat-pump` |
| `application` | Yes | Application ID, e.g. `time_of_sale` |
| *input columns* | Per measure | Named exactly as YAML variable IDs, e.g. `seer_efficient`, `gpm_low` |

Example:

```csv
row_id,measure_id,application,location,cooling_capacity_existing,cooling_capacity_efficient,heating_capacity_existing,heating_capacity_efficient,seer_efficient,hspf_efficient,eer_efficient,water_heater_fuel,gpm_base,gpm_low,people_per_household
A1,de-res-hvac-air-source-heat-pump,time_of_sale,baltimore_md,36000,36000,36000,36000,16,9,13,,,,
S1,de-res-water-heating-low-flow-shower-head,direct_install,,,,,,,,,electric,,1.5,
S2,de-res-water-heating-low-flow-shower-head,time_of_sale,,,,,,,,,fossil_fuel,2.8,1.5,4
```

Cell rules, applied per row against that row's `input_variables()`:

- **Blank cell:** the input isn't supplied. Optional inputs take the TRM
  default (recorded as `trm_default` in provenance); required inputs give
  `invalid_input`.
- **Number inputs:** parsed with `float()` after trimming whitespace. Thousands
  separators, units in the cell, `inf` and `nan` are `parse_error`.
- **Choice inputs:** the choice ID (`baltimore_md`), not the display name.
  Anything else is `invalid_input`, and the message lists the allowed IDs.
- **A filled cell in a column the row's measure doesn't use** is
  `invalid_input`, not silently ignored. A value in the wrong column is a
  likely data-entry mistake, and dropping it would hide it.
- **Unknown column headers** (not reserved and not an input of any measure)
  fail the whole file before any row is calculated. This is the only
  file-level error, together with a missing `measure_id`/`application` header
  or duplicate `row_id`s.
- UTF-8, with or without a BOM. The header row is required.

Two generated helpers make the schema discoverable without reading YAML:

- `csv_template(measure_ids)` returns a header row with every input column for
  the chosen measures.
- `input_dictionary()` returns one row per (measure, application, input):
  column, name, unit, required, TRM default, allowed values, bounds, TRM page
  and issue IDs. It is built from `input_variables()`.

## 5. CSV outputs

Mixed measures produce different outputs, so a wide output file would be mostly
empty and would change shape with every measure added. The outputs are in long
form instead: three files, all keyed by `row_id`.

**`rows.csv`**: one line per input row. This is the batch summary.

| Column | Example |
|---|---|
| `row_id`, `measure_id`, `application` | `S1`, `de-res-water-heating-low-flow-shower-head`, `direct_install` |
| `status` | `ok` / `error` |
| `measure_code` | `RS_WT_DI_SHWRHD_0519` |
| `jurisdiction`, `trm_version`, `source_status` | `DE`, `5.0`, `draft` |
| `human_reviewed` | `false` |
| `error_count`, `errors` | `0`, `""` (else `field: message; …`) |
| `warning_count`, `warnings` | `1`, `no_positive_water_savings` |

**`results.csv`**: one line per output value of an `ok` row.

| Column | Example |
|---|---|
| `row_id`, `measure_id`, `application` | |
| `output_id`, `output_name` | `kwh_savings`, `Annual electric savings` |
| `value`, `unit` | `363.9129161781945`, `kWh/year` |
| `calculation`, `equation` | `electric_savings`, the YAML `equation_display` |
| `trm_version`, `source_status`, `source_pages` | `5.0`, `draft`, `174–176` |
| `interpretation` | set for ASHP peak kW (VR-001) |
| `issues` | `VR-015;VR-022` |

Outputs that don't apply to a row (e.g. kWh for a fossil-fuel water heater)
have no line in `results.csv`. `rows.csv` records them under
`not_applicable`, so a missing output is never mistaken for zero.

**`provenance.csv`**: one line per resolved variable of an `ok` row: `row_id`,
`variable_id`, `symbol`, `name`, `value`, `unit`, `origin` (`user_input`,
`trm_default`, `deemed`, `lookup`, `derived`), `citation_pages`, `lookup`,
`issues`. This is where a reviewer sees that `gpm_base` came from the TRM default
on p. 174 rather than from the user.

The same `BatchResult` can also be written as JSON (`model_dump_json()`)
for programmatic users who want the full nested structure.

## 6. Single and batch, without Streamlit

```
trm_engine/                 (no UI or web imports, as today; tests enforce it)
  service.py    calculate(), input_variables()        ← unchanged
  batch.py      calculate_batch(), BatchRow/RowOutcome/BatchResult
  csv_io.py     read_batch_csv(), write_*_csv(), csv_template(), input_dictionary()
  __main__.py   python -m trm_engine batch input.csv --out results/
```

- `calculate()` stays the single-calculation entry point. `calculate_batch()`
  is a loop over it, so there is one code path for formulas.
- `csv_io` depends on `batch` and `service`; neither depends on `csv_io`.
- The command-line entry is a convenience over the library (argparse, stdlib).
  It writes the three CSVs and exits non-zero only on file-level errors, not
  on row errors.
- `tests/test_engine_independence.py` already forbids UI and web imports in
  `trm_engine`; the new modules fall under it automatically.

## 7. Streamlit, later

A separate **Batch (CSV)** page, using `st.navigation`, so the single-measure
page is unchanged:

1. Download a template (`csv_template`) and the input dictionary.
2. Upload a CSV (`st.file_uploader`). Bytes go to `read_batch_csv` and then
   `calculate_batch`. No parsing or validation in the UI.
3. Show the counts (ok / error / with warnings), then `rows.csv` as a table
   with errors and warnings visible, then `results.csv`.
4. Offer download buttons for the three CSVs (or a zip).
5. Show the same draft/unreviewed notice as the single page, once.

Expected size: about 80 lines in `trm_ui`, plus `AppTest` tests.

## 8. FastAPI, later

A separate `trm_api` package that imports only `trm_engine`'s public interface,
with a boundary test like the existing UI one:

| Endpoint | Engine call |
|---|---|
| `GET /measures` | `default_registry().entries()` |
| `GET /measures/{id}/applications/{app}/inputs` | `input_variables()` |
| `POST /calculate` (JSON: measure_id, application, inputs) | `calculate()` → `CalculationResult` JSON |
| `POST /calculate/batch` (JSON: list of `BatchRow`) | `calculate_batch()` → `BatchResult` JSON |
| `POST /calculate/batch.csv` (multipart CSV) | `read_batch_csv()` + `calculate_batch()` → zip of the three CSVs |

The Pydantic models already exist, so request and response schemas come for
free. HTTP status: 200 for a processed batch, even with row errors; 400 for
file-level errors; 422 for a malformed single request. Synchronous only, with
a row limit (e.g. 10,000). Background jobs aren't needed at this size.

## 9. Testing

- `calculate_batch` result for each row equals `calculate()` for the same
  inputs (property test over all validation-matrix cases).
- End-to-end: one mixed CSV built from the validation matrix (A-I1, A-I3,
  A-L1, S-I1–S-I3, S-Z2). Every value in `results.csv` must match
  `tests/validation/trm_reference.py`.
- One test per row-error code, and per file-level error.
- Partial success: a file with good and bad rows returns all good results,
  in order.
- CSV round-trip: written values parse back to the identical floats.
- Determinism: the same file gives byte-identical output files.

## 10. Complexity and PR sequence

Overall: **small to medium.** About 500–700 lines of code plus tests, and no
change to formulas or YAML. The open decisions are in the CSV cell rules
(§4), which PR 3 settles.

| PR | Scope | Size | Depends on |
|---|---|---|---|
| 1 | `ApplicationNotFoundError` (a `KeyError` subclass, so existing callers are unaffected); export it and `MeasureNotFoundError` | XS | — |
| 2 | `batch.py`: models and `calculate_batch()`, error mapping, partial success, equality-with-`calculate()` tests | S | 1 |
| 3 | `csv_io.read_batch_csv()`: cell rules, file-level errors, `csv_template()`, `input_dictionary()` | M | 2 |
| 4 | CSV writers (`rows`, `results`, `provenance`), JSON export, end-to-end validation-matrix CSV test | S | 3 |
| 5 | `python -m trm_engine batch` and README/architecture docs with an example CSV in `docs/examples/` | S | 4 |
| 6 | Streamlit Batch page (§7) | S–M | 4 |
| 7 | FastAPI (§8), only when there's an external consumer | M | 4 |

PRs 1–5 deliver the local library MVP. PR 6 is optional for Jen's review.
PR 7 waits for a real need, as the architecture document already says
(Phase 9).

## 11. Out of scope

Databases, user accounts, saved projects, job queues, new measures, and any
change to calculation logic or TRM values. Expert decisions from the
validation register flow into the YAML and functions as before. Batch picks
them up automatically.
