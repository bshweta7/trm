"""Engine-free reference calculator for the Delaware TRM v5 measures.

Expected values for validation tests come from here, not from the engine (see
docs/validation_plan.md, §1 and §7). Every TRM value is transcribed separately
from the measure YAML, with its page reference, and every formula is written
from the TRM equations in exact rational arithmetic.

This module must never import trm_engine; tests/validation/test_trm_reference.py
enforces that. Issue IDs (VR-###) refer to docs/validation_register.md.
"""

from fractions import Fraction as F

# --- Air Source Heat Pump, Time of Sale (pp. 71–81) -------------------------

ASHP_SEER_BASE = F(15)  # p. 75, fn 195; VR-003, VR-004
ASHP_HSPF_BASE = F("8.8")  # p. 76, fn 200; VR-003, VR-004
ASHP_EER_BASE = F("12.3")  # p. 78, fn 203; VR-011
ASHP_CF_SSP = F("0.69")  # p. 79, fn 206
ASHP_CF_PJM = F("0.66")  # p. 79, fn 207

ASHP_COOLING_HOURS = {  # EFLHcool, p. 74, fn 193
    "wilmington_de": F(719),
    "baltimore_md": F(744),
    "washington_dc": F(935),
}
ASHP_HEATING_HOURS = {  # FLHheat, p. 76, fn 198; VR-007
    "wilmington_de": F(935),
    "baltimore_md": F(866),
    "washington_dc": F(822),
}


def wassmer_eer(seer) -> F:
    """EER approximated from SEER: −0.02 × SEER² + 1.12 × SEER (p. 71 fn 190; VR-011)."""
    seer = F(seer)
    return F("-0.02") * seer**2 + F("1.12") * seer


def ashp_cooling_kwh(eflh, cap_exist, seer_base, cap_ee, seer_ee) -> F:
    """EFLHcool × (BTUHCexist/SEERbase − BTUHCee/SEERee) / 1000 (p. 73)."""
    return F(eflh) * (F(cap_exist) / F(seer_base) - F(cap_ee) / F(seer_ee)) / 1000


def ashp_heating_kwh(flh, cap_exist, hspf_base, cap_ee, hspf_ee) -> F:
    """EFLHheat × (BTUHHexist/HSPFbase − BTUHHee/HSPFee) / 1000 (p. 73)."""
    return F(flh) * (F(cap_exist) / F(hspf_base) - F(cap_ee) / F(hspf_ee)) / 1000


def ashp_connected_kw(cap_exist, eer_base, cap_ee, eer_ee) -> F:
    """(BTUHCexist/EERbase − BTUHCee/EERee) / 1000, before CF (p. 78)."""
    return (F(cap_exist) / F(eer_base) - F(cap_ee) / F(eer_ee)) / 1000


def ashp_time_of_sale(
    *,
    location,
    cooling_capacity_existing,
    cooling_capacity_efficient,
    heating_capacity_existing,
    heating_capacity_efficient,
    seer_efficient,
    hspf_efficient,
    eer_efficient,
) -> dict[str, F]:
    """All five Time of Sale outputs, keyed like the engine's outputs.

    Peak kW multiplies by CF, following the worked examples (VR-001).
    """
    cooling = ashp_cooling_kwh(
        ASHP_COOLING_HOURS[location],
        cooling_capacity_existing, ASHP_SEER_BASE,
        cooling_capacity_efficient, seer_efficient,
    )
    heating = ashp_heating_kwh(
        ASHP_HEATING_HOURS[location],
        heating_capacity_existing, ASHP_HSPF_BASE,
        heating_capacity_efficient, hspf_efficient,
    )
    kw = ashp_connected_kw(
        cooling_capacity_existing, ASHP_EER_BASE, cooling_capacity_efficient, eer_efficient
    )
    return {
        "kwh_cooling_savings": cooling,
        "kwh_heating_savings": heating,
        "kwh_savings": cooling + heating,
        "kw_ssp_savings": kw * ASHP_CF_SSP,
        "kw_pjm_savings": kw * ASHP_CF_PJM,
    }


# --- Low Flow Shower Head (pp. 174–178) -------------------------------------

SHOWER_GPM_LOW_MAX = F("2.0")  # p. 174, measure description "low flow (≤2.0 GPM)"; VR-021
SHOWER_GPM_BASE_DEFAULT = F("2.5")  # p. 174, fn 460
SHOWER_PEOPLE_DEFAULT = F("2.53")  # p. 175, fn 461
SHOWER_MINUTES = F("7.8")  # p. 175, fn 462
SHOWERS_PER_PERSON = F("0.6")  # p. 175, fn 463; VR-015
DAYS_PER_YEAR = F(365)  # p. 175
SHOWERHEADS_PER_HOME = F("1.3")  # p. 175, fn 464
POUNDS_PER_GALLON = F("8.3")  # p. 175
SHOWER_TEMP = F(105)  # p. 175, no footnote; VR-018
INLET_TEMP = F("60.9")  # p. 175, fn 465
ELECTRIC_RECOVERY_EFF = F("0.98")  # p. 175, fn 466
FOSSIL_RECOVERY_EFF = F("0.80")  # pp. 176–177, fn 468; VR-016
BTU_PER_KWH = F(3412)  # p. 175
BTU_PER_MMBTU = F(10**6)  # p. 176
GALLONS_PER_CCF = F(748)  # p. 177
KWH_PER_CCF_WATER = F("2.07")  # p. 177, no footnote; VR-019
SHOWER_CF = F("0.0039")  # p. 176, fn 467; VR-022


def shower_gallons(gpm_base, gpm_low, people) -> F:
    """(GPMbase − GPMlow) × TimeShower × # people × ShowersPerson × days / ShowerHeads/home."""
    return (
        (F(gpm_base) - F(gpm_low)) * SHOWER_MINUTES * F(people) * SHOWERS_PER_PERSON
        * DAYS_PER_YEAR / SHOWERHEADS_PER_HOME
    )


def shower_hours(people) -> F:
    """TimeShower × # people × ShowersPerson / 60 × days (p. 176)."""
    return SHOWER_MINUTES * F(people) * SHOWERS_PER_PERSON / 60 * DAYS_PER_YEAR


def low_flow_shower_head(
    *,
    water_heater_fuel,
    gpm_low,
    gpm_base=SHOWER_GPM_BASE_DEFAULT,
    people_per_household=SHOWER_PEOPLE_DEFAULT,
) -> dict[str, F]:
    """Outputs for one fuel, keyed like the engine's outputs (VR-023)."""
    gallons = shower_gallons(gpm_base, gpm_low, people_per_household)
    heat_btu = gallons * POUNDS_PER_GALLON * (SHOWER_TEMP - INLET_TEMP)
    ccf = gallons / GALLONS_PER_CCF
    outputs = {"water_savings_ccf": ccf, "kwh_water_savings": KWH_PER_CCF_WATER * ccf}
    if water_heater_fuel == "electric":
        kwh = heat_btu / ELECTRIC_RECOVERY_EFF / BTU_PER_KWH
        outputs["kwh_savings"] = kwh
        outputs["kw_savings"] = kwh / shower_hours(people_per_household) * SHOWER_CF
    elif water_heater_fuel == "fossil_fuel":
        outputs["mmbtu_savings"] = heat_btu / FOSSIL_RECOVERY_EFF / BTU_PER_MMBTU
    else:
        raise ValueError(f"unknown water_heater_fuel: {water_heater_fuel!r}")
    return outputs
