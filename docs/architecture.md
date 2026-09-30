# Delaware TRM Calculator

## Project Overview

The Delaware TRM Calculator is a machine-readable implementation of the Delaware Technical Reference Manual (TRM), beginning with Version 5.

The initial goal is to create a free public calculator that makes TRM calculations easier to access, understand, and reproduce.

The underlying architecture should eventually support:

- Interactive web calculations
- Batch calculations
- API access
- Multiple TRM versions
- Additional states/jurisdictions
- Automated TRM updates
- Calculation validation and testing
- Integration with external energy-program systems

The Streamlit application is only one interface. The primary asset is the underlying **structured TRM dataset and deterministic calculation engine**.

---

# 1. Design Principles

## 1.1 Separate Data From Calculation Logic

The system should distinguish between:

### Reference Data
Information defined by the TRM, including:

- Measure names
- Market sectors
- End-use categories
- Descriptions
- Effective dates
- Measure codes
- Deemed assumptions
- Lookup tables
- Units
- Source pages
- References

This information should primarily live in YAML.

### Calculation Logic
Executable implementations of TRM equations and conditional logic.

This should live in Python.

### Application Data
Future information generated through use of the application, including:

- Users
- Organizations
- Saved calculations
- Projects
- API usage
- Calculation history

This can eventually live in a database such as PostgreSQL.

Application data is separate from the authoritative TRM definitions.

---

# 2. Proposed Technology Stack

### TRM definitions
YAML

### Schema validation
Pydantic

### Calculation engine
Python

### Testing
pytest

### Initial frontend
Streamlit

### Future API
FastAPI

### Future application database
PostgreSQL

### Source/version control
Git/GitHub

A database is not required for the initial MVP.

---

# 3. Repository Structure

```text
de-trm/
│
├── trm/
│   └── de/
│       └── v5/
│           ├── manifest.yaml
│           │
│           ├── residential/
│           │   ├── hvac/
│           │   │   ├── air_source_heat_pump.yaml
│           │   │   ├── air_sealing.yaml
│           │   │   └── ...
│           │   ├── lighting/
│           │   ├── water_heating/
│           │   └── ...
│           │
│           └── commercial/
│               ├── hvac/
│               ├── lighting/
│               └── ...
│
├── engine/
│   ├── models.py
│   ├── registry.py
│   │
│   └── measures/
│       └── de_v5/
│           ├── air_source_heat_pump.py
│           ├── air_sealing.py
│           └── ...
│
├── tests/
│   └── de_v5/
│
├── app/
│   └── streamlit_app.py
│
└── pyproject.toml
```

Each TRM measure should generally have its own YAML file and corresponding Python implementation where executable logic is required.

---

# 4. Measure Identification

Every measure should receive a permanent internal identifier independent of identifiers used by the source TRM.

Example:

```yaml
id: de-res-hvac-air-source-heat-pump
```

TRM-specific identifiers should be stored separately:

```yaml
trm_identifiers:
  measure_code: "SOURCE_MEASURE_CODE"
  section: "SOURCE_SECTION"
```

This allows the internal identity of a measure to remain stable if future TRM versions rename, reorganize, or renumber it.

---

# 5. Basic Measure Structure

A measure YAML file should begin with core metadata.

```yaml
id: de-res-hvac-air-source-heat-pump

jurisdiction: DE
trm_version: "5.0"

classification:
  market_sector: residential
  category: hvac
  name: Air Source Heat Pump

effective_date: YYYY-MM-DD
end_date: null

source:
  document: Delaware Technical Reference Manual
  version: "5.0"
  page_start: 71
  page_end: 81
  section: "SOURCE_SECTION"

description: >
  Measure description from or derived from the TRM.
```

---

# 6. Classification

Measures should be organized hierarchically.

The initial hierarchy is:

```text
Jurisdiction
    ↓
TRM Version
    ↓
Market Sector
    ↓
End Use / Category
    ↓
Measure
```

Example:

```text
Delaware
└── Version 5
    └── Residential
        └── HVAC
            └── Air Source Heat Pump
```

Initial market sectors should follow the TRM's organization, such as:

- Residential
- Commercial & Industrial

Categories should similarly follow the TRM's end-use organization wherever practical.

---

# 7. Variables

Variables should be modeled as first-class objects rather than being embedded only inside equation strings.

Each variable should contain enough information for both the calculation engine and future UI generation.

Example user-provided variable:

```yaml
variables:

  - id: capacity
    symbol: CAP
    name: Rated cooling capacity
    description: Rated cooling capacity of installed equipment
    unit: Btu/hr
    type: number
    source: user_input
    required: true
```

Example TRM-defined variable:

```yaml
  - id: cooling_full_load_hours
    symbol: FLHcool
    name: Cooling full-load hours
    description: Equivalent full-load cooling hours
    unit: hours/year
    type: number
    source: lookup
    lookup: cooling_flh_by_location
```

---

# 8. Variable Sources

Every variable should identify where its value originates.

Initial controlled vocabulary:

```text
user_input
deemed
lookup
derived
conditional
```

## user_input

Provided by the person or system performing the calculation.

Examples:

- Equipment capacity
- Existing efficiency
- Installed efficiency
- Insulation area
- Pre-retrofit blower-door measurement

## deemed

A fixed assumption specified by the TRM.

Example:

```yaml
source: deemed
value: 0.75
```

## lookup

Selected from a TRM table according to one or more other variables.

Example:

```yaml
source: lookup
lookup: cooling_flh_by_location
```

## derived

Calculated from other variables before the primary savings calculation.

## conditional

Value or methodology depends on a TRM-defined condition or decision rule.

The extraction process should preserve conditional logic rather than reducing it to a single default value.

---

# 9. Lookup Tables

TRM lookup tables should generally remain structured data rather than being hard-coded into Python.

Example:

```yaml
lookups:

  cooling_flh_by_location:
    description: Cooling equivalent full-load hours
    unit: hours/year

    source:
      page: SOURCE_PAGE
      table: SOURCE_TABLE

    values:
      location_a: VALUE
      location_b: VALUE
      location_c: VALUE
```

This makes future TRM updates easy to review through Git.

For example:

```diff
- dover: OLD_VALUE
+ dover: NEW_VALUE
```

The actual values must always be extracted and validated against the applicable TRM version.

---

# 10. Source Provenance

Every assumption, lookup table, and calculation should retain its source whenever possible.

Example:

```yaml
source:
  page: 76
  table: "SOURCE_TABLE"
  note: "Default when actual value is unavailable"
```

This enables the eventual calculator to display information such as:

> Cooling full-load hours: X hours/year  
> Source: Delaware TRM v5, p. 76

Source provenance is a core feature, not optional metadata.

The calculator should make it possible to determine **where every important value came from**.

---

# 11. Applications and Baselines

A single measure may have multiple applications or baseline conditions.

These should be explicitly represented rather than flattened into one generic measure.

Example:

```yaml
applications:

  - id: time_of_sale
    name: Time of Sale

    baseline:
      type: code_standard

  - id: early_replacement
    name: Early Replacement

    baseline:
      type: existing_equipment
```

Different applications may have different:

- Required inputs
- Baseline assumptions
- Equations
- Measure lives
- Cost treatments
- Eligibility requirements

The data model must allow these differences.

---

# 12. Calculations

Calculation metadata should be stored in YAML.

Example:

```yaml
calculations:

  annual_cooling_savings:
    name: Annual cooling energy savings

    output: kwh_cooling
    unit: kWh/year

    equation_display: >
      TRM equation displayed here

    variables:
      - capacity
      - cooling_full_load_hours
      - baseline_seer
      - efficient_seer

    implementation:
      function: annual_cooling_savings

    source:
      page: SOURCE_PAGE
```

The `equation_display` field exists for documentation and UI purposes.

It should **not** generally be executed directly.

---

# 13. Executable Calculation Logic

Actual calculations should be implemented as deterministic Python functions.

Example structure:

```python
def annual_cooling_savings(
    capacity,
    cooling_full_load_hours,
    baseline_seer,
    efficient_seer,
):
    # Implement equation exactly according to applicable TRM.
    ...
```

The YAML describes the methodology.

Python executes the methodology.

This separation allows complicated TRM logic to use:

- Conditionals
- Intermediate calculations
- Lookup tables
- Multiple baseline cases
- Early-replacement logic
- Error handling

Avoid dynamically executing equation strings with `eval()`.

---

# 14. Outputs

Outputs should also be explicitly defined.

Possible outputs include:

- Annual electric energy savings (kWh/year)
- Summer peak demand savings (kW)
- Fossil-fuel savings
- Water savings
- Measure life
- Incremental cost
- Other TRM-defined impacts

Example:

```yaml
outputs:

  - id: annual_kwh_savings
    name: Annual Electric Savings
    unit: kWh/year

  - id: peak_kw_savings
    name: Summer Peak Demand Savings
    unit: kW
```

---

# 15. Economics and Measure Life

Where provided by the TRM, capture:

```yaml
measure_life:
  value: VALUE
  unit: years
  source:
    page: SOURCE_PAGE

costs:
  incremental_cost:
    value: VALUE
    unit: USD
    source:
      page: SOURCE_PAGE
```

The schema should also support more complicated cost structures when necessary.

---

# 16. Pydantic Validation

All YAML measure definitions should be validated using Pydantic.

Conceptual example:

```python
class Variable(BaseModel):
    id: str
    symbol: str | None
    name: str
    unit: str | None
    source: VariableSource
    required: bool = False
    value: float | str | None = None


class Measure(BaseModel):
    id: str
    jurisdiction: str
    trm_version: str
    classification: Classification
    variables: list[Variable]
    calculations: dict[str, Calculation]
    applications: list[Application]
```

Enums should be used for controlled fields where appropriate.

For example, AI-generated data containing:

```yaml
source: probably_from_table
```

should fail validation rather than silently entering the dataset.

---

# 17. Testing Strategy

Every implemented measure should have automated tests.

The preferred validation hierarchy is:

### 1. Published TRM examples

If the TRM provides an illustrative calculation, the implementation should reproduce the published result within an appropriate tolerance.

### 2. Independently calculated test cases

Create known input/output cases independently from the implementation.

### 3. Boundary and conditional tests

Test:

- Minimum/maximum allowed values
- Missing optional values
- Default assumptions
- Lookup-table boundaries
- Different baseline cases
- Early replacement vs. time of sale
- Other measure-specific conditions

### 4. Regression tests

Once a calculation has been validated, future changes should not alter its result unexpectedly.

---

# 18. Implementation Status

Each measure should track implementation and validation status.

Example:

```yaml
status:
  metadata_extracted: true
  variables_extracted: true
  equations_extracted: true
  calculation_implemented: false
  automated_tests: false
  human_reviewed: false
```

Potential additional fields:

```yaml
review:
  reviewed_by: null
  reviewed_date: null
  notes: []
```

This makes it possible to distinguish between:

> "AI extracted this measure"

and

> "This measure has been implemented, tested, and manually validated."

---

# 19. TRM Manifest

Each TRM version should have a manifest listing all known measures.

Example:

```yaml
jurisdiction: DE
version: "5.0"

measures:

  - id: de-res-hvac-air-source-heat-pump
    sector: residential
    category: hvac
    name: Air Source Heat Pump
    file: residential/hvac/air_source_heat_pump.yaml

  - id: de-res-hvac-air-sealing
    sector: residential
    category: hvac
    name: Air Sealing
    file: residential/hvac/air_sealing.yaml
```

The manifest provides an authoritative inventory.

It can also power application navigation and progress tracking.

---

# 20. AI Extraction Strategy

AI should accelerate TRM conversion but should not be treated as the authoritative interpreter.

For each measure, the extraction process should:

1. Identify measure metadata.
2. Extract descriptions and eligibility requirements.
3. Identify applications/baseline cases.
4. Identify user-provided inputs.
5. Identify deemed assumptions.
6. Extract lookup tables.
7. Identify derived variables.
8. Extract calculation equations.
9. Identify outputs.
10. Capture measure life and cost information.
11. Preserve page/table references.
12. Identify conditional logic.
13. Flag ambiguous material rather than guessing.

AI output must pass Pydantic validation before being accepted.

Technical correctness must then be validated separately.

---

# 21. Recommended MVP Measures

Do not initially attempt to implement the entire TRM.

Use several structurally different measures to develop and stress-test the schema.

Initial candidates:

### 1. Residential Air Source Heat Pump

Use as the first schema-design measure.

Useful because it introduces:

- Multiple applications/baselines
- Equipment efficiency variables
- User inputs
- Deemed assumptions
- Lookup values
- Derived values
- Multiple savings outputs
- Conditional logic

### 2. Residential Air Sealing

Useful because it introduces:

- Pre/post measurements
- Building characteristics
- Location-dependent assumptions
- Lookup tables
- Heating and cooling interactions

### 3. Attic/Ceiling/Roof Insulation

Useful for testing:

- Existing vs. installed R-values
- Area
- Building-envelope calculations
- TRM assumptions

### 4. Simple Lighting or Domestic Hot Water Measure

Useful for ensuring the architecture does not overcomplicate straightforward calculations.

### 5. C&I Unitary HVAC

Introduces the Commercial & Industrial market sector and tests whether the architecture generalizes beyond residential measures.

After these measures have been implemented, revise the schema as necessary and freeze **Schema v1.0** before performing large-scale extraction.

---

# 22. Proposed Development Sequence

## Phase 1 — Schema Prototype

Implement:

```text
Air Source Heat Pump
```

Create:

```text
air_source_heat_pump.yaml
```

plus:

```text
air_source_heat_pump.py
```

and associated tests.

## Phase 2 — Stress-Test Schema

Implement:

```text
Air Sealing
Attic Insulation
Simple Measure
C&I Unitary HVAC
```

Modify the schema as new requirements emerge.

## Phase 3 — Freeze Schema v1

Once the schema successfully represents several structurally different measures, define Schema v1.0.

## Phase 4 — Full TRM Catalog

Extract metadata for every Delaware V5 measure.

At minimum:

- Sector
- Category
- Measure name
- TRM identifier
- Effective date
- Source pages
- File path
- Implementation status

## Phase 5 — Structured Extraction

Use AI to populate measure YAML files systematically.

Do not assume extracted calculations are validated.

## Phase 6 — Calculation Implementation

Implement calculations measure-by-measure.

Use AI coding agents to accelerate implementation while requiring deterministic Python logic.

## Phase 7 — Validation

Add:

- TRM example tests
- Independent tests
- Conditional tests
- Regression tests
- Manual review

## Phase 8 — User Interface

Build the Streamlit application on top of the validated calculation engine.

The UI should dynamically determine required user inputs from measure metadata wherever practical.

## Phase 9 — API

Expose validated calculations through FastAPI once there is a reason to support external integrations or batch processing.

---

# 23. Future Multi-Jurisdiction Architecture

The schema should not contain Delaware-specific assumptions at the framework level.

Use:

```yaml
jurisdiction: DE
trm_version: "5.0"
```

rather than:

```yaml
delaware_trm_version: "5.0"
```

Future structure:

```text
trm/
├── de/
│   ├── v5/
│   └── v6/
│
├── md/
│   └── ...
│
├── nj/
│   └── ...
│
└── pa/
    └── ...
```

This allows the same engine to eventually represent multiple state or regional TRMs.

---

# 24. Future Application Architecture

Initial architecture:

```text
TRM YAML
    ↓
Pydantic
    ↓
Python Calculation Engine
    ↓
Streamlit
```

Potential mature architecture:

```text
                 Versioned TRM Repository
                           ↓
                    Calculation Engine
                           ↓
                        FastAPI
                     ↙      ↓      ↘
                  Web      Batch   External Systems
                   ↓
            Application Database
```

The authoritative TRM definitions remain version-controlled separately from application/user data.

---

# 25. Core Product Principle

The objective is not simply to create a nicer interface for a PDF.

The project should create a:

> **Version-controlled, source-cited, machine-readable, deterministic, and testable implementation of technical reference manual methodologies.**

The Delaware V5 calculator is the first application built on top of that infrastructure.

Every calculated value should ultimately be answerable to the question:

> **Where did this number come from?**

The system should be able to identify the user input, TRM assumption, lookup value, equation, TRM version, and source location that produced the result.