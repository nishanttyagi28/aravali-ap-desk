"""Shared synth layout types."""

from __future__ import annotations

from dataclasses import dataclass

from docai.contracts.bbox import BBox


@dataclass
class LayoutBox:
    page: int
    x0: float
    y0: float
    x1: float
    y1: float

    def to_bbox(self) -> BBox:
        return BBox(page=self.page, x0=self.x0, y0=self.y0, x1=self.x1, y1=self.y1)
