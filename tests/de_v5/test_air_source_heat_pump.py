"""Delaware TRM v5 — Air Source Heat Pump, Time of Sale (pp. 71–81).

Expected values were calculated independently of the implementation (exact
rational arithmetic, shown in each test) from the TRM equations and values.
A passing test shows consistency with the chosen interpretation, not that the
interpretation is authoritative; see docs/validation_register.md.
"""

import pytest

from trm_engine import ApplicationNotImplementedError, InputValidationError, calculate
from trm_engine.measures.de_v5.air_source_heat_pump import (
    time_of_sale_energy_savings,
    time_of_sale_peak_demand_savings,
)
from trm_engine.service import ValueOrigin

MEASURE = "de-res-hvac-air-source-heat-pump"

THREE_TON_WILMINGTON = dict(
    location="wilmington_de",
    cooling_capacity_existing=36_000,
    cooling_capacity_efficient=36_000,
    heating_capacity_existing=36_000,
    heating_capacity_efficient=36_000,
    seer_efficient=16,
    hspf_efficient=9,
    eer_efficient=13,
)


def values(result):
    return {k: v.value for k, v in result.outputs.items()}


# --- Independently calculated cases using TRM defaults ----------------------


@pytest.mark.trm_issue("VR-001", "VR-003")
def test_time_of_sale_defaults_wilmington():
    # cooling = 719 x (36000/15 - 36000/16) / 1000          = 107.85
    # heating = 935 x (36000/8.8 - 36000/9) / 1000          = 85.0
    # dkW     = (36000/12.3 - 36000/13) / 1000              = 0.157598...
    # SSP     = dkW x 0.69 = 0.108742964...; PJM = dkW x 0.66 = 0.104015009...
    result = values(calculate(MEASURE, "time_of_sale", THREE_TON_WILMINGTON))
    assert result == pytest.approx(
        {
            "kwh_cooling_savings": 107.85,
            "kwh_heating_savings": 85.0,
            "kwh_savings": 192.85,
            "kw_ssp_savings": 0.10874296435272045,
            "kw_pjm_savings": 0.10401500938086304,
        },
        rel=1e-12,
    )


@pytest.mark.trm_issue("VR-001", "VR-003", "VR-009")
def test_time_of_sale_downsized_washington_dc():
    # Existing 36,000 cooling / 34,000 heating; efficient 30,000 / 29,000;
    # SEERee 18, HSPFee 10, EERee 14, Washington DC (935 cooling, 822 heating hours).
    # cooling = 935 x (36000/15 - 30000/18) / 1000          = 685.6666...
    # heating = 822 x (34000/8.8 - 29000/10) / 1000         = 792.1090...
    # dkW     = (36000/12.3 - 30000/14) / 1000              = 0.783972...
    result = values(
        calculate(
            MEASURE,
            "time_of_sale",
            dict(
                location="washington_dc",
                cooling_capacity_existing=36_000,
                cooling_capacity_efficient=30_000,
                heating_capacity_existing=34_000,
                heating_capacity_efficient=29_000,
                seer_efficient=18,
                hspf_efficient=10,
                eer_efficient=14,
            ),
        )
    )
    assert result == pytest.approx(
        {
            "kwh_cooling_savings": 685.6666666666666,
            "kwh_heating_savings": 792.1090909090909,
            "kwh_savings": 1477.7757575757576,
            "kw_ssp_savings": 0.5409407665505227,
            "kw_pjm_savings": 0.5174216027874564,
        },
        rel=1e-12,
    )


@pytest.mark.parametrize(
    ("location", "cooling_hours", "heating_hours"),
    [("wilmington_de", 719, 935), ("baltimore_md", 744, 866), ("washington_dc", 935, 822)],
)
def test_full_load_hours_lookup(location, cooling_hours, heating_hours):
    # TRM p. 74 (EFLHcool) and p. 76 (FLHheat).
    result = calculate(MEASURE, "time_of_sale", THREE_TON_WILMINGTON | {"location": location})
    assert result.variables["cooling_full_load_hours"].value == cooling_hours
    assert result.variables["heating_full_load_hours"].value == heating_hours
    assert result.variables["cooling_full_load_hours"].origin is ValueOrigin.LOOKUP


def test_baseline_at_minimum_efficiency_has_zero_savings():
    # An efficient unit at exactly the baseline ratings saves nothing.
    result = values(
        calculate(
            MEASURE,
            "time_of_sale",
            THREE_TON_WILMINGTON | dict(seer_efficient=15, hspf_efficient=8.8, eer_efficient=12.3),
        )
    )
    assert result == pytest.approx(dict.fromkeys(result, 0.0), abs=1e-12)


# --- Published TRM illustrative examples --------------------------------------
# The examples use their own inputs, which differ from the TRM defaults, so they
# test the equations directly rather than through the service.


@pytest.mark.trm_issue("VR-002")
def test_published_time_of_sale_kwh_example():
    # p. 77: 3-ton, SEER 15 / HSPF 8.5, Baltimore -> 509 kWh.
    # The example uses SEERbase 14 and HSPFbase 7.7, not the defined 15 / 8.8 (VR-002).
    result = time_of_sale_energy_savings(
        cooling_capacity_existing=36_000,
        cooling_capacity_efficient=36_000,
        heating_capacity_existing=36_000,
        heating_capacity_efficient=36_000,
        seer_baseline=14,
        seer_efficient=15,
        hspf_baseline=7.7,
        hspf_efficient=8.5,
        cooling_full_load_hours=744,
        heating_full_load_hours=866,
    )
    assert round(result["kwh_savings"]) == 509


@pytest.mark.trm_issue("VR-001")
def test_published_time_of_sale_kw_example():
    # p. 79: 3-ton EER 11.8 replaced by 2-ton EER 12.5 -> dkW_SSP = 0.78 kW.
    result = time_of_sale_peak_demand_savings(
        cooling_capacity_existing=36_000,
        cooling_capacity_efficient=24_000,
        eer_baseline=11.8,
        eer_efficient=12.5,
        coincidence_factor_ssp=0.69,
        coincidence_factor_pjm=0.66,
    )
    assert round(result["kw_ssp_savings"], 2) == 0.78


@pytest.mark.trm_issue("VR-001")
@pytest.mark.parametrize(("eer_existing", "published_kw"), [(9.9, 1.18), (11.8, 0.78)])
def test_published_early_replacement_kw_examples_confirm_cf_multiplication(eer_existing, published_kw):
    # p. 80: the Early Replacement kW examples use the same structure as Time of
    # Sale with a different baseline EER, so they also exercise the CF handling.
    # Dividing by CF instead would give 2.49 and 1.64 kW.
    result = time_of_sale_peak_demand_savings(
        cooling_capacity_existing=36_000,
        cooling_capacity_efficient=24_000,
        eer_baseline=eer_existing,
        eer_efficient=12.5,
        coincidence_factor_ssp=0.69,
        coincidence_factor_pjm=0.66,
    )
    assert round(result["kw_ssp_savings"], 2) == published_kw


# --- Provenance, applications, and validation ---------------------------------


@pytest.mark.trm_issue("VR-001")
def test_peak_demand_outputs_are_flagged_as_interpretation():
    result = calculate(MEASURE, "time_of_sale", THREE_TON_WILMINGTON)
    for output_id in ("kw_ssp_savings", "kw_pjm_savings"):
        assert result.outputs[output_id].interpretation
        assert "VR-001" in result.outputs[output_id].issues
    assert result.outputs["kwh_savings"].interpretation is None


@pytest.mark.trm_issue("VR-008")
def test_eligibility_warning_is_returned_without_changing_results():
    result = calculate(MEASURE, "time_of_sale", THREE_TON_WILMINGTON)
    [warning] = result.warnings
    assert warning.code == "efficient_equipment_eligibility_not_verified"
    assert warning.issues == ["VR-008"]
    assert warning.variables == {}
    # Same values as test_time_of_sale_defaults_wilmington.
    assert values(result) == pytest.approx(
        {
            "kwh_cooling_savings": 107.85,
            "kwh_heating_savings": 85.0,
            "kwh_savings": 192.85,
            "kw_ssp_savings": 0.10874296435272045,
            "kw_pjm_savings": 0.10401500938086304,
        },
        rel=1e-12,
    )


@pytest.mark.trm_issue("VR-008")
def test_eligibility_warning_does_not_reject_low_efficiency_equipment():
    # A unit below the baseline is still calculated (negative savings) and warned about.
    result = calculate(MEASURE, "time_of_sale", THREE_TON_WILMINGTON | {"seer_efficient": 14})
    assert result.outputs["kwh_cooling_savings"].value < 0
    assert [w.code for w in result.warnings] == ["efficient_equipment_eligibility_not_verified"]


def test_provenance_of_resolved_variables():
    result = calculate(MEASURE, "time_of_sale", THREE_TON_WILMINGTON)
    seer = result.variables["seer_baseline"]
    assert (seer.value, seer.origin, seer.citation.page) == (15, ValueOrigin.DEEMED, 75)
    assert result.variables["seer_efficient"].origin is ValueOrigin.USER_INPUT
    assert result.variables["heating_full_load_hours"].citation.page == 76
    assert result.measure_code == "RS_HV_TOS_ASHP_0518"
    assert result.source_document.status == "draft"
    assert result.status.human_reviewed is False


def test_early_replacement_is_not_implemented():
    with pytest.raises(ApplicationNotImplementedError):
        calculate(MEASURE, "early_replacement", THREE_TON_WILMINGTON)


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"location": "dover_de"}, "location"),
        ({"seer_efficient": 0}, "seer_efficient"),
        ({"cooling_capacity_efficient": -12_000}, "cooling_capacity_efficient"),
        ({"eer_efficient": "13"}, "eer_efficient"),
        ({"seer_baseline": 14}, "seer_baseline"),  # deemed values cannot be overridden
    ],
)
def test_invalid_inputs_are_rejected(change, message):
    with pytest.raises(InputValidationError, match=message):
        calculate(MEASURE, "time_of_sale", THREE_TON_WILMINGTON | change)


def test_missing_required_input_is_rejected():
    inputs = dict(THREE_TON_WILMINGTON)
    del inputs["hspf_efficient"]
    with pytest.raises(InputValidationError, match="hspf_efficient"):
        calculate(MEASURE, "time_of_sale", inputs)
