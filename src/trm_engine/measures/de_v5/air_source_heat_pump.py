"""Delaware TRM v5 — Split System Air Source Heat Pump (pp. 71–81).

Deterministic implementations only; every value arrives as an argument already
resolved by the service layer. Argument names match variable ids in
trm/de/v5/residential/hvac/air_source_heat_pump.yaml.
"""


def time_of_sale_energy_savings(
    cooling_capacity_existing: float,
    cooling_capacity_efficient: float,
    heating_capacity_existing: float,
    heating_capacity_efficient: float,
    seer_baseline: float,
    seer_efficient: float,
    hspf_baseline: float,
    hspf_efficient: float,
    cooling_full_load_hours: float,
    heating_full_load_hours: float,
) -> dict[str, float]:
    """Time of Sale annual energy savings, p. 73."""
    kwh_cooling = (
        cooling_full_load_hours
        * (cooling_capacity_existing / seer_baseline - cooling_capacity_efficient / seer_efficient)
        / 1000
    )
    kwh_heating = (
        heating_full_load_hours
        * (heating_capacity_existing / hspf_baseline - heating_capacity_efficient / hspf_efficient)
        / 1000
    )
    return {
        "kwh_cooling_savings": kwh_cooling,
        "kwh_heating_savings": kwh_heating,
        "kwh_savings": kwh_cooling + kwh_heating,
    }


def time_of_sale_peak_demand_savings(
    cooling_capacity_existing: float,
    cooling_capacity_efficient: float,
    eer_baseline: float,
    eer_efficient: float,
    coincidence_factor_ssp: float,
    coincidence_factor_pjm: float,
) -> dict[str, float]:
    """Time of Sale summer coincident peak kW savings, p. 78.

    Multiplies by CF, following all three worked examples on pp. 79–80. The printed
    equation divides by (1000 x CF); see VR-001.
    """
    delta_kw = (
        cooling_capacity_existing / eer_baseline - cooling_capacity_efficient / eer_efficient
    ) / 1000
    return {
        "kw_ssp_savings": delta_kw * coincidence_factor_ssp,
        "kw_pjm_savings": delta_kw * coincidence_factor_pjm,
    }


FUNCTIONS = {
    "time_of_sale_energy_savings": time_of_sale_energy_savings,
    "time_of_sale_peak_demand_savings": time_of_sale_peak_demand_savings,
}
