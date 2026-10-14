"""Issue IDs referenced from YAML and tests must exist in the validation register.

Note: these tests check traceability only. They never imply an issue is resolved.
"""

import re
from pathlib import Path

import pytest

from trm_engine.registry import default_registry

REPO = Path(__file__).resolve().parents[1]
REGISTER = REPO / "docs" / "validation_register.md"


def register_ids() -> set[str]:
    return set(re.findall(r"^### (VR-\d{3})\b", REGISTER.read_text(encoding="utf-8"), re.MULTILINE))


def yaml_issue_ids() -> set[str]:
    registry = default_registry()
    ids: set[str] = set()
    for entry in registry.entries():
        m = registry.get(entry.id)
        ids.update(m.issues)
        for group in (m.applications, m.variables, m.lookups.values(), m.calculations, m.warnings):
            for item in group:
                ids.update(item.issues)
    return ids


def test_register_ids_are_unique_and_sequential():
    found = re.findall(r"^### (VR-\d{3})\b", REGISTER.read_text(encoding="utf-8"), re.MULTILINE)
    assert len(found) == len(set(found))
    assert found == sorted(found)


def test_yaml_issue_ids_exist_in_register():
    assert yaml_issue_ids() <= register_ids()


def test_test_markers_reference_existing_issues(request):
    marked: set[str] = set()
    for item in request.session.items:
        for marker in item.iter_markers("trm_issue"):
            marked.update(marker.args)
    if not marked:
        pytest.skip("run the full test suite to check markers")
    assert marked <= register_ids()


def test_no_issue_is_resolved_without_a_reviewer():
    text = REGISTER.read_text(encoding="utf-8")
    for block in re.split(r"^### ", text, flags=re.MULTILINE)[1:]:
        status = re.search(r"\*\*Review status:\*\*\s*(\w[\w ]*)", block)
        reviewer = re.search(r"\*\*Reviewer:\*\*[ \t]*(\S.*)?$", block, re.MULTILINE)
        assert status, block[:20]
        if status.group(1).strip() == "Resolved":
            assert reviewer and reviewer.group(1), f"{block[:6]} is resolved without a reviewer"
