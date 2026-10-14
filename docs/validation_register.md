# Validation Register — TRM Ambiguities and Implementation Decisions

A living list of points in the source TRM that are ambiguous, conflicting, or
unsupported, together with the decisions this implementation made about them.
It is the agenda for review with an energy efficiency expert.

**Ground rules**

- A passing test shows that the code is consistent with the decision recorded
  here. It does **not** show that the decision is correct. Issues are never
  marked Resolved because tests pass.
- An issue becomes **Resolved** only when a named reviewer records a resolution
  and review date. If a resolution changes values or equations, the YAML, code,
  and tests change in the same PR and that PR references the issue ID.
- Issue IDs are permanent. Do not renumber or reuse them. `tests/test_traceability.py`
  checks that every ID referenced from YAML (`issues: [...]`) and tests
  (`@pytest.mark.trm_issue(...)`) exists here.

**Categories**

| Category | Meaning |
|---|---|
| Mathematical inconsistency | The TRM's own numbers or equations disagree with each other. |
| Ambiguous methodology | The TRM does not say clearly how to calculate something, or which value to use. |
| Unsupported assumption | A value is stated without a source, or its source does not obviously support it. |
| Regulatory applicability | A question of policy or program rules rather than engineering: what is allowed, required, or in effect. |

**Review status:** Open · Under Review · Resolved · Deferred (not needed until a later PR).

**Source:** Delaware TRM Version 5.0, *draft*
([PDF](https://documents.dnrec.delaware.gov/energy/eeac/emv/meetings/2025/0408/Draft-Technical-Reference-Manual.pdf)).
Page numbers are the printed page numbers, which match the PDF page numbers.

**YAML files:** `ASHP` = `trm/de/v5/residential/hvac/air_source_heat_pump.yaml`;
`LFSH` = `trm/de/v5/residential/water_heating/low_flow_shower_head.yaml`.

## Summary

| ID | Measure | Category | Topic | Affects PR 1 results | Status |
|---|---|---|---|---|---|
| [VR-001](#vr-001) | ASHP | Mathematical inconsistency | Peak kW equation divides by CF; examples multiply | **Yes** | Open |
| [VR-002](#vr-002) | ASHP | Mathematical inconsistency | Time of Sale kWh example uses old baseline values | Tests only | Open |
| [VR-003](#vr-003) | ASHP | Ambiguous methodology | Which baseline efficiencies apply to Time of Sale | **Yes** | Open |
| [VR-004](#vr-004) | ASHP | Ambiguous methodology | SEER/HSPF/EER vs SEER2/HSPF2/EER2 rating basis | **Yes** | Open |
| [VR-005](#vr-005) | ASHP | Ambiguous methodology | Baseline capacity for new construction | **Yes** | Open |
| [VR-006](#vr-006) | ASHP | Regulatory applicability | Which peak definition and CF to report | **Yes** | Open |
| [VR-007](#vr-007) | ASHP | Mathematical inconsistency | Heating-hours footnote cites 1195, table uses 866 | No (values used as tabled) | Open |
| [VR-008](#vr-008) | ASHP | Regulatory applicability | Efficient-unit eligibility is not enforced | **Yes** | Open |
| [VR-009](#vr-009) | ASHP | Ambiguous methodology | Rating condition for heating capacity | **Yes** | Open |
| [VR-010](#vr-010) | ASHP | Mathematical inconsistency | Early Replacement "new baseline" values disagree | No | Deferred |
| [VR-011](#vr-011) | ASHP | Ambiguous methodology | "SEER2" in the Wassmer formula means SEER squared | No | Deferred |
| [VR-012](#vr-012) | ASHP | Ambiguous methodology | "No central cooling" rule has no method | No | Deferred |
| [VR-013](#vr-013) | ASHP | Regulatory applicability | Only Wilmington/Baltimore/DC hours; none for Kent or Sussex | **Yes** | Open |
| [VR-014](#vr-014) | ASHP | Ambiguous methodology | Incremental cost table only covers integer SEER 16–21 | No | Deferred |
| [VR-015](#vr-015) | LFSH | Mathematical inconsistency | kWh/kW/water examples omit ShowersPerson and use 101 °F | Tests only | Open |
| [VR-016](#vr-016) | LFSH | Mathematical inconsistency | MMBtu example needs 0.75 efficiency; 0.80 defined | **Yes** | Open |
| [VR-017](#vr-017) | LFSH | Regulatory applicability | Footnote refers to a deemed savings value that is not published | **Yes** | Open |
| [VR-018](#vr-018) | LFSH | Unsupported assumption | Shower temperature 105 °F has no source | **Yes** | Open |
| [VR-019](#vr-019) | LFSH | Unsupported assumption | 2.07 kWh/CCF has no source and is optional to claim | **Yes** | Open |
| [VR-020](#vr-020) | LFSH | Ambiguous methodology | Rules for measured flow rates | **Yes** | Open |
| [VR-021](#vr-021) | LFSH | Regulatory applicability | ≤ 2.0 GPM eligibility limit vs "lower than code" | **Yes** | Open |
| [VR-022](#vr-022) | LFSH | Unsupported assumption | Derivation of CF = 0.0039 | **Yes** | Open |
| [VR-023](#vr-023) | LFSH | Regulatory applicability | Water heater types not covered (e.g. heat pump water heaters) | **Yes** | Open |
| [VR-024](#vr-024) | LFSH | Ambiguous methodology | Rounding of intermediate values | Minor | Open |
| [VR-025](#vr-025) | Both | Regulatory applicability | Source is a draft TRM | **Yes** | Open |
| [VR-026](#vr-026) | LFSH | Regulatory applicability | Eligibility when installed flow ≥ baseline flow | **Yes** (warning) | Open |

---

## Air Source Heat Pump (Delaware TRM v5.0, pp. 71–81)

### VR-001

**Peak demand equation divides by CF; worked examples multiply by CF**

- **Measure / TRM version:** Split System Air Source Heat Pump, DE TRM 5.0 (draft)
- **Category:** Mathematical inconsistency
- **Source:** p. 78, Summer Coincident Peak kW Savings Algorithm (Time of Sale and both Early Replacement equations); examples on pp. 79–80
- **Description:** All three printed kW equations put CF in the denominator. All three worked examples multiply by CF. Dividing by a coincidence factor below 1 would make peak savings larger than the connected-load reduction, which contradicts how CF is described in the introduction (p. 9).
- **Conflicting values or formulas:**
  - Printed: `ΔkW = ((BTUHCexist × 1/EERbase) − (BTUHCee × 1/EERee)) / (1000 × CF)`
  - Examples: `((36,000 × 1/11.8) − (24,000 × 1/12.5)) / 1,000 × 0.69 = 0.78 kW` (p. 79); `… 1/9.9 … = 1.18 kW` (p. 80). Dividing would give 1.64 kW and 2.49 kW.
- **Current implementation decision:** Multiply by CF. The YAML keeps the printed form in `equation_as_printed` and records the decision in `interpretation`; every kW output carries `interpretation` and this issue ID in its result.
- **Rationale:** Consistent with all three worked examples, the Central A/C measure's description of CF, and the meaning of a coincidence factor.
- **Potential impact:** If the printed equation were intended, kW savings would be (1/CF²) ≈ 2.1× (SSP) or 2.3× (PJM) the implemented values.
- **Question for expert:** Is multiplying by CF correct for DE TRM v5 ASHP peak savings, and is the printed equation a typesetting error?
- **Linked definitions:** ASHP `calculations[time_of_sale_peak_demand_savings]`
- **Linked tests:** `tests/de_v5/test_air_source_heat_pump.py::test_published_time_of_sale_kw_example`, `::test_published_early_replacement_kw_examples_confirm_cf_multiplication`, `::test_peak_demand_outputs_are_flagged_as_interpretation`
- **Review status:** Open
- **Reviewer:**
- **Review date:**
- **Resolution:**

### VR-002

**Time of Sale kWh example uses baseline values that differ from the defined defaults**

- **Measure / TRM version:** Split System Air Source Heat Pump, DE TRM 5.0 (draft)
- **Category:** Mathematical inconsistency
- **Source:** p. 77, Time of Sale illustrative example; p. 75 (SEERbase), p. 76 (HSPFbase)
- **Description:** The example uses SEER 14 and HSPF 7.7 as the baseline. The variable definitions give SEERbase = 15 and HSPFbase = 8.8. HSPF 7.7 is the 2006–2014 *existing-equipment* value from the age table on p. 77, not a new-equipment baseline.
- **Conflicting values or formulas:** Example: `744 × (36,000/14 − 36,000/15)/1,000 + 866 × (36,000/7.7 − 36,000/8.5)/1,000 = 509 kWh`. With the defined baselines the same unit saves `744 × (36,000/15 − 36,000/15)/1,000 + 866 × (36,000/8.8 − 36,000/8.5)/1,000 = −125 kWh` (an HSPF 8.5 unit is below the 8.8 baseline).
- **Current implementation decision:** Use the defined values (15 / 8.8). Reproduce the example by calling the equation directly with the example's own inputs.
- **Rationale:** The TRM states examples are illustrative only and should not be used as default assumptions (p. 8 and the example heading).
- **Potential impact:** None on calculations. The example would mislead anyone checking results against it.
- **Question for expert:** Confirm the example is stale (pre-2023 baseline) and that SEERbase 15 / HSPFbase 8.8 are the intended Time of Sale defaults.
- **Linked definitions:** ASHP `calculations[time_of_sale_energy_savings]`
- **Linked tests:** `tests/de_v5/test_air_source_heat_pump.py::test_published_time_of_sale_kwh_example`
- **Review status:** Open
- **Reviewer:**
- **Review date:**
- **Resolution:**

### VR-003

**Which baseline efficiencies apply to Time of Sale**

- **Measure / TRM version:** Split System Air Source Heat Pump, DE TRM 5.0 (draft)
- **Category:** Ambiguous methodology
- **Source:** p. 71 (Federal Standard table, manufactured before 1/1/2023), p. 72 (table for units manufactured after 1/1/2023), p. 73 (baseline definition), pp. 75, 76, 78 (variable definitions)
- **Description:** The baseline definition (p. 73) points to "the minimum Federal standards defined above", but three sets of values appear in the section.
- **Conflicting values or formulas:**

  | Source | SEER | HSPF | EER |
  |---|---|---|---|
  | p. 71 Federal Standard (before 1/1/2023) | 14 | 8.2 | 11.8 |
  | p. 72 Federal Standard, Southeast (after 1/1/2023) | 14.3 SEER2 | 7.5 HSPF2 | 11.9 EER2 |
  | Variable definitions (pp. 75, 76, 78) | 15 | 8.8 | 12.3 |

- **Current implementation decision:** Use the variable definitions: SEERbase 15, HSPFbase 8.8, EERbase 12.3.
- **Rationale:** These are the values given directly against the equation variables, with footnotes citing the current federal minimum. They correspond approximately to the SEER2 14.3 / HSPF2 7.5 standard expressed on the older SEER/HSPF basis.
- **Potential impact:** Large. Moving from 15/8.8/12.3 to 14/8.2/11.8 would increase savings for the same efficient unit.
- **Question for expert:** Which baseline should Delaware programs use for Time of Sale ASHP installed today: the variable-definition values (15 / 8.8 / 12.3), or the p. 71 or p. 72 table values?
- **Linked definitions:** ASHP `variables[seer_baseline, hspf_baseline, eer_baseline]`, `applications[time_of_sale]`
- **Linked tests:** `tests/de_v5/test_air_source_heat_pump.py::test_time_of_sale_defaults_wilmington`, `::test_time_of_sale_downsized_washington_dc`
- **Review status:** Open
- **Reviewer:**
- **Review date:**
- **Resolution:**

### VR-004

**Rating basis: SEER/HSPF/EER vs SEER2/HSPF2/EER2**

- **Measure / TRM version:** Split System Air Source Heat Pump, DE TRM 5.0 (draft)
- **Category:** Ambiguous methodology
- **Source:** p. 73: "SEER, EER, and HSPF should be replaced with SEER2, EER2, and HSPF2 ratings in the below equations where appropriate."
- **Description:** Units manufactured after 1/1/2023 are rated in SEER2/HSPF2/EER2, which are numerically lower than SEER/HSPF/EER for the same unit. The TRM does not say when replacement is "appropriate", and gives no SEER2-basis baseline values next to the equation variables. Mixing bases (e.g. a SEER2 efficient rating against a SEER baseline) understates savings.
- **Conflicting values or formulas:** Baselines in the equations are SEER 15 / HSPF 8.8 / EER 12.3 (SEER basis); p. 72 gives 14.3 SEER2 / 7.5 HSPF2 / 11.9 EER2.
- **Current implementation decision:** All ratings are on the SEER/HSPF/EER basis. Efficient-unit inputs are documented as SEER/HSPF/EER. No conversion is performed and SEER2 inputs cannot be detected.
- **Rationale:** Keeps baseline and efficient ratings on the same basis using the values the TRM attaches to the equation variables. Conversion factors are not given in the TRM and are not invented.
- **Potential impact:** Large if users enter SEER2 ratings: savings would be understated, and could turn negative.
- **Question for expert:** For units rated in SEER2/HSPF2/EER2, should users enter those ratings with SEER2-basis baselines (14.3 / 7.5 / 11.9), or convert to SEER basis? If converting, which conversion factors are approved for Delaware?
- **Linked definitions:** ASHP `variables[seer_efficient, hspf_efficient, eer_efficient, seer_baseline, hspf_baseline, eer_baseline]`, `calculations[time_of_sale_energy_savings]`
- **Linked tests:** —
- **Review status:** Open
- **Reviewer:**
- **Review date:**
- **Resolution:**

### VR-005

**Baseline capacity in Time of Sale, including new construction**

- **Measure / TRM version:** Split System Air Source Heat Pump, DE TRM 5.0 (draft)
- **Category:** Ambiguous methodology
- **Source:** p. 72 (Time of Sale includes "installation of a new system in a new home"); p. 73 (equation uses BTUHCexist, BTUHHexist); pp. 74, 76 (definitions: capacity of existing ASHP, "Actual")
- **Description:** The Time of Sale equation sizes the baseline using the *existing* unit's capacity. In a new home there is no existing unit, and the TRM does not say what to use.
- **Conflicting values or formulas:** —
- **Current implementation decision:** Existing cooling and heating capacities are required inputs for all Time of Sale calculations. The variable description states they are also the baseline capacities. No default is provided for new construction.
- **Rationale:** No TRM value exists to default to.
- **Potential impact:** Users may enter the efficient unit's capacity for new homes, which is plausible but unconfirmed.
- **Question for expert:** For new construction under Time of Sale, should baseline capacity equal the installed unit's capacity?
- **Linked definitions:** ASHP `variables[cooling_capacity_existing, heating_capacity_existing]`, `applications[time_of_sale]`
- **Linked tests:** `tests/de_v5/test_air_source_heat_pump.py::test_time_of_sale_downsized_washington_dc`
- **Review status:** Open
- **Reviewer:**
- **Review date:**
- **Resolution:**

### VR-006

**Peak definitions and coincidence factors**

- **Measure / TRM version:** Split System Air Source Heat Pump, DE TRM 5.0 (draft)
- **Category:** Regulatory applicability
- **Source:** p. 9 (peak definitions); p. 79, footnotes 206–207 (CFSSP 0.69, CFPJM 0.66)
- **Description:** The TRM provides two coincidence factors, but the equation names a single "CF". Both values come from BG&E research on Central A/C and heat pumps in Maryland. The introduction calls system peak the primary definition and PJM the secondary one.
- **Conflicting values or formulas:** CFSSP = 0.69; CFPJM = 0.66.
- **Current implementation decision:** Report both outputs (`kw_ssp_savings`, `kw_pjm_savings`) and do not choose between them.
- **Rationale:** Selecting one is a reporting/policy choice, not a calculation choice.
- **Potential impact:** About 4.5% difference between the two outputs.
- **Question for expert:** Which peak definition should Delaware programs report, and should the calculator show both?
- **Linked definitions:** ASHP `variables[coincidence_factor_ssp, coincidence_factor_pjm]`, `calculations[time_of_sale_peak_demand_savings]`
- **Linked tests:** —
- **Review status:** Open
- **Reviewer:**
- **Review date:**
- **Resolution:**

### VR-007

**Heating full-load-hours footnote cites a different Baltimore value**

- **Measure / TRM version:** Split System Air Source Heat Pump, DE TRM 5.0 (draft)
- **Category:** Mathematical inconsistency
- **Source:** p. 76, FLHheat table and footnote 198
- **Description:** Footnote 198 says the Wilmington and DC values were scaled from BG&E's Baltimore value of 1195 hours. The table's Baltimore value is 866 (footnote 199), and the Wilmington and DC values match scaling from 866, not 1195.
- **Conflicting values or formulas:** 866 × 2346/2172 = 935 and 866 × 2061/2172 = 822 (match the table). 1195 × 2346/2172 = 1291 and 1195 × 2061/2172 = 1134.
- **Current implementation decision:** Use the tabled values (935 / 866 / 822).
- **Rationale:** The table is internally consistent; the footnote text appears outdated.
- **Potential impact:** None if the table is correct; heating savings would rise by about 38% if 1195 were intended.
- **Question for expert:** Confirm the tabled heating hours and that footnote 198's 1195 reference is outdated.
- **Linked definitions:** ASHP `lookups[heating_full_load_hours_by_location]`
- **Linked tests:** `tests/de_v5/test_air_source_heat_pump.py::test_full_load_hours_lookup`
- **Review status:** Open
- **Reviewer:**
- **Review date:**
- **Resolution:**

### VR-008

**Efficient-unit eligibility is not enforced**

- **Measure / TRM version:** Split System Air Source Heat Pump, DE TRM 5.0 (draft)
- **Category:** Regulatory applicability
- **Source:** p. 71 (ENERGY STAR V6.2, footnote 187 links to the 2025 *Most Efficient* criteria); p. 72 (ENERGY STAR 16.0 SEER2 / 8.0 HSPF2 / 11.0 EER2); p. 73 (efficient condition "or other specifications as determined by the programs"; ENERGY STAR revision expected for 2026)
- **Description:** The efficient condition refers to ENERGY STAR, but the version cited in the text (V6.2) and the linked document (2025 Most Efficient) differ. Programs may also set their own specifications.
- **Conflicting values or formulas:** ENERGY STAR before 1/1/2023: 15 SEER / 8.5 HSPF / 12.5 EER. After: 16.0 SEER2 / 8.0 HSPF2 / 11.0 EER2.
- **Current implementation decision:** No minimum efficiency is enforced for the efficient unit, apart from ratings being positive. Every Time of Sale result carries the warning `efficient_equipment_eligibility_not_verified`, which references this issue. Equipment below any standard is still calculated, not rejected.
- **Rationale:** The applicable specification is a program decision, and the TRM allows program-defined specifications. A warning makes the gap visible without inventing thresholds.
- **Potential impact:** Users can calculate savings for units that would not qualify for a program.
- **Question for expert:** Should the calculator enforce a minimum efficient-unit specification, and if so which one?
- **Linked definitions:** ASHP `variables[seer_efficient, hspf_efficient, eer_efficient]`, `applications[time_of_sale]`, `warnings[efficient_equipment_eligibility_not_verified]`
- **Linked tests:** `tests/de_v5/test_air_source_heat_pump.py::test_eligibility_warning_is_returned_without_changing_results`, `::test_eligibility_warning_does_not_reject_low_efficiency_equipment`
- **Review status:** Open
- **Reviewer:**
- **Review date:**
- **Resolution:**

### VR-009

**Rating condition for heating capacity**

- **Measure / TRM version:** Split System Air Source Heat Pump, DE TRM 5.0 (draft)
- **Category:** Ambiguous methodology
- **Source:** p. 76 (BTUHHexist, BTUHHee: "tons × 12,000 BTU/hr", "Actual")
- **Description:** Heat pump heating capacity depends on the rating condition (e.g. 47 °F vs 17 °F). The TRM defines it only as "tons × 12,000 BTU/hr", which suggests the nominal cooling tonnage may be intended.
- **Conflicting values or formulas:** —
- **Current implementation decision:** Heating capacities are separate user inputs in Btu/hr with no stated rating condition.
- **Rationale:** Matches the TRM's separate variables without inventing a rating point.
- **Potential impact:** Moderate. Rated heating capacity at 47 °F can differ noticeably from nominal tonnage × 12,000.
- **Question for expert:** Should heating capacity be the nominal tonnage × 12,000, or the AHRI-rated heating capacity at 47 °F?
- **Linked definitions:** ASHP `variables[heating_capacity_existing, heating_capacity_efficient]`
- **Linked tests:** `tests/de_v5/test_air_source_heat_pump.py::test_time_of_sale_downsized_washington_dc`
- **Review status:** Open
- **Reviewer:**
- **Review date:**
- **Resolution:**

### VR-010

**Early Replacement "new baseline" efficiencies disagree with each other and with Time of Sale**

- **Measure / TRM version:** Split System Air Source Heat Pump, DE TRM 5.0 (draft)
- **Category:** Mathematical inconsistency
- **Source:** p. 73 (Early Retirement/Replacement Baseline Efficiencies table); p. 75 (SEERbasereplace); p. 77 (HSPFbasereplace); p. 79 (EERbasereplace); pp. 77–78 (example)
- **Description:** The "new baseline" values for the remaining measure life do not form a consistent set.
- **Conflicting values or formulas:**

  | Value | ASHP | Electric resistance + Central AC |
  |---|---|---|
  | SEERbasereplace (p. 75) | 15 | 15 |
  | Table p. 73 SEER | 14 | 14 |
  | EERbasereplace (p. 79) | 11.8 (= Wassmer of SEER 14) | 11.8 |
  | HSPFbasereplace (p. 77) / table p. 73 | 8.2 | 3.41 |
  | Time of Sale HSPFbase (p. 76) | 8.8 | — |

  The Early Replacement example on p. 78 uses SEER 14 for the remaining-life baseline (7,420 kWh), not the defined 15.
- **Current implementation decision:** Not implemented in PR 1. Early Replacement is listed in the YAML with `calculation_implemented: false`.
- **Rationale:** Out of scope for PR 1.
- **Potential impact:** Will affect Early Replacement savings when implemented.
- **Question for expert:** What are the correct new-baseline SEER, EER, and HSPF for Early Replacement? Should an existing electric-resistance home's new baseline really be HSPF 3.41 (electric resistance) rather than a new heat pump?
- **Linked definitions:** ASHP `applications[early_replacement]`
- **Linked tests:** `tests/de_v5/test_air_source_heat_pump.py::test_early_replacement_is_not_implemented`
- **Review status:** Deferred
- **Reviewer:**
- **Review date:**
- **Resolution:**

### VR-011

**"SEER2" in the Wassmer EER formula means SEER squared**

- **Measure / TRM version:** Split System Air Source Heat Pump, DE TRM 5.0 (draft)
- **Category:** Ambiguous methodology
- **Source:** p. 71 footnote 190; p. 78 footnote 203; p. 79 (EERexist conversion)
- **Description:** The formula is printed as `EER = (-0.02 × SEER2) + (1.12 × SEER)`. Footnote 203 uses a superscript (SEER²) and the result checks out: −0.02 × 15² + 1.12 × 15 = 12.3. In the text on p. 79 the same expression could be misread as the SEER2 rating, which also appears throughout the section.
- **Conflicting values or formulas:** SEER² interpretation gives EERbase = 12.3 (matches TRM). SEER2-rating interpretation is not dimensionally meaningful.
- **Current implementation decision:** No conversion is used in PR 1. EERbase is taken as the published 12.3. When Early Replacement is implemented, the formula will use SEER².
- **Rationale:** The squared interpretation reproduces the TRM's published values (11.8 from SEER 14, 12.3 from SEER 15).
- **Potential impact:** Early Replacement only (EERexist derived from SEERexist).
- **Question for expert:** Confirm SEER² is intended, and say whether the formula applies to SEER2-rated equipment (footnote 190 says it is valid only for single-speed units).
- **Linked definitions:** ASHP `variables[eer_baseline]`, `applications[early_replacement]`
- **Linked tests:** —
- **Review status:** Deferred
- **Reviewer:**
- **Review date:**
- **Resolution:**

### VR-012

**"No central cooling" rule for Early Replacement has no method**

- **Measure / TRM version:** Split System Air Source Heat Pump, DE TRM 5.0 (draft)
- **Category:** Ambiguous methodology
- **Source:** p. 75 (SEERexist table, footnote 197); p. 79 (EERexist table, footnote 205)
- **Description:** When there is no existing central cooling, the TRM says to set 1/SEERexist = 0 and 1/EERexist = 0, and that "the added cooling load should be subtracted from any heating benefit." It gives no method for calculating that added load.
- **Conflicting values or formulas:** —
- **Current implementation decision:** Not implemented in PR 1.
- **Rationale:** Out of scope; the method needs to be defined before it can be implemented.
- **Potential impact:** Early Replacement savings in homes without central cooling.
- **Question for expert:** With 1/SEERexist = 0 the cooling term is already negative. Does that negative term fully represent the "added cooling load", or must something else be subtracted?
- **Linked definitions:** ASHP `applications[early_replacement]`
- **Linked tests:** —
- **Review status:** Deferred
- **Reviewer:**
- **Review date:**
- **Resolution:**

### VR-013

**Full-load hours are given only for Wilmington, Baltimore, and Washington DC**

- **Measure / TRM version:** Split System Air Source Heat Pump, DE TRM 5.0 (draft)
- **Category:** Regulatory applicability
- **Source:** p. 74 (EFLHcool table); p. 76 (FLHheat table)
- **Description:** The only Delaware location is Wilmington (New Castle County). There are no values for Dover (Kent County) or Sussex County, and no rule for choosing a location.
- **Conflicting values or formulas:** —
- **Current implementation decision:** Location is a required choice among the three published locations. There is no default and no mapping from county or ZIP code.
- **Rationale:** Choosing a location for Kent or Sussex would be an unsupported assumption.
- **Potential impact:** Up to about 30% difference in cooling hours between locations.
- **Question for expert:** Which location should projects in Kent and Sussex counties use? Is Wilmington intended as the single Delaware value?
- **Linked definitions:** ASHP `variables[location]`, `lookups[cooling_full_load_hours_by_location, heating_full_load_hours_by_location]`
- **Linked tests:** `tests/de_v5/test_air_source_heat_pump.py::test_full_load_hours_lookup`, `::test_invalid_inputs_are_rejected`
- **Review status:** Open
- **Reviewer:**
- **Review date:**
- **Resolution:**

### VR-014

**Incremental cost table covers only integer SEER 16–21**

- **Measure / TRM version:** Split System Air Source Heat Pump, DE TRM 5.0 (draft)
- **Category:** Ambiguous methodology
- **Source:** pp. 80–81, Incremental Cost table (footnote 208, Itron 2017)
- **Description:** Costs per ton are listed for SEER 16, 17, …, 21 only. The table does not say how to treat fractional ratings, ratings below 16 (the ENERGY STAR minimum is 15 SEER), or SEER2 ratings.
- **Conflicting values or formulas:** —
- **Current implementation decision:** Not captured in PR 1 (deferred to PR 2 as agreed).
- **Rationale:** Out of scope.
- **Potential impact:** Cost-effectiveness inputs only; no effect on savings.
- **Question for expert:** For a SEER 15.5 or a SEER2-rated unit, should cost be interpolated, rounded down, or taken from the nearest row?
- **Linked definitions:** ASHP top-level `issues`
- **Linked tests:** —
- **Review status:** Deferred
- **Reviewer:**
- **Review date:**
- **Resolution:**

---

## Low Flow Shower Head (Delaware TRM v5.0, pp. 174–178)

### VR-015

**Illustrative examples omit ShowersPerson and use 101 °F instead of the defined 105 °F**

- **Measure / TRM version:** Low Flow Shower Head, DE TRM 5.0 (draft)
- **Category:** Mathematical inconsistency
- **Source:** p. 174 (equation); p. 175 (variable definitions and kWh example); p. 176 (kW example); p. 177 (MMBtu and water examples)
- **Description:** The equations include ShowersPerson (0.6) and TEMPsh is defined as 105 °F. The kWh, MMBtu, and water examples leave out ShowersPerson and use 101 °F. The kW example then divides that kWh by Hours = 72, which *does* include ShowersPerson. So no single consistent set of inputs reproduces every published example.
- **Conflicting values or formulas:**

  | Output (2.0 GPM unit) | Published example | Defined equation and defaults |
  |---|---|---|
  | kWh | 276 | 182.0 |
  | kW | 0.015 | 0.0099 |
  | Water (CCF) | 3.7 | 2.22 |
  | kWh from water | 7.7 | 4.60 |

- **Current implementation decision:** Use the equations and variable definitions as written (ShowersPerson 0.6, TEMPsh 105 °F). Tests reproduce each example by passing the example's own inputs to the equation functions, and document that the defaults give different results.
- **Rationale:** Approved approach: implement the documented equations and defaults, and do not adjust assumptions to match inconsistent examples. The TRM states examples are not default assumptions.
- **Potential impact:** Implemented kWh is about 34% lower than the example (the 0.6 factor lowers it; the 105 °F temperature raises it).
- **Question for expert:** Are the equations (with ShowersPerson) and TEMPsh = 105 °F correct, making the examples stale? Or are the examples (no ShowersPerson, 101 °F) what programs actually claim?
- **Linked definitions:** LFSH `variables[showers_per_person_per_day, shower_temperature]`, `calculations[electric_savings]`
- **Linked tests:** `tests/de_v5/test_low_flow_shower_head.py::test_published_kwh_example_uses_inputs_inconsistent_with_defaults`, `::test_published_kw_example`, `::test_published_mmbtu_example_requires_unstated_efficiency`, `::test_published_water_examples`, `::test_electric_defaults`
- **Review status:** Open
- **Reviewer:**
- **Review date:**
- **Resolution:**

### VR-016

**MMBtu example needs a 0.75 recovery efficiency; 0.80 is defined and printed**

- **Measure / TRM version:** Low Flow Shower Head, DE TRM 5.0 (draft)
- **Category:** Mathematical inconsistency
- **Source:** pp. 176–177 (Gas DHW Recovery Efficiency = 0.80, footnote 468; example)
- **Description:** The example prints "/ .80" but its result (1.23 MMBtu) is only reached with 0.75. Footnote 468 says new gas units range from 70–87% and that existing units average 75%, so the source seems to support 0.75 rather than 0.80. Elsewhere in the DHW section, DHW Pipe Insulation defines 0.75 (p. 189). Faucet Aerators defines 0.80 but its example also divides by 0.75 (p. 181).
- **Conflicting values or formulas:** Example inputs with 0.80 → 1.15 MMBtu; with 0.75 → 1.23 MMBtu (published).
- **Current implementation decision:** Use 0.80 as defined.
- **Rationale:** Approved approach: follow the variable definitions.
- **Potential impact:** If 0.75 is correct, fossil fuel savings are understated by about 6.3%.
- **Question for expert:** Should the gas recovery efficiency be 0.80 or 0.75?
- **Linked definitions:** LFSH `variables[fossil_recovery_efficiency]`, `calculations[fossil_fuel_savings]`
- **Linked tests:** `tests/de_v5/test_low_flow_shower_head.py::test_published_mmbtu_example_requires_unstated_efficiency`, `::test_fossil_fuel_defaults`
- **Review status:** Open
- **Reviewer:**
- **Review date:**
- **Resolution:**

### VR-017

**Footnote refers to a deemed savings result that is not published**

- **Measure / TRM version:** Low Flow Shower Head, DE TRM 5.0 (draft)
- **Category:** Regulatory applicability
- **Source:** p. 174, footnote 459: "the algorithm and variables are provided as documentation for the deemed savings result provided which should be claimed for all showerhead installations."
- **Description:** No deemed savings value appears in the section. The only results are illustrative examples marked "do not use as default assumption."
- **Conflicting values or formulas:** —
- **Current implementation decision:** Calculate savings from the algorithm with user inputs and TRM defaults. No deemed per-unit value is returned.
- **Rationale:** There is no published deemed value to use.
- **Potential impact:** If programs must claim a fixed deemed value, calculated results will differ from claimed savings.
- **Question for expert:** Should Delaware programs claim a single deemed value per showerhead? If so, what is it and where is it published? Can programs use measured flow rates (p. 174) under a deemed approach?
- **Linked definitions:** LFSH top-level `issues`
- **Linked tests:** —
- **Review status:** Open
- **Reviewer:**
- **Review date:**
- **Resolution:**

### VR-018

**Shower water temperature (105 °F) has no source**

- **Measure / TRM version:** Low Flow Shower Head, DE TRM 5.0 (draft)
- **Category:** Unsupported assumption
- **Source:** p. 175 (TEMPsh = 105, no footnote)
- **Description:** Every other assumption in the section has a footnote; TEMPsh does not. The examples use 101 °F (VR-015).
- **Conflicting values or formulas:** 105 °F (definition) vs 101 °F (examples).
- **Current implementation decision:** Use 105 °F.
- **Rationale:** Value given in the variable definition.
- **Potential impact:** Energy savings are proportional to (TEMPsh − 60.9): 105 °F gives 10% more savings than 101 °F.
- **Question for expert:** What is the source for TEMPsh, and is 105 °F correct?
- **Linked definitions:** LFSH `variables[shower_temperature]`
- **Linked tests:** —
- **Review status:** Open
- **Reviewer:**
- **Review date:**
- **Resolution:**

### VR-019

**2.07 kWh/CCF has no source and claiming it is optional**

- **Measure / TRM version:** Low Flow Shower Head, DE TRM 5.0 (draft)
- **Category:** Unsupported assumption
- **Source:** p. 176 ("utilities may consider whether it is appropriate to claim kWh savings from the reduction in water consumption"); p. 177 (ΔkWhwater = 2.07 kWh/CCF × ΔWater, no footnote; warning about double counting)
- **Description:** The factor is uncited, and the TRM leaves it to utilities whether to claim it.
- **Conflicting values or formulas:** —
- **Current implementation decision:** Return it as a separate output, `kwh_water_savings`, never added to `kwh_savings`. It is returned for both fuel types.
- **Rationale:** Keeps the optional claim visible and separate so users can decide.
- **Potential impact:** Small (about 4.6 kWh/year with defaults). Risk of double counting if added to kWh savings.
- **Question for expert:** Should Delaware programs claim water-related kWh savings? What is the source for 2.07 kWh/CCF? Does it apply to homes on private wells and septic systems?
- **Linked definitions:** LFSH `variables[kwh_per_ccf_water]`, `outputs[kwh_water_savings]`, `calculations[water_savings]`
- **Linked tests:** `tests/de_v5/test_low_flow_shower_head.py::test_electric_defaults`, `::test_fossil_fuel_defaults`
- **Review status:** Open
- **Reviewer:**
- **Review date:**
- **Resolution:**

### VR-020

**Rules for measured flow rates**

- **Measure / TRM version:** Low Flow Shower Head, DE TRM 5.0 (draft)
- **Category:** Ambiguous methodology
- **Source:** p. 174 (Baseline, Efficient Condition, GPMbase and GPMlow definitions)
- **Description:**
  1. The baseline section allows measured existing flow for *direct install* programs, but the GPMbase definition says "or actual flow rate if recorded" without limiting it to direct install.
  2. If the baseline is measured, the installed unit's *measured* flow must be used too. The calculator cannot verify this.
  3. The TRM does not say what to do if the measured baseline is at or below the installed flow rate, which gives zero or negative savings. The eligibility question is tracked separately as VR-026.
- **Conflicting values or formulas:** —
- **Current implementation decision:** `gpm_base` is optional (default 2.5) for both applications. The measured-flow coupling is documented but not enforced. Zero or negative savings are returned unchanged, with the warning `no_positive_water_savings` (see VR-026).
- **Rationale:** No TRM rule to enforce; avoids inventing eligibility rules.
- **Potential impact:** Users could combine a measured baseline with a rated installed flow, which the TRM disallows. Negative results are possible.
- **Question for expert:** Should a measured baseline be allowed for Time of Sale? When a baseline is measured, must the installed flow also be measured?
- **Linked definitions:** LFSH `variables[gpm_base, gpm_low]`, `applications[direct_install, time_of_sale]`
- **Linked tests:** `tests/de_v5/test_low_flow_shower_head.py::test_measured_flow_and_known_household_size`, `::test_equal_flow_rates_warn_and_give_zero_savings`, `::test_installed_flow_above_baseline_warns_and_keeps_negative_result`
- **Review status:** Open
- **Reviewer:**
- **Review date:**
- **Resolution:**

### VR-021

**Eligibility limit: ≤ 2.0 GPM vs "lower than required by code"**

- **Measure / TRM version:** Low Flow Shower Head, DE TRM 5.0 (draft)
- **Category:** Regulatory applicability
- **Source:** p. 174 (Measure Description: "low flow (≤2.0 GPM)"; Efficient Condition: "a lower GPM flow than required by code")
- **Description:** The two statements define different eligibility limits: ≤ 2.0 GPM vs < 2.5 GPM.
- **Conflicting values or formulas:** ≤ 2.0 GPM vs < 2.5 GPM.
- **Current implementation decision:** Enforce `gpm_low ≤ 2.0` as an input constraint.
- **Rationale:** The measure description gives an explicit numeric limit.
- **Potential impact:** Showerheads between 2.0 and 2.5 GPM are rejected.
- **Question for expert:** Is 2.0 GPM the eligibility limit for Delaware programs?
- **Linked definitions:** LFSH `variables[gpm_low]`
- **Linked tests:** `tests/de_v5/test_low_flow_shower_head.py::test_eligibility_maximum_flow_rate`
- **Review status:** Open
- **Reviewer:**
- **Review date:**
- **Resolution:**

### VR-022

**Derivation of the coincidence factor (0.0039)**

- **Measure / TRM version:** Low Flow Shower Head, DE TRM 5.0 (draft)
- **Category:** Unsupported assumption
- **Source:** p. 176, footnote 467
- **Description:** The footnote computes 9% × 7.8 "minutes per day" = 0.702 minutes, then divides by 180 peak-period minutes. But 7.8 is minutes per *shower*, not per day. Daily shower minutes per household would be 7.8 × 2.53 × 0.6 ≈ 11.8. Separately, ΔkW divides per-showerhead kWh (÷ 1.3 showerheads) by household shower hours (not ÷ 1.3).
- **Conflicting values or formulas:** CF = 0.09 × 7.8 / 180 = 0.0039 (as published).
- **Current implementation decision:** Use 0.0039 and the ΔkW equation exactly as published.
- **Rationale:** Published value; changing it would be an invented correction.
- **Potential impact:** Peak demand savings only; could differ by a multiple if the derivation is wrong.
- **Question for expert:** Is CF = 0.0039 correct given that 7.8 is minutes per shower? Is ΔkW = ΔkWh / Hours × CF intended to give per-showerhead savings?
- **Linked definitions:** LFSH `variables[coincidence_factor]`, `calculations[electric_savings]`
- **Linked tests:** `tests/de_v5/test_low_flow_shower_head.py::test_published_kw_example`
- **Review status:** Open
- **Reviewer:**
- **Review date:**
- **Resolution:**

### VR-023

**Water heater types not covered by the two fuel cases**

- **Measure / TRM version:** Low Flow Shower Head, DE TRM 5.0 (draft)
- **Category:** Regulatory applicability
- **Source:** p. 174 ("If electric domestic water heater"); p. 175 (recovery efficiency 0.98, footnote 466); p. 176 ("If fossil fuel domestic water heater")
- **Description:** The 0.98 recovery efficiency fits electric resistance water heaters. Heat pump water heaters are also electric but much more efficient, so applying 0.98 would overstate savings. Fossil fuel is not split by fuel (gas, propane, oil).
- **Conflicting values or formulas:** —
- **Current implementation decision:** `water_heater_fuel` has two choices: `electric` (0.98) and `fossil_fuel` (0.80). MMBtu is not split by fuel.
- **Rationale:** Matches the two cases in the TRM.
- **Potential impact:** kWh savings would be overstated for homes with heat pump water heaters.
- **Question for expert:** How should showerheads in homes with heat pump water heaters be treated? Is a fuel breakdown of MMBtu needed for reporting?
- **Linked definitions:** LFSH `variables[water_heater_fuel, electric_recovery_efficiency]`
- **Linked tests:** `tests/de_v5/test_low_flow_shower_head.py::test_fuel_type_selects_outputs`
- **Review status:** Open
- **Reviewer:**
- **Review date:**
- **Resolution:**

### VR-024

**Rounding of intermediate values**

- **Measure / TRM version:** Low Flow Shower Head, DE TRM 5.0 (draft); applies to all measures
- **Category:** Ambiguous methodology
- **Source:** p. 176 (Hours shown as 72); p. 177–178 (ΔkWhwater example uses the rounded 3.7 CCF)
- **Description:** The TRM rounds intermediate values in its examples (72.03 hours → 72; 3.704 CCF → 3.7). It gives no rounding rule.
- **Conflicting values or formulas:** —
- **Current implementation decision:** No rounding of intermediate or final values. Hours are calculated from the formula, so they change when `people_per_household` is supplied.
- **Rationale:** Rounding is a presentation choice; full precision avoids compounding error.
- **Potential impact:** Below 0.1% for defaults.
- **Question for expert:** Are there Delaware reporting rules for rounding savings? Should Hours stay fixed at 72 when the actual household size is known?
- **Linked definitions:** LFSH `variables[shower_hours_per_year]`
- **Linked tests:** `tests/de_v5/test_low_flow_shower_head.py::test_published_water_examples`, `::test_measured_flow_and_known_household_size`
- **Review status:** Open
- **Reviewer:**
- **Review date:**
- **Resolution:**

---

## General

### VR-025

**The source is a draft TRM**

- **Measure / TRM version:** All measures, DE TRM 5.0 (draft)
- **Category:** Regulatory applicability
- **Source:** Document header ("Version 5.0/July 2025"), DRAFT watermark on every page, published with the 8 April 2025 EEAC meeting materials
- **Description:** All values come from a draft. The final version may differ, and the effective date of v5.0 is not stated in the draft.
- **Conflicting values or formulas:** —
- **Current implementation decision:** Record `source.status: draft` and the URL in every measure file, and include it in each calculation result.
- **Rationale:** Makes the provisional status visible wherever results are used.
- **Potential impact:** Any value may change in the final TRM.
- **Question for expert:** Has a final v5.0 been adopted? If so, where is it published and from what date is it effective?
- **Linked definitions:** ASHP and LFSH top-level `source` and `issues`
- **Linked tests:** `tests/de_v5/test_air_source_heat_pump.py::test_provenance_of_resolved_variables`
- **Review status:** Open
- **Reviewer:**
- **Review date:**
- **Resolution:**

---

## Added after initial review

### VR-026

**Eligibility of installations with no flow reduction**

- **Measure / TRM version:** Low Flow Shower Head, DE TRM 5.0 (draft)
- **Category:** Regulatory applicability
- **Source:** p. 174 (Measure Description: low flow ≤ 2.0 GPM; Definition of Efficient Condition: "a lower GPM flow than required by code"; GPMbase: "or actual flow rate if recorded")
- **Description:** With the default 2.5 GPM baseline and the ≤ 2.0 GPM limit (VR-021), savings are always positive. With a measured baseline (VR-020), the installed flow can equal or exceed the baseline, for example a measured 1.8 GPM existing showerhead replaced by a 2.0 GPM unit. The TRM does not say whether such an installation is eligible, or whether its savings should be claimed as zero or as the negative calculated value.
- **Conflicting values or formulas:** — (the equations give zero savings when GPMlow = GPMbase and negative savings when GPMlow > GPMbase)
- **Current implementation decision:** Return the calculated result unchanged (zero or negative), together with the result warning `no_positive_water_savings` whenever `gpm_low ≥ gpm_base`. The warning includes both flow rates and references VR-020 and VR-026. The installation is not rejected and results are not clamped to zero.
- **Rationale:** Rejecting or clamping would invent an eligibility rule the TRM does not state. The warning makes the condition machine-readable for the caller.
- **Potential impact:** Programs could claim negative or zero savings, or count ineligible installations, if callers ignore the warning.
- **Question for expert:** If the installed flow rate is equal to or greater than the measured baseline, is the installation ineligible? If it is eligible, should savings be reported as zero or as the calculated negative value?
- **Linked definitions:** LFSH `warnings[no_positive_water_savings]`, `variables[gpm_base, gpm_low]`
- **Linked tests:** `tests/de_v5/test_low_flow_shower_head.py::test_equal_flow_rates_warn_and_give_zero_savings`, `::test_installed_flow_above_baseline_warns_and_keeps_negative_result`, `::test_no_warning_when_flow_is_reduced`
- **Review status:** Open
- **Reviewer:**
- **Review date:**
- **Resolution:**
