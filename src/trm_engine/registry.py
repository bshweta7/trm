"""Load and locate TRM measure definitions. Contains no calculation logic."""

from __future__ import annotations

from functools import cache
from importlib.resources import files
from importlib.resources.abc import Traversable
from pathlib import Path

import yaml

from trm_engine.models import Manifest, ManifestEntry, Measure


class MeasureNotFoundError(KeyError):
    pass


class ReferenceDataError(ValueError):
    """A YAML file is missing, malformed, or inconsistent with the manifest."""


def default_data_root() -> Traversable:
    """Locate the ``trm/`` reference-data directory.

    Installed wheels carry a copy at ``trm_engine/data/trm`` (see pyproject.toml).
    Source checkouts and editable installs fall back to the repository's ``trm/``.
    """
    packaged = files("trm_engine") / "data" / "trm"
    if packaged.is_dir():
        return packaged
    checkout = Path(__file__).resolve().parents[2] / "trm"
    if checkout.is_dir():
        return checkout
    raise ReferenceDataError("TRM reference data not found in the package or a source checkout")


def _read_yaml(path: Traversable) -> dict:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ReferenceDataError(f"cannot read {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ReferenceDataError(f"{path}: expected a mapping at the top level")
    return data


class MeasureRegistry:
    """Measures for one jurisdiction and TRM version, as listed in its manifest."""

    def __init__(self, version_dir: Traversable):
        self._dir = version_dir
        self.manifest = Manifest.model_validate(_read_yaml(version_dir / "manifest.yaml"))
        self._entries = {m.id: m for m in self.manifest.measures}
        self._cache: dict[str, Measure] = {}

    @classmethod
    def for_version(
        cls, jurisdiction: str, version: str, data_root: Traversable | None = None
    ) -> MeasureRegistry:
        """E.g. ``MeasureRegistry.for_version("de", "v5")`` loads ``trm/de/v5/``."""
        root = data_root if data_root is not None else default_data_root()
        return cls(root / jurisdiction / version)

    def entries(self) -> list[ManifestEntry]:
        return list(self.manifest.measures)

    def get(self, measure_id: str) -> Measure:
        if measure_id in self._cache:
            return self._cache[measure_id]
        entry = self._entries.get(measure_id)
        if entry is None:
            raise MeasureNotFoundError(measure_id)

        path = self._dir
        for part in entry.file.split("/"):
            path = path / part
        measure = Measure.model_validate(_read_yaml(path))

        mismatches = [
            name
            for name, expected, actual in (
                ("id", entry.id, measure.id),
                ("sector", entry.sector, measure.classification.market_sector),
                ("category", entry.category, measure.classification.category),
                ("name", entry.name, measure.classification.name),
                ("jurisdiction", self.manifest.jurisdiction, measure.jurisdiction),
                ("version", self.manifest.version, measure.trm_version),
            )
            if expected != actual
        ]
        if mismatches:
            raise ReferenceDataError(f"{entry.file}: manifest mismatch in {', '.join(mismatches)}")

        self._cache[measure_id] = measure
        return measure


@cache
def default_registry() -> MeasureRegistry:
    """The Delaware TRM v5 registry, the only TRM version implemented so far."""
    return MeasureRegistry.for_version("de", "v5")
