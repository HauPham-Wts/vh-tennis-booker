"""One parsed UI hierarchy dump and label matching on it.

A dump returns every element on the screen with its bounds in about the time of
a single element query, so the flow reads each screen once and finds all the
elements it needs locally. Kept free of device access for unit tests.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass

from court_booker.geometry import Box, center, parse_bounds


@dataclass(frozen=True)
class Node:
    """An element of the screen: its accessibility label and visible bounds."""

    desc: str
    box: Box
    clickable: bool

    @property
    def center(self) -> tuple[int, int]:
        """Return the tap point in the middle of the visible bounds."""
        return center(self.box)

    @property
    def height(self) -> int:
        return self.box[3] - self.box[1]


@dataclass(frozen=True)
class Match:
    """Criteria an element label must meet; unset criteria are ignored.

    ``pattern`` must match the whole label, like ``descriptionMatches`` in uiautomator.
    """

    desc: str | None = None
    prefix: str | None = None
    contains: str | None = None
    pattern: str | None = None
    clickable: bool | None = None

    def __call__(self, node: Node) -> bool:
        text = node.desc
        return (
            (self.desc is None or text == self.desc)
            and (self.prefix is None or text.startswith(self.prefix))
            and (self.contains is None or self.contains in text)
            and (self.pattern is None or re.fullmatch(self.pattern, text, re.DOTALL) is not None)
            and (self.clickable is None or node.clickable == self.clickable)
        )


class Screen:
    """The elements of one hierarchy dump, in document order."""

    def __init__(self, nodes: list[Node]) -> None:
        self.nodes = nodes

    @classmethod
    def parse(cls, xml: str) -> Screen:
        """Build a screen from ``dump_hierarchy`` XML; nodes without bounds are skipped."""
        nodes = []
        for element in ET.fromstring(xml).iter("node"):
            box = parse_bounds(element.get("bounds", ""))
            if box is not None:
                nodes.append(
                    Node(element.get("content-desc", ""), box, element.get("clickable") == "true")
                )
        return cls(nodes)

    @property
    def size(self) -> tuple[int, int]:
        """Return ``(width, height)`` covered by the elements, i.e. the screen size.

        Read from the dump because ``window_size()`` reports the landscape size when
        MuMu runs a tablet resolution with the app in portrait.
        """
        if not self.nodes:
            return 0, 0
        return max(n.box[2] for n in self.nodes), max(n.box[3] for n in self.nodes)

    def find(self, match: Match) -> Node | None:
        """Return the first element that satisfies ``match``."""
        return next((node for node in self.nodes if match(node)), None)

    def find_all(self, match: Match) -> list[Node]:
        """Return every element that satisfies ``match``."""
        return [node for node in self.nodes if match(node)]

    def describe(self) -> list[str]:
        """Return one log line per labelled or clickable element, in document order.

        Unlabelled clickable elements are kept because some buttons, such as the
        month arrows of the calendar, may have no label.
        """
        lines = []
        for node in self.nodes:
            if node.desc or node.clickable:
                left, top, right, bottom = node.box
                flag = " clickable" if node.clickable else ""
                lines.append(f"[{left},{top}][{right},{bottom}]{flag} {node.desc!r}")
        return lines
