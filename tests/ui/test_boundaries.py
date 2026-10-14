"""trm_ui may use only trm_engine's public interface, and only streamlit_app imports Streamlit."""

import ast
from pathlib import Path

UI_SRC = Path(__file__).resolve().parents[2] / "src" / "trm_ui"
PUBLIC_ENGINE_MODULES = {"trm_engine", "trm_engine.models"}
STREAMLIT_MODULES = {"streamlit_app.py"}


def imports(path: Path) -> set[str]:
    found = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            found.add(node.module)
    return found


def ui_files():
    return sorted(UI_SRC.rglob("*.py"))


def test_ui_uses_only_public_engine_modules():
    for path in ui_files():
        engine = {m for m in imports(path) if m.split(".")[0] == "trm_engine"}
        assert engine <= PUBLIC_ENGINE_MODULES, f"{path.name} imports engine internals: {engine - PUBLIC_ENGINE_MODULES}"


def test_only_streamlit_app_imports_streamlit():
    for path in ui_files():
        roots = {m.split(".")[0] for m in imports(path)}
        if path.name not in STREAMLIT_MODULES:
            assert "streamlit" not in roots, path.name
        assert "fastapi" not in roots, path.name
