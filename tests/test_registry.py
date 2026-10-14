"""Loading reference data, manifest consistency, and packaging."""

import os
import shutil
import subprocess
import sys
import venv
from pathlib import Path

import pytest

from conftest import DEMO_MEASURE_ID, DEMO_VERSION_DIR, FIXTURE_ROOT
from trm_engine.registry import (
    MeasureNotFoundError,
    MeasureRegistry,
    ReferenceDataError,
    default_data_root,
    default_registry,
)

REPO = Path(__file__).resolve().parents[1]


def test_loads_measure_listed_in_manifest():
    registry = MeasureRegistry.for_version("xx", "v1", data_root=FIXTURE_ROOT)
    assert [e.id for e in registry.entries()] == [DEMO_MEASURE_ID]
    measure = registry.get(DEMO_MEASURE_ID)
    assert measure.classification.name == "Demo Widget"
    assert registry.get(DEMO_MEASURE_ID) is measure  # cached


def test_unknown_measure():
    registry = MeasureRegistry(DEMO_VERSION_DIR)
    with pytest.raises(MeasureNotFoundError):
        registry.get("xx-res-demo-perpetual-motion")


def copy_demo(tmp_path) -> Path:
    target = tmp_path / "xx" / "v1"
    shutil.copytree(DEMO_VERSION_DIR, target)
    return target


@pytest.mark.parametrize(
    ("old", "new", "field"),
    [
        ("name: Demo Widget", "name: Demo Gadget", "name"),
        ("category: demo", "category: lighting", "category"),
        ('version: "1.0"', 'version: "2.0"', "version"),
    ],
)
def test_manifest_mismatch_is_rejected(tmp_path, old, new, field):
    version_dir = copy_demo(tmp_path)
    manifest = version_dir / "manifest.yaml"
    manifest.write_text(manifest.read_text().replace(old, new))
    with pytest.raises(ReferenceDataError, match=field):
        MeasureRegistry(version_dir).get(DEMO_MEASURE_ID)


def test_malformed_yaml_is_rejected(tmp_path):
    version_dir = copy_demo(tmp_path)
    (version_dir / "residential" / "demo" / "widget.yaml").write_text("id: [unclosed")
    with pytest.raises(ReferenceDataError):
        MeasureRegistry(version_dir).get(DEMO_MEASURE_ID)


def test_non_mapping_yaml_is_rejected(tmp_path):
    version_dir = copy_demo(tmp_path)
    (version_dir / "residential" / "demo" / "widget.yaml").write_text("- just\n- a list\n")
    with pytest.raises(ReferenceDataError, match="mapping"):
        MeasureRegistry(version_dir).get(DEMO_MEASURE_ID)


def test_missing_manifest_is_rejected(tmp_path):
    with pytest.raises(ReferenceDataError):
        MeasureRegistry(tmp_path)


def test_default_registry_is_delaware_v5_from_checkout():
    assert Path(str(default_data_root())) == REPO / "trm"
    registry = default_registry()
    assert (registry.manifest.jurisdiction, registry.manifest.version) == ("DE", "5.0")
    for entry in registry.entries():
        registry.get(entry.id)


@pytest.mark.skipif(not os.environ.get("TRM_TEST_WHEEL"), reason="set TRM_TEST_WHEEL=1 (needs network)")
def test_installed_wheel_finds_reference_data(tmp_path):
    """Build a wheel, install it into a fresh venv, and load every measure from outside the repo."""
    dist = tmp_path / "dist"
    subprocess.run(
        [sys.executable, "-m", "pip", "wheel", "--no-deps", "-w", dist, REPO],
        check=True,
        capture_output=True,
    )
    env_dir = tmp_path / "venv"
    venv.create(env_dir, with_pip=True)
    python = env_dir / "bin" / "python"
    subprocess.run([python, "-m", "pip", "install", "-q", *dist.glob("*.whl")], check=True)
    script = (
        "import trm_engine; from trm_engine.registry import default_data_root, default_registry;"
        "r = default_registry(); [r.get(e.id) for e in r.entries()];"
        "print(default_data_root()); print(len(r.entries()))"
    )
    out = subprocess.run([python, "-I", "-c", script], cwd=tmp_path, check=True, capture_output=True, text=True)
    data_root, count = out.stdout.split()
    assert "site-packages" in data_root
    assert int(count) == len(default_registry().entries())
