import { useEffect, useRef, useState } from "react";
import * as pdfjs from "pdfjs-dist";
import type { PageRotation } from "../utils/bbox";
import { BboxOverlay, type OverlayField } from "./BboxOverlay";
import styles from "./PdfViewer.module.css";

pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  "pdfjs-dist/build/pdf.worker.min.mjs",
  import.meta.url,
).toString();

interface Props {
  file: Blob | null;
  pageNumber: number;
  pageCount: number;
  onPageChange: (page: number) => void;
  fields: OverlayField[];
  highlighted: string | null;
  onHighlight: (name: string | null) => void;
}

export function PdfViewer({
  file,
  pageNumber,
  pageCount,
  onPageChange,
  fields,
  highlighted,
  onHighlight,
}: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const wrapRef = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(1);
  const [pageWidth, setPageWidth] = useState(0);
  const [pageHeight, setPageHeight] = useState(0);
  const [rotation, setRotation] = useState<PageRotation>(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!file || !canvasRef.current) return;
    let cancelled = false;
    setError(null);

    const render = async () => {
      try {
        const data = await file.arrayBuffer();
        const pdf = await pdfjs.getDocument({ data }).promise;
        const page = await pdf.getPage(pageNumber);
        const rot = (page.rotate % 360) as PageRotation;
        const viewport = page.getViewport({ scale: 1, rotation: rot });
        const containerWidth = wrapRef.current?.clientWidth ?? viewport.width;
        const fitScale = containerWidth / viewport.width;
        const vp = page.getViewport({ scale: fitScale, rotation: rot });

        const canvas = canvasRef.current!;
        const ctx = canvas.getContext("2d");
        if (!ctx) return;

        canvas.width = vp.width;
        canvas.height = vp.height;
        const unrotated = page.getViewport({ scale: 1, rotation: 0 });
        setScale(fitScale);
        setPageWidth(unrotated.width);
        setPageHeight(unrotated.height);
        const normRot: PageRotation =
          rot === 0 || rot === 90 || rot === 180 || rot === 270 ? rot : 0;
        setRotation(normRot);

        if (cancelled) return;
        await page.render({ canvasContext: ctx, viewport: vp }).promise;
      } catch (e) {
        if (!cancelled) setError(String(e));
      }
    };

    render();
    return () => {
      cancelled = true;
    };
  }, [file, pageNumber]);

  const pageFields = fields.filter((f) => f.bbox.page === pageNumber);
  const pages = Math.max(1, pageCount);

  return (
    <div ref={wrapRef} className={styles.wrap}>
      {pages > 1 && (
        <nav className={styles.pager} aria-label="PDF pages">
          {Array.from({ length: pages }, (_, i) => i + 1).map((p) => (
            <button
              key={p}
              type="button"
              className={p === pageNumber ? styles.pageActive : styles.pageBtn}
              aria-label={`Page ${p}`}
              aria-current={p === pageNumber ? "page" : undefined}
              onClick={() => onPageChange(p)}
            >
              {p}
            </button>
          ))}
        </nav>
      )}
      {error && <p className={styles.error} role="alert">{error}</p>}
      <div className={styles.canvasWrap}>
        <canvas ref={canvasRef} className={styles.canvas} />
        {pageWidth > 0 && (
          <BboxOverlay
            fields={pageFields}
            pageWidth={pageWidth}
            pageHeight={pageHeight}
            scale={scale}
            rotation={rotation}
            highlighted={highlighted}
            onHighlight={onHighlight}
          />
        )}
      </div>
    </div>
  );
}
