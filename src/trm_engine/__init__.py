"""Machine-readable, source-cited TRM calculation engine.

This package is framework-independent: it must not import any UI or web
framework, so interfaces such as the Streamlit app (``trm_ui``) or a future
HTTP API can share it unchanged.
"""

from trm_engine.inputs import InputValidationError
from trm_engine.registry import MeasureRegistry, default_registry
from trm_engine.service import (
    ApplicationNotImplementedError,
    CalculationResult,
    CalculationWarning,
    ValueOrigin,
    calculate,
    input_variables,
)

__all__ = [
    "ApplicationNotImplementedError",
    "CalculationResult",
    "CalculationWarning",
    "InputValidationError",
    "MeasureRegistry",
    "ValueOrigin",
    "calculate",
    "default_registry",
    "input_variables",
]
