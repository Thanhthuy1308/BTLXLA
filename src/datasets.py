"""Manifest loading and provenance handling for the benchmark experiment."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SampleRecord:
    """One manifest row with the provenance needed to interpret a result.

    ``parent_image_id`` and ``variant`` identify controlled derived samples. ExDark
    fields preserve official condition metadata so results can be grouped by lighting
    environment without inspecting the image files again.
    """

    image_id: str
    file_path: str
    source: str
    condition_label: str
    reference_path: str
    reference_type: str
    license_note: str
    notes: str
    parent_image_id: str
    variant: str
    illumination_condition: str
    environment: str
    dataset_split: str


def read_manifest(path: str | Path) -> list[SampleRecord]:
    """Load benchmark metadata into immutable records.

    Optional provenance fields default to an empty string to keep older manifests
    readable while the dataset schema evolves. Required image paths are validated by
    the runner when it opens each image.
    """
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        records: list[SampleRecord] = []
        for row in csv.DictReader(handle):
            # Backward compatibility for manifests created before ExDark condition
            # metadata and derived-variant provenance were introduced.
            for field in ("parent_image_id", "variant", "illumination_condition", "environment", "dataset_split"):
                row.setdefault(field, "")
            records.append(SampleRecord(**row))
        return records
