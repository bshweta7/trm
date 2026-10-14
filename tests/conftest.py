from pathlib import Path

import pytest
import yaml

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "trm"
DEMO_VERSION_DIR = FIXTURE_ROOT / "xx" / "v1"
DEMO_MEASURE_FILE = DEMO_VERSION_DIR / "residential" / "demo" / "widget.yaml"
DEMO_MEASURE_ID = "xx-res-demo-widget"


@pytest.fixture
def demo_measure_data() -> dict:
    """Raw YAML of the synthetic demo measure, safe to mutate."""
    return yaml.safe_load(DEMO_MEASURE_FILE.read_text(encoding="utf-8"))
