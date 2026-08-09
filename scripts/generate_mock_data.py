"""Generate the complete Meridian sample dataset into sample_data/.

Deterministic: fixed seed, pinned reference date. Run from the repo root:

    python scripts/generate_mock_data.py [--out sample_data]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from mockgen.output import generate  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="sample_data", type=Path)
    args = parser.parse_args()

    summary = generate(args.out)
    print("Generated sample dataset:")
    for k, v in summary.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
