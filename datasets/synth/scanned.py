"""Rasterise vector PDFs into mild scanned image-only PDFs (v1)."""

from __future__ import annotations

import math
import random
from io import BytesIO
from pathlib import Path

import pypdfium2 as pdfium
from PIL import Image, ImageFilter
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from datasets.synth.types import LayoutBox


def _rotate_point(
    x: float, y: float, cx: float, cy: float, angle_rad: float
) -> tuple[float, float]:
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)
    dx, dy = x - cx, y - cy
    return cx + cos_a * dx - sin_a * dy, cy + sin_a * dx + cos_a * dy


def transform_layout_boxes(
    boxes: dict[str, LayoutBox],
    page_width: float,
    page_height: float,
    angle_deg: float,
) -> dict[str, LayoutBox]:
    """Map layout boxes through the same rotation applied to the rasterised page."""
    if abs(angle_deg) < 1e-9:
        return boxes
    cx, cy = page_width / 2, page_height / 2
    angle_rad = math.radians(angle_deg)
    out: dict[str, LayoutBox] = {}
    for key, box in boxes.items():
        corners = [
            (box.x0, box.y0),
            (box.x0, box.y1),
            (box.x1, box.y0),
            (box.x1, box.y1),
        ]
        rotated = [_rotate_point(x, y, cx, cy, angle_rad) for x, y in corners]
        xs = [p[0] for p in rotated]
        ys = [p[1] for p in rotated]
        out[key] = LayoutBox(
            page=box.page,
            x0=min(xs),
            y0=min(ys),
            x1=max(xs),
            y1=max(ys),
        )
    return out


def rasterize_to_scanned_pdf(
    vector_pdf: Path,
    out_pdf: Path,
    rng: random.Random,
    *,
    dpi: int | None = None,
) -> tuple[float, int]:
    """Replace ``vector_pdf`` with an image-only PDF; return (angle_deg, dpi)."""
    if dpi is None:
        dpi = rng.randint(150, 200)
    angle_deg = rng.uniform(-1.5, 1.5)

    doc = pdfium.PdfDocument(vector_pdf.read_bytes())
    page = doc[0]
    width_pt, height_pt = page.get_size()
    scale = dpi / 72.0
    bitmap = page.render(scale=scale)
    pil = bitmap.to_pil()
    doc.close()

    if abs(angle_deg) >= 0.05:
        pil = pil.rotate(
            angle_deg, resample=Image.Resampling.BICUBIC, expand=False, fillcolor="white"
        )
    pil = pil.filter(ImageFilter.GaussianBlur(radius=0.6))
    noise = Image.effect_noise(pil.size, 8.0).convert("RGB")
    pil = Image.blend(pil, noise, alpha=0.04)

    buf = BytesIO()
    pil.save(buf, format="PNG")
    buf.seek(0)

    page_w, page_h = A4
    c = canvas.Canvas(str(out_pdf), pagesize=A4, invariant=1)
    c.drawImage(
        ImageReader(buf),
        0,
        0,
        width=page_w,
        height=page_h,
        preserveAspectRatio=True,
        anchor="c",
    )
    c.showPage()
    c.save()
    return angle_deg, dpi
