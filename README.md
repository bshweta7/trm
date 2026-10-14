# Delaware TRM Calculator

A machine-readable, source-cited, deterministic implementation of the Delaware
Technical Reference Manual (TRM), beginning with Version 5.0. See
[docs/architecture.md](docs/architecture.md) for the design.

It consists of a calculation engine (`trm_engine`) and a minimal Streamlit
interface (`trm_ui`). There is no HTTP API or database yet.

## Status

| Measure | Application | Implemented | Automated tests | Human reviewed |
|---|---|---|---|---|
| Air Source Heat Pump (pp. 71–81) | Time of Sale | Yes | Yes | **No** |
| Air Source Heat Pump | Early Replacement | No (metadata only) | No | No |
| Low Flow Shower Head (pp. 174–178) | Direct Install, Time of Sale | Yes | Yes | **No** |

All values come from the **draft** Delaware TRM v5.0
([PDF](https://documents.dnrec.delaware.gov/energy/eeac/emv/meetings/2025/0408/Draft-Technical-Reference-Manual.pdf)).
No measure has been reviewed by an energy efficiency expert. Several TRM
inconsistencies affect results; see [Known TRM inconsistencies](#known-trm-inconsistencies).

## Installation

Requires Python 3.11+.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev,ui]'   # leave out ",ui" to install only the engine
pytest
```

A regular (non-editable) install bundles the YAML reference data inside the
package, so it works outside the repository:

```bash
pip install .
```

To check this, run `TRM_TEST_WHEEL=1 pytest -k wheel`. It builds a wheel,
installs it into a fresh virtual environment and calculates from outside the
repository, so it needs network access.

## Streamlit app

```bash
pip install -e '.[ui]'
streamlit run src/trm_ui/streamlit_app.py
```

Choose a measure and an implemented application at the top of the page, fill
in the form, and press **Calculate**.

- **Form:** generated from the engine's input metadata and grouped the same way
  for every measure: selections, required values, and optional values. Optional
  inputs show the TRM default as a placeholder. If you leave one empty, the
  engine uses the default and records that in the results. The form uses two
  columns on wide screens and one on narrow screens.
- **Notice:** one line says when the source TRM is a draft and when the measure
  has not been independently validated.
- **Results:** every applicable output appears as a card with its unit. A †
  marks outputs that depend on an implementation interpretation, with the note
  below. Outputs that don't apply (for example, electric savings for a gas
  water heater) are listed, and calculation warnings appear under the cards.
- **Details:** collapsed sections hold the output details (source, issues) and
  the full-precision record of where every value came from.
- **Validation issues:** a collapsed section links each related issue to the
  validation register. The app doesn't show each issue's review status;
  structured issue metadata from the engine is planned for a later PR.
- **Report a bug:** opens a GitHub issue prefilled with the measure,
  application and TRM version. Your inputs aren't included.

**When results are shown**

| Situation | What you see |
|---|---|
| Calculated with the current inputs | The results. They stay visible while you use the page. |
| Inputs edited since the last calculation | No numbers; a notice to press **Calculate** again. |
| The latest calculation failed | The error, plus the last successful result labelled **Previous result**, noting that it doesn't match the inputs you submitted. |
| Different measure or application selected | No results until you calculate. |

Invalid inputs are listed by field. Unexpected failures show a general message;
the technical details go to the server log, not the page.

Displayed values are rounded to about four significant figures. Calculations
are never rounded.

## Continuous integration

GitHub Actions ([.github/workflows/tests.yml](.github/workflows/tests.yml))
runs on every pull request into `dev` or `main` and on every push to those
branches. It has two jobs:

- **pytest:** the full test suite, with warnings treated as errors, on Ubuntu
  with Python 3.11 and 3.12. It installs the `ui` extra so the headless
  Streamlit tests run.
- **Wheel install smoke test:** builds a wheel, installs it into a fresh
  virtual environment, and loads every measure from outside the repository.
  It runs once, on Python 3.12.

A new push to a pull request cancels that pull request's earlier runs. The
workflow can only read the repository.

To run the same checks locally:

```bash
pip install -e '.[dev,ui]'
python -m pytest -W error                      # pytest job
TRM_TEST_WHEEL=1 python -m pytest -W error \
  tests/test_registry.py::test_installed_wheel_finds_reference_data   # wheel job (needs network)
```

Use an editable install (`-e`). One test checks that a source checkout reads
the repository's `trm/` data, and it fails against a regular install.

## Usage

```python
from trm_engine import calculate

result = calculate(
    "de-res-hvac-air-source-heat-pump",
    "time_of_sale",
    {
        "location": "wilmington_de",          # wilmington_de | baltimore_md | washington_dc
        "cooling_capacity_existing": 36_000,  # Btu/hr (also the baseline capacity)
        "cooling_capacity_efficient": 36_000,
        "heating_capacity_existing": 36_000,
        "heating_capacity_efficient": 36_000,
        "seer_efficient": 16,                 # SEER basis, not SEER2 (see VR-004)
        "hspf_efficient": 9,
        "eer_efficient": 13,
    },
)

for output in result.outputs.values():
    print(f"{output.name}: {output.value:.3f} {output.unit}")
# Annual cooling electric savings: 107.850 kWh/year
# Annual heating electric savings: 85.000 kWh/year
# Annual electric savings: 192.850 kWh/year
# Summer system peak demand savings: 0.109 kW
# PJM summer peak demand savings: 0.104 kW

print(result.outputs["kw_ssp_savings"].interpretation)  # implementation decision, see VR-001
```

Every resolved value records where it came from:

```python
hours = result.variables["cooling_full_load_hours"]
print(hours.value, hours.origin, hours.lookup, hours.citation.page)
# 719.0 lookup cooling_full_load_hours_by_location 74
```

`origin` is one of:

- `user_input`: supplied by the caller.
- `trm_default`: an optional input that was not supplied, so the TRM default was used.
- `deemed`: a fixed TRM assumption.
- `lookup`: taken from a TRM table.
- `derived`: calculated from other values.

The water heater fuel decides which energy outputs apply. Outputs that don't
apply are left out, not reported as zero:

```python
result = calculate(
    "de-res-water-heating-low-flow-shower-head",
    "direct_install",
    {"water_heater_fuel": "fossil_fuel", "gpm_low": 1.5},  # gpm_base defaults to 2.5
)
print(sorted(result.outputs))
# ['kwh_water_savings', 'mmbtu_savings', 'water_savings_ccf']
print(result.not_applicable[0].reason)
# applies only when water_heater_fuel = electric
```

Results can carry machine-readable `warnings`. A warning means the result is
still calculated but needs attention. Each warning has a `code`, a `message`,
the validation-register `issues` it relates to, and the input `variables` it
checked:

```python
result = calculate(
    "de-res-water-heating-low-flow-shower-head",
    "direct_install",
    {"water_heater_fuel": "electric", "gpm_base": 1.8, "gpm_low": 2.0},  # measured baseline
)
warning = result.warnings[0]
print(warning.code, warning.issues, warning.variables)
# no_positive_water_savings ['VR-020', 'VR-026'] {'gpm_base': 1.8, 'gpm_low': 2.0}
print(round(result.outputs["kwh_savings"].value, 2))  # returned unchanged
# -72.78
```

Every ASHP Time of Sale result carries `efficient_equipment_eligibility_not_verified`
(VR-008). Warnings are separate from errors, which raise exceptions and return
no result, and from the `issues` lists on outputs and variables.

Invalid inputs raise `trm_engine.InputValidationError`, listing each problem.
This includes unknown inputs and attempts to override deemed TRM values.
`exc.details` gives one `{"field": ..., "message": ...}` per problem:

```python
from trm_engine import InputValidationError

try:
    calculate("de-res-water-heating-low-flow-shower-head", "direct_install", {"gpm_low": 2.5})
except InputValidationError as exc:
    print(exc.details)
# [{'field': 'water_heater_fuel', 'message': 'Field required'},
#  {'field': 'gpm_low', 'message': 'Input should be less than or equal to 2'}]
```

To list the inputs an application accepts (for building a form or an API
schema):

```python
from trm_engine import input_variables

for v in input_variables("de-res-water-heating-low-flow-shower-head", "direct_install"):
    print(v.id, v.unit, "required" if v.required else f"default {v.default}")
# water_heater_fuel None required
# gpm_base gal/min default 2.5
# gpm_low gal/min required
# people_per_household people default 2.53
```

To browse measures:

```python
from trm_engine import default_registry

registry = default_registry()
for entry in registry.entries():
    measure = registry.get(entry.id)
    print(measure.id, [(a.id, a.status.calculation_implemented) for a in measure.applications])
```

## Layout

```text
trm/de/v5/                      Reference data (YAML): manifest + one file per measure
src/trm_engine/
  models.py                     Pydantic schema for measure YAML and manifest
  registry.py                   Loads and locates measures (no calculation logic)
  inputs.py                     Validates user inputs against YAML variable specs
  service.py                    Resolves values, runs calculations, builds results
  measures/de_v5/*.py           Deterministic calculation functions (no I/O)
  measures/__init__.py          Explicit measure id -> functions map
src/trm_ui/
  presentation.py               Turns engine objects into display data (no UI framework)
  streamlit_app.py              Streamlit page (the only module that imports Streamlit)
tests/                          Engine tests (on a synthetic TRM in tests/fixtures), per-measure tests,
                                and UI tests in tests/ui
docs/validation_register.md     TRM issues needing expert review
```

`trm_engine` holds all TRM formulas, assumptions, validation and default
handling, and imports no UI or web framework. `trm_ui` handles presentation only
and uses just the engine's public interface (`trm_engine` and
`trm_engine.models`). Tests enforce both boundaries. A future HTTP API can call
the same public functions (`calculate`, `input_variables`, `default_registry`)
without changes to the engine.

Equations in YAML (`equation_display`) are documentation only and are never
executed. Calculation functions are plain Python, named in YAML and looked up
in an explicit map, so the YAML can't make arbitrary code run.

## Known TRM inconsistencies

[docs/validation_register.md](docs/validation_register.md) lists every
ambiguity, conflict and implementation decision found so far (VR-001 to VR-026).
Each entry includes the TRM pages, the decision made, its impact and a question
for an expert. YAML definitions (`issues: [VR-…]`) and tests
(`@pytest.mark.trm_issue(...)`) link to these IDs.

The issues that most affect current results:

- **VR-001 (ASHP peak kW):** the printed equation divides by CF, but every worked
  example multiplies. The implementation multiplies. This is an interpretation,
  not a correction of the TRM.
- **VR-003 / VR-004 (ASHP baselines):** the section gives three different sets of
  baseline efficiencies, and doesn't define when SEER2 ratings replace SEER.
- **VR-015 / VR-016 (shower head examples):** the published examples leave out
  showers per person, use 101 °F instead of 105 °F, and use a gas efficiency of
  0.75 instead of 0.80. The implementation follows the defined equation and
  defaults, giving 182 kWh rather than the example's 276 kWh for a 2.0 GPM unit.
- **VR-017:** the shower head footnote refers to a deemed savings value that the
  TRM doesn't publish.

Passing tests show consistency with these decisions, not that they are correct.
