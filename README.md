# Delaware TRM Calculator

A machine-readable, source-cited, deterministic implementation of the Delaware
Technical Reference Manual (TRM), beginning with Version 5.0. See
[docs/architecture.md](docs/architecture.md) for the design.

This is the backend foundation only. It has no frontend, API, or database.

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
pip install -e '.[dev]'
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

Invalid inputs raise `trm_engine.InputValidationError`, listing each problem.
This includes unknown inputs and attempts to override deemed TRM values.

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
tests/                          Engine tests (on a synthetic TRM in tests/fixtures) and per-measure tests
docs/validation_register.md     TRM issues needing expert review
```

Equations in YAML (`equation_display`) are documentation only and are never
executed. Calculation functions are plain Python, named in YAML and looked up
in an explicit map, so the YAML can't make arbitrary code run.

## Known TRM inconsistencies

[docs/validation_register.md](docs/validation_register.md) lists every
ambiguity, conflict and implementation decision found so far (VR-001 to VR-025).
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
