import type { BBox, PageRotation } from "../utils/bbox";
import { bboxToCanvasRect, confidenceColor } from "../utils/bbox";
import styles from "./BboxOverlay.module.css";

export interface OverlayField {
  name: string;
  bbox: BBox;
  confidence: number;
}

interface Props {
  fields: OverlayField[];
  pageWidth: number;
  pageHeight: number;
  scale: number;
  rotation: PageRotation;
  highlighted: string | null;
  onHighlight: (name: string | null) => void;
}

export function BboxOverlay({
  fields,
  pageWidth,
  pageHeight,
  scale,
  rotation,
  highlighted,
  onHighlight,
}: Props) {
  return (
    <div className={styles.layer} aria-hidden="true">
      {fields.map((f) => {
        const rect = bboxToCanvasRect(
          f.bbox,
          pageWidth,
          pageHeight,
          scale,
          rotation,
        );
        const active = highlighted === f.name;
        return (
          <button
            key={f.name}
            type="button"
            className={`${styles.box} ${active ? styles.active : ""}`}
            style={{
              left: rect.x,
              top: rect.y,
              width: rect.width,
              height: rect.height,
              borderColor: confidenceColor(f.confidence),
            }}
            title={f.name}
            onMouseEnter={() => onHighlight(f.name)}
            onMouseLeave={() => onHighlight(null)}
            onFocus={() => onHighlight(f.name)}
            onBlur={() => onHighlight(null)}
            tabIndex={-1}
          />
        );
      })}
    </div>
  );
}
