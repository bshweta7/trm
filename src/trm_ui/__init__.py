"""Presentation layer for the TRM calculation engine.

``presentation`` turns public ``trm_engine`` objects into plain data for display
and imports no UI framework. ``streamlit_app`` is the only module that imports
Streamlit. All TRM formulas, assumptions, validation and defaults stay in
``trm_engine``.
"""
