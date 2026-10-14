"""Explicit map from measure id to its Python implementation functions.

Measure YAML names functions; it never names modules. Only functions listed
here can be invoked, so reference data cannot cause arbitrary code to run.
"""

from collections.abc import Callable

from trm_engine.measures.de_v5 import air_source_heat_pump, low_flow_shower_head

IMPLEMENTATIONS: dict[str, dict[str, Callable]] = {
    "de-res-hvac-air-source-heat-pump": air_source_heat_pump.FUNCTIONS,
    "de-res-water-heating-low-flow-shower-head": low_flow_shower_head.FUNCTIONS,
}
