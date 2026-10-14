"""Explicit map from measure id to its Python implementation functions.

Measure YAML names functions; it never names modules. Only functions listed
here can be invoked, so reference data cannot cause arbitrary code to run.
"""

from collections.abc import Callable

IMPLEMENTATIONS: dict[str, dict[str, Callable]] = {}
