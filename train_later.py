"""LoRA recipe for a later stitcher adaptation. This file does not train.

CS781 Module 4.1 merges LoRA into the base weights at inference. Module 3.4
puts an FP16 Adam step for 7 billion parameters near 112 GB, which this
laptop does not have. Rank 16 and alpha 32 match the adaptation used on the
legal model. Nothing here steps an optimizer.
"""

from __future__ import annotations

import argparse

LORA = {
    "target": "stitcher attention projections only",
    "rank": 16,
    "alpha": 32,
    "dropout": 0.0,
    "epochs": 0,
    "merge_at_inference": True,
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Record the LoRA recipe and exit.")
    parser.add_argument("--train", action="store_true", help="Ignored. Training stays off.")
    parser.parse_args()
    print("SourceDesk LoRA recipe, not training")
    for key, value in LORA.items():
        print(f"{key}={value}")
    print("epochs=0")
    print("optimizer steps=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
