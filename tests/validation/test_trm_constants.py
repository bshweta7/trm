"""Compares the TRM values transcribed in trm_reference with the measure YAML.

The two are separate transcriptions of the same TRM pages, so a typo in either
shows up here as a mismatch (validation plan §7, step 4). On a mismatch,
check the TRM page and record the outcome in docs/validation_register.md before
changing either side; never edit one to match the other without that check.
"""

from fractions import Fraction as F

import pytest

import trm_reference as ref
from trm_engine import default_registry

ASHP = "de-res-hvac-air-source-heat-pump"
SHOWER = "de-res-water-heating-low-flow-shower-head"

# (measure, variable id, attribute) -> reference value
VARIABLES = {
    (ASHP, "seer_baseline", "value"): ref.ASHP_SEER_BASE,
    (ASHP, "hspf_baseline", "value"): ref.ASHP_HSPF_BASE,
    (ASHP, "eer_baseline", "value"): ref.ASHP_EER_BASE,
    (ASHP, "coincidence_factor_ssp", "value"): ref.ASHP_CF_SSP,
    (ASHP, "coincidence_factor_pjm", "value"): ref.ASHP_CF_PJM,
    (SHOWER, "gpm_base", "default"): ref.SHOWER_GPM_BASE_DEFAULT,
    (SHOWER, "gpm_low", "maximum"): ref.SHOWER_GPM_LOW_MAX,
    (SHOWER, "people_per_household", "default"): ref.SHOWER_PEOPLE_DEFAULT,
    (SHOWER, "shower_minutes", "value"): ref.SHOWER_MINUTES,
    (SHOWER, "showers_per_person_per_day", "value"): ref.SHOWERS_PER_PERSON,
    (SHOWER, "days_per_year", "value"): ref.DAYS_PER_YEAR,
    (SHOWER, "showerheads_per_home", "value"): ref.SHOWERHEADS_PER_HOME,
    (SHOWER, "pounds_per_gallon", "value"): ref.POUNDS_PER_GALLON,
    (SHOWER, "shower_temperature", "value"): ref.SHOWER_TEMP,
    (SHOWER, "inlet_temperature", "value"): ref.INLET_TEMP,
    (SHOWER, "electric_recovery_efficiency", "value"): ref.ELECTRIC_RECOVERY_EFF,
    (SHOWER, "fossil_recovery_efficiency", "value"): ref.FOSSIL_RECOVERY_EFF,
    (SHOWER, "btu_per_kwh", "value"): ref.BTU_PER_KWH,
    (SHOWER, "btu_per_mmbtu", "value"): ref.BTU_PER_MMBTU,
    (SHOWER, "gallons_per_ccf", "value"): ref.GALLONS_PER_CCF,
    (SHOWER, "kwh_per_ccf_water", "value"): ref.KWH_PER_CCF_WATER,
    (SHOWER, "coincidence_factor", "value"): ref.SHOWER_CF,
}

LOOKUPS = {
    (ASHP, "cooling_full_load_hours_by_location"): ref.ASHP_COOLING_HOURS,
    (ASHP, "heating_full_load_hours_by_location"): ref.ASHP_HEATING_HOURS,
}


def exact(value) -> F:
    # str() gives the shortest decimal that round-trips, i.e. the value typed in the YAML.
    return F(str(value))


def measure(measure_id):
    return default_registry().get(measure_id)


@pytest.mark.parametrize(
    "key, reference", VARIABLES.items(), ids=[f"{m.split('-')[-1]}.{v}.{a}" for m, v, a in VARIABLES]
)
def test_variable_matches_reference(key, reference):
    measure_id, variable_id, attribute = key
    yaml_value = getattr(measure(measure_id).variable(variable_id), attribute)
    assert yaml_value is not None, f"{variable_id}.{attribute} missing from YAML"
    assert exact(yaml_value) == reference, (
        f"{measure_id} {variable_id}.{attribute}: YAML {yaml_value} vs reference {float(reference)}"
    )


@pytest.mark.parametrize("key, reference", LOOKUPS.items(), ids=[t for _, t in LOOKUPS])
def test_lookup_matches_reference(key, reference):
    measure_id, table = key
    yaml_values = {k: exact(v) for k, v in measure(measure_id).lookups[table].values.items()}
    assert yaml_values == reference


@pytest.mark.parametrize("measure_id", [ASHP, SHOWER])
def test_every_yaml_constant_has_a_reference_transcription(measure_id):
    """A new deemed value, default or lookup must also be transcribed in trm_reference."""
    m = measure(measure_id)
    in_yaml = {
        (measure_id, v.id, attr)
        for v in m.variables
        for attr in ("value", "default", "maximum")
        if getattr(v, attr, None) is not None
    }
    assert in_yaml - set(VARIABLES) == set()
    assert {(measure_id, t) for t in m.lookups} == {k for k in LOOKUPS if k[0] == measure_id}


@pytest.mark.trm_issue("VR-011")
def test_a_p7_deemed_eer_baseline_is_wassmer_of_seer_baseline():
    m = measure(ASHP)
    seer = exact(m.variable("seer_baseline").value)
    assert ref.wassmer_eer(seer) == exact(m.variable("eer_baseline").value)

