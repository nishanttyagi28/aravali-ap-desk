import { describe, expect, it } from "vitest";
import { bboxToCanvasRect } from "./bbox";

const sample = {
  page: 1,
  x0: 100,
  y0: 200,
  x1: 150,
  y1: 220,
};

describe("bboxToCanvasRect", () => {
  const pageWidth = 600;
  const pageHeight = 800;
  const scale = 2;

  it("rotation 0", () => {
    expect(
      bboxToCanvasRect(sample, pageWidth, pageHeight, scale, 0),
    ).toEqual({
      x: 200,
      y: 1160,
      width: 100,
      height: 40,
    });
  });

  it("rotation 90", () => {
    expect(
      bboxToCanvasRect(sample, pageWidth, pageHeight, scale, 90),
    ).toEqual({
      x: 400,
      y: 900,
      width: 40,
      height: 100,
    });
  });

  it("rotation 180", () => {
    expect(
      bboxToCanvasRect(sample, pageWidth, pageHeight, scale, 180),
    ).toEqual({
      x: 900,
      y: 400,
      width: 100,
      height: 40,
    });
  });

  it("rotation 270", () => {
    expect(
      bboxToCanvasRect(sample, pageWidth, pageHeight, scale, 270),
    ).toEqual({
      x: 1160,
      y: 200,
      width: 40,
      height: 100,
    });
  });
});
