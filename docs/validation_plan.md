# Validation Plan and Matrix — Delaware TRM v5 Measures

A plan for systematically validating the two implemented measures, and a
matrix of reference cases with independently derived expected values.

**Status:** in progress. The engine-free reference calculator (§7 step 2)
the engine tests for the §6 gaps (step 3) and the check of transcribed TRM
values against the measure YAML (step 4) exist. No discrepancies or
transcription mismatches were found, and no calculation code was modified.

## 1. Principles

1. **Expected values never come from the engine.** Every expected value below
   comes from one of:
   - **Published:** a worked example printed in the TRM, with the example's own
     inputs.
   - **Independent:** arithmetic done separately from the engine. Each value
     was computed with exact rational arithmetic (Python `fractions`) in a
     standalone script written from the TRM equations, which does not import
     `trm_engine`. The arithmetic is shown in each row so it can be checked by
     hand.
   - **Property:** a mathematical consequence of the TRM equations (zero
     savings, scaling, ratios), which holds whatever the engine computes.
2. **Discrepancies are recorded, not fixed.** Where the TRM is inconsistent,
   the case states both values and links the validation-register issue. The
   implementation follows the decision recorded there. A passing test shows
   consistency with that decision, not that the decision is correct.
3. **Tolerances**

   | Source | Tolerance | Reason |
   |---|---|---|
   | Independent | relative 1e‑12 | Exact rational value vs. floating point; allows rounding error only |
   | Property (equalities) | relative 1e‑12, or exact where the computation is identical | — |
   | Zero-savings cases | absolute 1e‑12 | — |
   | Published | half a unit of the last printed digit (e.g. 509 → ±0.5; 0.78 → ±0.005) | The TRM rounds its printed results |

4. **TRM source:** Delaware TRM v5.0, **draft** (VR-025). Page numbers are
   printed page numbers, which match the PDF.

## 2. Audit of existing tests

The measure tests are in `tests/de_v5/`. Engine and UI tests use a synthetic
fixture or check presentation, so they aren't calculation validation and are
left out here.

| Area | Tests | Assessment |
|---|---|---|
| ASHP independent cases | `test_time_of_sale_defaults_wilmington`, `test_time_of_sale_downsized_washington_dc` | Good. Exact values derived independently; all 5 outputs checked. |
| ASHP published examples | `test_published_time_of_sale_kwh_example`, `test_published_time_of_sale_kw_example`, `test_published_early_replacement_kw_examples_confirm_cf_multiplication` | Good, but they call the equation function directly with the example's inputs, so they check equations, not the TRM defaults or lookups. The ER kWh examples (pp. 77–78) aren't covered. |
| ASHP properties and boundaries | `test_baseline_at_minimum_efficiency_has_zero_savings`, `test_eligibility_warning_does_not_reject_low_efficiency_equipment`, `test_invalid_inputs_are_rejected`, `test_missing_required_input_is_rejected` | Zero savings covered. The below-baseline case checks only the sign of the result. No scaling or ratio properties. |
| ASHP location | `test_full_load_hours_lookup` (3 locations) | Checks the looked-up hours only. Full results are checked for Wilmington and DC, **not Baltimore**. |
| Shower independent cases | `test_electric_defaults` (both applications), `test_fossil_fuel_defaults`, `test_measured_flow_and_known_household_size` | Good. The measured-flow case is electric only, with no fossil-fuel variant. Only the 2.0 GPM default case is covered. |
| Shower published examples | `test_published_kwh_example_uses_inputs_inconsistent_with_defaults`, `test_published_mmbtu_example_requires_unstated_efficiency`, `test_published_water_examples`, `test_published_hours`, `test_published_kw_example` | Good documentation of VR-015/VR-016. `test_published_kw_example` only repeats the TRM's arithmetic (276 / 72 × 0.0039) plus the hours function; it doesn't run the kW equation. |
| Shower zero/negative | `test_equal_flow_rates_warn_and_give_zero_savings`, `test_installed_flow_above_baseline_warns_and_keeps_negative_result` (both fuels) | Good. Exact values derived independently. |
| Shower boundaries and fuel | `test_eligibility_maximum_flow_rate`, `test_no_warning_when_flow_is_reduced`, `test_fuel_type_selects_outputs`, `test_invalid_inputs_are_rejected` | Good. |
| Shower properties | — | None (linearity, invariance to household size). |

Other observations:

- The expected values in the existing tests were derived independently (exact
  arithmetic, with the working in comments). None were copied from engine
  output; every expected value in the matrix below was recomputed for this
  plan and matches the existing tests.
- The derivations exist only as comments. There is no reusable, engine-free
  reference calculator, so each new case must be derived by hand.
- No test checks that the TRM values used for expected answers (baselines,
  hours, constants) match the TRM text. They are re-typed in each test.

## 3. Validation matrix — Air Source Heat Pump, Time of Sale (pp. 71–81)

Common to all rows: SEERbase 15, HSPFbase 8.8, EERbase 12.3 (VR-003, VR-004),
CFSSP 0.69, CFPJM 0.66 (p. 79), and peak kW **multiplied** by CF (VR-001).
Capacities in Btu/hr; ratings on the SEER/HSPF/EER basis. ΔkW below means the
reduction in connected demand before CF: (BTUHCexist/EERbase − BTUHCee/EERee)/1000.

### 3.1 Published worked examples

| ID | Inputs (as printed) | Expected | TRM ref | Tolerance | Discrepancies | Automated |
|---|---|---|---|---|---|---|
| A-P1 | TOS kWh, Baltimore (744 / 866 h), 36,000 Btu/hr both units and modes, SEERee 15, HSPFee 8.5, **SEERbase 14, HSPFbase 7.7** | **509 kWh** (exact 508.609) | p. 77 | ±0.5 | VR-002: the defined baselines (15 / 8.8) give **−125.04 kWh** for the same unit | Yes (equation only) |
| A-P2 | TOS kW SSP, 36,000 → 24,000, EERbase 11.8, EERee 12.5, CF 0.69 | **0.78 kW** (exact 0.780285) | p. 79 | ±0.005 | VR-001: the printed form (÷ CF) would give 1.639 kW | Yes |
| A-P3 | ER kW, remaining life, EERexist 9.9, 36,000 → 24,000, EERee 12.5 | **1.18 kW** (exact 1.184291) | p. 80 | ±0.005 | VR-001; ER not implemented (VR-010) | Yes (TOS equation, same form) |
| A-P4 | ER kW, end of life, EERbasereplace 11.8 | **0.78 kW** | p. 80 | ±0.005 | VR-001, VR-010 | Yes (same as A-P2) |
| A-P5 | ER kWh, remaining life, Baltimore, SEERexist 11, HSPFexist 3.41, 36,000 → 24,000 (both modes), SEERee 15, HSPFee 8.5 | **7,942 kWh** (exact 7,941.855) | p. 77 | ±0.5 | ER not implemented; same equation form as TOS | Yes (equation only) |
| A-P6 | ER kWh, end of life as printed: SEERbasereplace **14**, HSPFbasereplace 3.41 | **7,420 kWh** (exact 7,420.088) | pp. 77–78 | ±0.5 | **VR-010**: the table value SEERbasereplace 15 gives **7,292.55 kWh** | **Gap** |
| A-P7 | Wassmer EER from SEER: −0.02·SEER² + 1.12·SEER | SEER 15 → **12.3** (EERbase); SEER 14 → **11.76 ≈ 11.8** | p. 71 fn 190, p. 78 fn 203 | exact / ±0.05 | VR-011 (SEER² notation) | Yes (deemed EERbase in YAML) |

A-P5 to A-P7 can only check the equation form, because Early Replacement isn't
implemented. A-P6 needs an expert decision first (see §5).

### 3.2 Independently calculated reference cases

| ID | Inputs | Expected (kWh cooling / heating / total; kW SSP / PJM) | Arithmetic | Automated |
|---|---|---|---|---|
| A-I1 | Wilmington; 36,000 all capacities; SEERee 16, HSPFee 9, EERee 13 | 107.85 / 85.0 / **192.85**; **0.1087429644** / 0.1040150094 | 719×(36000/15−36000/16)/1000; 935×(36000/8.8−36000/9)/1000; ΔkW (36000/12.3−36000/13)/1000 = 0.157598 | Yes |
| A-I2 | DC; cooling 36,000 → 30,000; heating 34,000 → 29,000; 18 / 10 / 14 | 685.6667 / 792.1091 / **1,477.7758**; **0.5409407666** / 0.5174216028 | 935×(36000/15−30000/18)/1000; 822×(34000/8.8−29000/10)/1000; ΔkW 0.783972 | Yes |
| A-I3 | **Baltimore**; cooling 42,000 → 36,000; heating 40,000 → 35,000; 17 / 9.5 / 13 | 507.6706 / 745.8373 / **1,253.5079**; **0.4453283302** / 0.4259662289 | 744×(42000/15−36000/17)/1000; 866×(40000/8.8−35000/9.5)/1000; ΔkW (42000/12.3−36000/13)/1000 = 0.645403 | Yes |

### 3.3 Zero-savings, boundary and property cases

| ID | Case | Expected | Source | Automated |
|---|---|---|---|---|
| A-Z1 | Equal capacities, efficient ratings = baseline (15 / 8.8 / 12.3) | All 5 outputs = 0 | Property | Yes |
| A-M2 | A-I1 with SEERee **14** (below baseline) | cooling **−123.2571**, heating 85.0, total **−38.2571**; kW unchanged from A-I1; eligibility warning present | Independent: 719×(36000/15−36000/14)/1000 | Yes |
| A-M3 | A-I1 with every capacity doubled (72,000) | Every output exactly 2× A-I1 (215.7 / 170.0 / 385.7; 0.2174859287 / 0.2080300188) | Property (linear in capacity) | Yes |
| A-M4 | Any case | kW PJM / kW SSP = 0.66 / 0.69 = 22/23 exactly | Property | Yes |
| A-M5 | Any case | kWh total = cooling + heating | Property | Implied by A-I1/A-I2 |
| A-L1 | Each location with A-I1 equipment | Wilmington 192.85; Baltimore 744×0.15 + 866×(36000/8.8−4000)/1000 = **111.6 + 78.7273 = 190.3273**; DC 935×0.15 + 822×0.0909091 = **140.25 + 74.7273 = 214.9773** kWh | Independent | Yes |
| A-B1 | Ratings 0, negative capacity, text instead of number, unknown location, override of a deemed value, missing input | Rejected with a per-field error | Engine input contract (not TRM) | Yes |
| A-B2 | Efficient capacity **larger** than existing (upsizing) | Calculated (cooling savings may be negative); no TRM rule | Property; VR-005 | **Gap**; flag for expert (§5) |

## 4. Validation matrix — Low Flow Shower Head (pp. 174–178)

Defaults (pp. 174–177): GPMbase 2.5, # people 2.53, TimeShower 7.8,
ShowersPerson 0.6, days 365, ShowerHeads/home 1.3, 8.3 lb/gal, TEMPsh 105 °F
(VR-018), TEMPin 60.9 °F, recovery efficiency 0.98 electric / 0.80 gas
(VR-016), 3,412 Btu/kWh, 10⁶ Btu/MMBtu, 748 gal/CCF, 2.07 kWh/CCF (VR-019),
CF 0.0039 (VR-022).

Shorthand: **G** = (GPMbase − GPMlow) × 7.8 × people × 0.6 × 365 / 1.3
(gallons/year); **H** = 7.8 × people × 0.6 / 60 × 365 (hours/year).
kWh = G×8.3×(105−60.9)/0.98/3412; kW = kWh/H×0.0039;
MMBtu = G×8.3×44.1/0.80/10⁶; CCF = G/748; kWh_water = 2.07×CCF.

### 4.1 Published worked examples (2.0 GPM unit)

| ID | Quantity | Published | Reproduced with the example's own inputs | With the defined equation and defaults | TRM ref | Tol. | Discrepancy | Automated |
|---|---|---|---|---|---|---|---|---|
| S-P1 | ΔkWh | **276** | 275.754 (no ShowersPerson, 101 °F) | 181.956 | p. 175 | ±0.5 | VR-015 | Yes |
| S-P2 | ΔkW | **0.015** | 276 / 72 × 0.0039 = 0.01495. The example mixes kWh *without* ShowersPerson with Hours *with* it; consistent inputs would give 0.00896 (no SPP) or 0.00985 (defaults) | 0.009852 | p. 176 | ±0.0005 | VR-015, VR-022 | Partial (arithmetic only) |
| S-P3 | Hours | **72** | 72.0291 | 72.0291 | p. 176 | ±0.5 | — | Yes |
| S-P4 | ΔMMBtu | **1.23** | 1.2294 only with efficiency **0.75**; with the printed 0.80 → 1.1526 | 0.7605 | p. 177 | ±0.005 | VR-015, VR-016 | Yes |
| S-P5 | Water | **3.7 CCF** | 3.7037 | 2.2222 | p. 177 | ±0.05 | VR-015 | Yes |
| S-P6 | ΔkWh_water | **7.7** | 2.07 × 3.7 = 7.659 (rounded CCF) or 7.6666 (unrounded) | 4.6000 | pp. 177–178 | ±0.05 | VR-015, VR-019, VR-024 | Yes |

### 4.2 Independently calculated reference cases

| ID | Application, inputs | G (gal) | Expected | Automated |
|---|---|---|---|---|
| S-I1e | DI and TOS, electric, GPMlow 2.0, defaults | 1,662.21 | kWh **181.9564581**, kW **0.009851992966**, CCF 2.222205882, kWh_water 4.599966176 | Yes |
| S-I1g | DI, fossil fuel, GPMlow 2.0, defaults | 1,662.21 | MMBtu **0.760523407875**, CCF 2.222205882, kWh_water 4.599966176 | Yes |
| S-I2e | Electric, GPMlow **1.5**, defaults | 3,324.42 | kWh **363.9129162**, kW 0.01970398593, CCF 4.444411765, kWh_water 9.199932353 | Yes |
| S-I2g | Fossil fuel, GPMlow 1.5, defaults | 3,324.42 | MMBtu **1.52104681575** | Yes |
| S-I3e | DI, electric, GPMbase 2.8 (measured), GPMlow 1.5, 4 people | 6,832.8 | kWh **747.963306**, H 113.88, kW 0.02561518171, CCF 9.134759358, kWh_water 18.90895187 | Yes |
| S-I3g | Same, **fossil fuel** | 6,832.8 | MMBtu **3.12626223** | Yes |

### 4.3 Zero-savings, boundary, fuel and property cases

| ID | Case | Expected | Source | VR | Automated |
|---|---|---|---|---|---|
| S-Z1 | GPMbase 2.0 = GPMlow 2.0 | All outputs 0; warning `no_positive_water_savings` | Property | VR-020, VR-026 | Yes |
| S-Z2 | GPMbase 1.8 < GPMlow 2.0 (both fuels) | G −664.884; kWh −72.78258324; kW −0.003940797186; MMBtu −0.30420936315; CCF −0.8888823529; kWh_water −1.839986471; warning | Independent | VR-020, VR-026 | Yes |
| S-B1 | GPMlow 2.0 accepted; 2.01 rejected | — | TRM eligibility (≤ 2.0 GPM, p. 174) | VR-021 | Yes |
| S-B2 | GPMbase 2.0, GPMlow 1.99 | Positive savings; no warning | Property | — | Yes |
| S-B3 | GPMlow 0, people 0, text instead of number, NaN, override of a deemed value | Rejected | Engine input contract | — | Yes |
| S-F1 | Electric → kWh, kW, CCF, kWh_water; fossil → MMBtu, CCF, kWh_water | Outputs for the other fuel omitted, not zero | TRM pp. 174, 176 | VR-023 | Yes |
| S-M1 | Same flows, **4 people** vs 2.53 | kWh scales by 4/2.53 (287.678 vs 181.956), but **kW is identical** (0.009851992966) because people cancels in kWh/Hours | Property | **VR-022** | Yes (records current behaviour); flag for expert (§5) |
| S-M2 | GPMlow 1.5 vs 2.0 at GPMbase 2.5 | Every output exactly 2× (S-I2 = 2 × S-I1) | Property (linear in GPMbase − GPMlow) | — | Yes |
| S-M3 | Any case | kWh_water = 2.07 × CCF; kW = kWh / H × 0.0039 | Property | VR-019 | Implied by S-I cases |

## 5. Ambiguous cases for expert review

These have no single defensible expected value. They shouldn't be turned into
pass/fail tests, or used to justify changing formulas, until an expert decides.

| ID | Case | Values at stake | VR |
|---|---|---|---|
| X-1 | Peak kW: multiply or divide by CF | A-P2: 0.780 vs 1.639 kW | VR-001 |
| X-2 | Which Time of Sale baseline: variable definitions (15 / 8.8 / 12.3), p. 71 (14 / 8.2 / 11.8), or p. 72 SEER2 (14.3 / 7.5 / 11.9) | A-P1 unit: −125.04 kWh total with the current baselines (0 cooling, −125.04 heating) vs **+261.73 kWh** with the p. 71 values (127.54 cooling + 134.19 heating) | VR-002, VR-003 |
| X-3 | Equipment rated in SEER2/HSPF2/EER2 | No conversion is defined; mixing rating bases understates savings | VR-004 |
| X-4 | ER end-of-life SEERbasereplace: 14 (example) or 15 (table) | A-P6: 7,420 vs 7,292.55 kWh | VR-010 |
| X-5 | Upsized or new-construction ASHP (no existing unit) | No defined baseline capacity | VR-005, VR-009 |
| X-6 | Kent and Sussex county locations | No full-load hours published | VR-013 |
| X-7 | Shower examples vs defined defaults | 276 vs 182 kWh; 1.23 vs 0.76 MMBtu | VR-015, VR-016, VR-018 |
| X-8 | Shower peak kW doesn't depend on household size | S-M1 | VR-022 |
| X-9 | Measured baseline ≤ installed flow: eligible? zero or negative savings? | S-Z1, S-Z2 | VR-020, VR-026 |
| X-10 | Single deemed savings value per showerhead (footnote 459) | Not published | VR-017 |

## 6. Coverage gaps, in priority order

Items 1–4 and 6, and the A-P5 part of item 5, are covered by
`tests/validation/test_engine_gaps.py` (§7 step 3); A-P7 by
`tests/validation/test_trm_constants.py` (step 4).

1. **A-I3, A-L1:** full Baltimore results, and all three locations with the same equipment.
2. **A-M2:** exact values for the below-baseline case (currently only the sign is checked).
3. **S-I2, S-I3g:** shower 1.5 GPM (both fuels) and the measured-flow fossil-fuel case.
4. **A-M3, A-M4, S-M2:** scaling and ratio properties.
5. **A-P5, A-P7:** the ER kWh remaining-life example and the Wassmer EER check, as equation-form checks.
6. **S-M1:** the household-size invariance of kW, recorded as a property test that references VR-022. It shows current behaviour without endorsing it.
7. **Expert-dependent:** A-P6, A-B2. Add them only after the related issues are resolved.

## 7. Proposed next steps

1. Review this plan, and send the §5 items to an energy efficiency expert
   together with the validation register.
2. **Done:** `tests/validation/trm_reference.py`, checked by
   `tests/validation/test_trm_reference.py`. Add an engine-free reference module under `tests/validation/`. It would
   hold the TRM values (each with a page reference) and the exact-arithmetic
   formulas, so every expected value is reproducible. A check would enforce
   that it never imports `trm_engine`.
3. **Done:** `tests/validation/test_engine_gaps.py`. Add data-driven tests for the gaps in §6, one parametrized case per matrix
   row, keyed by matrix ID and linked to VR IDs with `@pytest.mark.trm_issue`.
4. **Done:** `tests/validation/test_trm_constants.py`, which also requires
   every deemed value, default, limit and lookup in the YAML to have a
   transcription. Add a test that checks each TRM value in the reference module against the
   corresponding value in the measure YAML. This is a second, independent
   transcription, so a typo in either would be caught.
5. Keep this matrix updated as measures and expert decisions change.
