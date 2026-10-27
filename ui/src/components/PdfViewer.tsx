import { useEffect, useRef, useState } from "react";
import * as pdfjs from "pdfjs-dist";
import type { PDFDocumentLoadingTask, PDFDocumentProxy } from "pdfjs-dist";
import type { PageRotation } from "../utils/bbox";
import { normalizePageRotation } from "../utils/bbox";
import { BboxOverlay, type OverlayField } from "./BboxOverlay";
import styles from "./PdfViewer.module.css";

pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  "pdfjs-dist/build/pdf.worker.min.mjs",
  import.meta.url,
).toString();

interface RenderResources {
  renderTask: { cancel: () => void; promise: Promise<void> } | null;
  pdf: PDFDocumentProxy | null;
  loadingTask: PDFDocumentLoadingTask | null;
}

async function tearDownRenderResources(resources: RenderResources): Promise<void> {
  if (resources.renderTask) {
    resources.renderTask.cancel();
    try {
      await resources.renderTask.promise;
    } catch {
      // RenderingCancelledException or superseded render
    }
    resources.renderTask = null;
  }
  if (resources.pdf) {
    try {
      await resources.pdf.destroy();
    } catch {
      // already destroyed
    }
    resources.pdf = null;
  }
  if (resources.loadingTask) {
    resources.loadingTask.destroy();
    resources.loadingTask = null;
  }
}

function isRenderingCancelled(error: unknown): boolean {
  return (
    error instanceof Error &&
    (error.name === "RenderingCancelledException" ||
      error.message.includes("Rendering cancelled"))
  );
}

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
  const renderGenerationRef = useRef(0);
  const [scale, setScale] = useState(1);
  const [pageWidth, setPageWidth] = useState(0);
  const [pageHeight, setPageHeight] = useState(0);
  const [rotation, setRotation] = useState<PageRotation>(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!file || !canvasRef.current) return;

    const renderId = ++renderGenerationRef.current;
    const resources: RenderResources = {
      renderTask: null,
      pdf: null,
      loadingTask: null,
    };

    const isStale = () => renderId !== renderGenerationRef.current;

    const render = async () => {
      try {
        setError(null);
        const data = await file.arrayBuffer();
        if (isStale()) return;

        const loadingTask = pdfjs.getDocument({ data });
        resources.loadingTask = loadingTask;
        const pdf = await loadingTask.promise;
        resources.pdf = pdf;
        resources.loadingTask = null;
        if (isStale()) return;

        const page = await pdf.getPage(pageNumber);
        if (isStale()) return;

        const rot = normalizePageRotation(page.rotate);
        const viewport = page.getViewport({ scale: 1, rotation: rot });
        const measuredWidth = wrapRef.current?.clientWidth ?? 0;
        const containerWidth =
          measuredWidth > 0 ? measuredWidth : viewport.width;
        const fitScale = containerWidth / viewport.width;
        const vp = page.getViewport({ scale: fitScale, rotation: rot });
        if (isStale()) return;

        const offscreen = document.createElement("canvas");
        offscreen.width = vp.width;
        offscreen.height = vp.height;
        const offCtx = offscreen.getContext("2d");
        if (!offCtx) return;

        const renderTask = page.render({
          canvasContext: offCtx,
          viewport: vp,
        });
        resources.renderTask = renderTask;
        await renderTask.promise;
        resources.renderTask = null;
        if (isStale()) return;

        const canvas = canvasRef.current;
        if (!canvas) return;
        const ctx = canvas.getContext("2d");
        if (!ctx) return;

        canvas.width = vp.width;
        canvas.height = vp.height;
        ctx.setTransform(1, 0, 0, 1, 0, 0);
        ctx.drawImage(offscreen, 0, 0);

        const unrotated = page.getViewport({ scale: 1, rotation: 0 });
        setScale(fitScale);
        setPageWidth(unrotated.width);
        setPageHeight(unrotated.height);
        setRotation(rot);
      } catch (e) {
        if (isStale() || isRenderingCancelled(e)) return;
        setError(String(e));
      }
    };

    void render();

    return () => {
      renderGenerationRef.current += 1;
      void tearDownRenderResources(resources);
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
