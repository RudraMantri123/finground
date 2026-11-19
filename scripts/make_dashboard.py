#!/usr/bin/env python3
"""Generate the static observability report (traces + leaderboard) as one HTML file.

Usage:
  python scripts/make_dashboard.py                    # -> traces/dashboard.html
  python scripts/make_dashboard.py --out /tmp/x.html --traces path/to/traces
"""

from __future__ import annotations

import argparse
from pathlib import Path

from finground.dashboard import write_dashboard


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=None, help="output HTML path")
    parser.add_argument("--traces", type=Path, default=None, help="trace directory")
    args = parser.parse_args(argv)
    path = write_dashboard(args.out, directory=args.traces)
    print(f"Wrote {path}\nOpen it with: open {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
