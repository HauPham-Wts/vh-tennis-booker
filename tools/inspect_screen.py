"""Dump the current UI hierarchy and list the nodes level with a given text.

Usage:
    python tools/inspect_screen.py
    python tools/inspect_screen.py --near "Tôi đã hiểu"
"""

from __future__ import annotations

import argparse
import re
import xml.etree.ElementTree as ET

import uiautomator2


def parse_bounds(text: str) -> tuple[int, int, int, int] | None:
    nums = [int(n) for n in re.findall(r"-?\d+", text or "")]
    return (nums[0], nums[1], nums[2], nums[3]) if len(nums) == 4 else None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--device", default="127.0.0.1:16384", help="ADB serial (default: MuMu 12 instance 0)"
    )
    parser.add_argument("--near", help="text whose row should be listed")
    parser.add_argument("--out", default="dump.xml")
    args = parser.parse_args()

    device = uiautomator2.connect(args.device)
    xml = device.dump_hierarchy(compressed=False)
    with open(args.out, "w", encoding="utf-8") as file:
        file.write(xml)
    print(f"Saved {args.out} (screen {device.window_size()})")
    if not args.near:
        return

    nodes = list(ET.fromstring(xml).iter("node"))
    label = next(
        (n for n in nodes if args.near in n.get("content-desc", "") + n.get("text", "")),
        None,
    )
    if label is None:
        print(f"Text not found: {args.near!r}")
        return
    label_box = parse_bounds(label.get("bounds", ""))
    assert label_box is not None
    _, top, _, bottom = label_box

    print(f"Label bounds={label.get('bounds')} clickable={label.get('clickable')}")
    print("-" * 72)
    for node in nodes:
        box = parse_bounds(node.get("bounds", ""))
        if not box or box[3] < top - 50 or box[1] > bottom + 50:
            continue
        text = (node.get("content-desc", "") or node.get("text", "")).replace("\n", " ")[:40]
        kind = node.get("class", "").rsplit(".", 1)[-1]
        print(
            f"{node.get('bounds'):<26} {kind:<14} "
            f"clickable={node.get('clickable'):<5} checkable={node.get('checkable'):<5} {text!r}"
        )


if __name__ == "__main__":
    main()
