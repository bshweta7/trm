"""Delaware TRM v5 — Low Flow Shower Head (pp. 174–178).

Deterministic implementations only; every value arrives as an argument already
resolved by the service layer. Argument names match variable ids in
trm/de/v5/residential/water_heating/low_flow_shower_head.yaml.
"""


def water_saved_gallons(
    gpm_base: float,
    gpm_low: float,
    shower_minutes: float,
    people_per_household: float,
    showers_per_person_per_day: float,
    days_per_year: float,
    showerheads_per_home: float,
) -> float:
    """Annual gallons saved per showerhead: the bracketed term shared by every algorithm."""
    return (
        (gpm_base - gpm_low)
        * shower_minutes
        * people_per_household
        * showers_per_person_per_day
        * days_per_year
        / showerheads_per_home
    )


def shower_hours_per_year(
    shower_minutes: float,
    people_per_household: float,
    showers_per_person_per_day: float,
    days_per_year: float,
) -> float:
    """Hours per year spent using the shower head, p. 176."""
    return shower_minutes * people_per_household * showers_per_person_per_day / 60 * days_per_year


def electric_savings(
    water_saved_gallons: float,
    pounds_per_gallon: float,
    shower_temperature: float,
    inlet_temperature: float,
    electric_recovery_efficiency: float,
    btu_per_kwh: float,
    shower_hours_per_year: float,
    coincidence_factor: float,
) -> dict[str, float]:
    """Electric water heater energy (p. 174) and peak demand (p. 176) savings."""
    kwh = (
        water_saved_gallons
        * pounds_per_gallon
        * (shower_temperature - inlet_temperature)
        / electric_recovery_efficiency
        / btu_per_kwh
    )
    return {
        "kwh_savings": kwh,
        "kw_savings": kwh / shower_hours_per_year * coincidence_factor,
    }


def fossil_fuel_savings(
    water_saved_gallons: float,
    pounds_per_gallon: float,
    shower_temperature: float,
    inlet_temperature: float,
    fossil_recovery_efficiency: float,
    btu_per_mmbtu: float,
) -> dict[str, float]:
    """Fossil fuel water heater energy savings, p. 176."""
    return {
        "mmbtu_savings": (
            water_saved_gallons
            * pounds_per_gallon
            * (shower_temperature - inlet_temperature)
            / fossil_recovery_efficiency
            / btu_per_mmbtu
        )
    }


def water_savings(
    water_saved_gallons: float,
    gallons_per_ccf: float,
    kwh_per_ccf_water: float,
) -> dict[str, float]:
    """Water savings and associated pumping/treatment kWh, p. 177."""
    ccf = water_saved_gallons / gallons_per_ccf
    return {
        "water_savings_ccf": ccf,
        "kwh_water_savings": kwh_per_ccf_water * ccf,
    }


def installed_flow_not_below_baseline(gpm_base: float, gpm_low: float) -> bool:
    """True when the installed showerhead does not reduce the flow rate (VR-026)."""
    return gpm_low >= gpm_base


FUNCTIONS = {
    "water_saved_gallons": water_saved_gallons,
    "shower_hours_per_year": shower_hours_per_year,
    "electric_savings": electric_savings,
    "fossil_fuel_savings": fossil_fuel_savings,
    "water_savings": water_savings,
    "installed_flow_not_below_baseline": installed_flow_not_below_baseline,
}
