"""Bounding boxes in PDF user space."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


class BBox(BaseModel):
    """Axis-aligned rectangle on a PDF page.

    Coordinate convention: PDF user space of the **unrotated** page, units = points,
    origin **bottom-left**, *y* increases upward (reportlab / pypdf). Producers using
    top-left tools (e.g. pdfplumber ``top``/``bottom`` or OCR pixels) must convert:
    ``y0 = page_height - bottom``, ``y1 = page_height - top``.
    """

    model_config = ConfigDict(extra="forbid")

    page: int = Field(ge=1)
    x0: float
    y0: float
    x1: float
    y1: float

    @model_validator(mode="after")
    def _check_bounds(self) -> BBox:
        if self.x0 > self.x1:
            raise ValueError("x0 must be <= x1")
        if self.y0 > self.y1:
            raise ValueError("y0 must be <= y1")
        return self
