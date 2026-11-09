"""Ask one question from the command line.

    python -m sourcedesk samples "What is Rahul Verma's bonus?"

Run from the repository root with src on PYTHONPATH, or use tests/test_smoke.py.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sourcedesk.tiers import probe
from sourcedesk.workbench import Workbench


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ask SourceDesk one question.")
    parser.add_argument("folder", type=Path)
    parser.add_argument("question")
    args = parser.parse_args(argv)
    tier = probe()
    print(f"tier={tier.name} stitcher={tier.stitcher} ({tier.reason})")
    if not tier.opens_corpus:
        print(tier.reason)
        return 2
    answer = Workbench(args.folder, tier=tier).ask(args.question)
    print(answer.status)
    print(answer.text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
