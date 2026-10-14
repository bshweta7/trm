"""trm_engine must stay framework-independent so any interface can reuse it."""

import ast
import subprocess
import sys
from pathlib import Path

ENGINE_SRC = Path(__file__).resolve().parents[1] / "src" / "trm_engine"
FORBIDDEN = {"streamlit", "fastapi", "starlette", "trm_ui"}


def imported_roots(path: Path) -> set[str]:
    roots = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            roots.add(node.module.split(".")[0])
    return roots


def test_engine_source_does_not_import_frameworks():
    offenders = {
        str(path.relative_to(ENGINE_SRC)): sorted(imported_roots(path) & FORBIDDEN)
        for path in ENGINE_SRC.rglob("*.py")
        if imported_roots(path) & FORBIDDEN
    }
    assert offenders == {}


def test_importing_and_using_engine_loads_no_framework():
    script = (
        "import sys, trm_engine;"
        "trm_engine.calculate('de-res-water-heating-low-flow-shower-head', 'direct_install',"
        " {'water_heater_fuel': 'electric', 'gpm_low': 2.0});"
        f"print(sorted(m for m in sys.modules if m.split('.')[0] in {sorted(FORBIDDEN)!r}))"
    )
    out = subprocess.run([sys.executable, "-c", script], check=True, capture_output=True, text=True)
    assert out.stdout.strip() == "[]"
