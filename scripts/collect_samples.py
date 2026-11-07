"""Copy user-provided images into the local benchmark dataset.

Example:
    python scripts/collect_samples.py source.jpg data/raw/personal/example.jpg
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def main() -> None:
    """Copy one approved local image while preserving its timestamp metadata.

    This utility deliberately copies rather than moves the source image so the original
    remains available to its owner. The caller is responsible for adding matching
    provenance metadata to ``data/manifests/benchmark.csv``.
    """
    parser = argparse.ArgumentParser(description="Copy a user-owned image into the benchmark set.")
    parser.add_argument("source", type=Path, help="Original image path")
    parser.add_argument("destination", type=Path, help="Dataset destination path")
    args = parser.parse_args()

    # Validate before creating the destination directory to avoid empty folders caused
    # by an invalid path supplied at the command line.
    if not args.source.is_file():
        raise FileNotFoundError(f"Source image not found: {args.source}")

    # Create the local-only benchmark destination and preserve the source timestamps.
    args.destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(args.source, args.destination)
    print(f"Collected: {args.destination}")


if __name__ == "__main__":
    main()
