/** PDF user-space bbox (bottom-left origin, points). */
export interface BBox {
  page: number;
  x0: number;
  y0: number;
  x1: number;
  y1: number;
}

export type PageRotation = 0 | 90 | 180 | 270;

export interface CanvasRect {
  x: number;
  y: number;
  width: number;
  height: number;
}

/**
 * Map a PDF bbox to canvas/CSS coordinates for a given page size, scale, and rotation.
 * Rotation matches PDF / pdf.js viewport rotation (degrees clockwise).
 */
export function bboxToCanvasRect(
  bbox: BBox,
  pageWidth: number,
  pageHeight: number,
  scale: number,
  rotation: PageRotation,
): CanvasRect {
  const { x0, y0, x1, y1 } = bbox;
  switch (rotation) {
    case 0:
      return {
        x: x0 * scale,
        y: (pageHeight - y1) * scale,
        width: (x1 - x0) * scale,
        height: (y1 - y0) * scale,
      };
    case 90:
      return {
        x: y0 * scale,
        y: (pageWidth - x1) * scale,
        width: (y1 - y0) * scale,
        height: (x1 - x0) * scale,
      };
    case 180:
      return {
        x: (pageWidth - x1) * scale,
        y: y0 * scale,
        width: (x1 - x0) * scale,
        height: (y1 - y0) * scale,
      };
    case 270:
      return {
        x: (pageHeight - y1) * scale,
        y: x0 * scale,
        width: (y1 - y0) * scale,
        height: (x1 - x0) * scale,
      };
    default:
      return bboxToCanvasRect(bbox, pageWidth, pageHeight, scale, 0);
  }
}

export function confidenceColor(confidence: number): string {
  if (confidence >= 0.9) return "var(--bbox-high)";
  if (confidence >= 0.7) return "var(--bbox-mid)";
  return "var(--bbox-low)";
}
