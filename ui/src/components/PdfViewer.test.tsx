import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import {
  afterEach,
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

type MockRenderTask = {
  cancel: ReturnType<typeof vi.fn>;
  promise: Promise<void>;
  resolve: () => void;
  reject: (error: Error) => void;
  targetCanvas: HTMLCanvasElement;
};

type Fake2dContext = {
  canvas: HTMLCanvasElement;
  setTransform: ReturnType<typeof vi.fn>;
  drawImage: ReturnType<typeof vi.fn>;
};

const renderTasks: MockRenderTask[] = [];
let pageRotate = 0;
let pageWidthBase = 100;
let pdfDestroy = vi.fn(async () => {});
let loadingDestroy = vi.fn();
let visibleDrawImageCalls = 0;
let visibleCanvas: HTMLCanvasElement | null = null;

const contexts = new WeakMap<HTMLCanvasElement, Fake2dContext>();
const originalGetContext = HTMLCanvasElement.prototype.getContext;

function createFake2dContext(canvas: HTMLCanvasElement): Fake2dContext {
  const ctx: Fake2dContext = {
    canvas,
    setTransform: vi.fn(),
    drawImage: vi.fn(() => {
      if (visibleCanvas && canvas === visibleCanvas) {
        visibleDrawImageCalls += 1;
      }
    }),
  };
  contexts.set(canvas, ctx);
  return ctx;
}

function installCanvas2dStub(): void {
  HTMLCanvasElement.prototype.getContext = function (
    this: HTMLCanvasElement,
    type: string,
  ): RenderingContext | null {
    if (type !== "2d") {
      return originalGetContext.call(this, type);
    }
    const existing = contexts.get(this);
    if (existing) return existing as unknown as CanvasRenderingContext2D;
    return createFake2dContext(this) as unknown as CanvasRenderingContext2D;
  } as typeof HTMLCanvasElement.prototype.getContext;
}

function restoreCanvasStub(): void {
  HTMLCanvasElement.prototype.getContext = originalGetContext;
}

function createRenderTask(canvasContext: Fake2dContext): MockRenderTask {
  let resolve!: () => void;
  let reject!: (error: Error) => void;
  const promise = new Promise<void>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  const task: MockRenderTask = {
    cancel: vi.fn(() => {
      reject(new Error("Rendering cancelled"));
    }),
    promise,
    resolve: () => resolve(),
    reject,
    targetCanvas: canvasContext.canvas,
  };
  renderTasks.push(task);
  return task;
}

const { getDocumentMock } = vi.hoisted(() => ({
  getDocumentMock: vi.fn(),
}));

vi.mock("pdfjs-dist", () => ({
  GlobalWorkerOptions: { workerSrc: "" },
  getDocument: (options: unknown) => getDocumentMock(options),
}));

import { PdfViewer } from "./PdfViewer";

function configurePdfMock(): void {
  getDocumentMock.mockImplementation(() => {
    const loadingTask = {
      promise: Promise.resolve({
        getPage: vi.fn(async () => ({
          rotate: pageRotate,
          getViewport: vi.fn(
            ({ scale }: { scale: number; rotation?: number }) => ({
              width: pageWidthBase * scale,
              height: 200 * scale,
            }),
          ),
          render: vi.fn(
            ({ canvasContext }: { canvasContext: Fake2dContext }) => {
              const task = createRenderTask(canvasContext);
              return { cancel: task.cancel, promise: task.promise };
            },
          ),
        })),
        destroy: pdfDestroy,
      }),
      destroy: loadingDestroy,
    };
    return loadingTask;
  });
}

configurePdfMock();

function ViewerHarness() {
  const [page, setPage] = useState(1);
  return (
    <PdfViewer
      file={null}
      pageNumber={page}
      pageCount={3}
      onPageChange={setPage}
      fields={[
        {
          name: "a",
          bbox: { page: 2, x0: 0, y0: 0, x1: 10, y1: 10 },
          confidence: 1,
        },
      ]}
      highlighted={null}
      onHighlight={() => {}}
    />
  );
}

function makePdfBlob(tag = "a"): Blob {
  const bytes = new TextEncoder().encode(tag);
  const blob = new Blob([bytes], { type: "application/pdf" });
  Object.defineProperty(blob, "arrayBuffer", {
    value: async () => bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength),
  });
  return blob;
}

describe("PdfViewer multipage", () => {
  it("renders pager and switches pages", async () => {
    const user = userEvent.setup();
    render(<ViewerHarness />);

    expect(screen.getByRole("button", { name: /page 1/i })).toHaveAttribute(
      "aria-current",
      "page",
    );

    await user.click(screen.getByRole("button", { name: /page 2/i }));
    expect(screen.getByRole("button", { name: /page 2/i })).toHaveAttribute(
      "aria-current",
      "page",
    );
  });
});

describe("PdfViewer render lifecycle", () => {
  let loadCount = 0;

  beforeEach(() => {
    installCanvas2dStub();
    renderTasks.length = 0;
    pageRotate = 0;
    pageWidthBase = 100;
    loadCount = 0;
    pdfDestroy = vi.fn(async () => {});
    loadingDestroy = vi.fn();
    visibleDrawImageCalls = 0;
    visibleCanvas = null;
    getDocumentMock.mockClear();
    configurePdfMock();
    getDocumentMock.mockImplementation(() => {
      loadCount += 1;
      const widthForDoc = loadCount === 1 ? 100 : 500;
      const loadingTask = {
        promise: Promise.resolve({
          getPage: vi.fn(async () => ({
            rotate: pageRotate,
            getViewport: vi.fn(
              ({ scale }: { scale: number; rotation?: number }) => ({
                width: widthForDoc * scale,
                height: 200 * scale,
              }),
            ),
            render: vi.fn(
              ({ canvasContext }: { canvasContext: Fake2dContext }) => {
                const task = createRenderTask(canvasContext);
                return { cancel: task.cancel, promise: task.promise };
              },
            ),
          })),
          destroy: pdfDestroy,
        }),
        destroy: loadingDestroy,
      };
      return loadingTask;
    });
  });

  afterEach(() => {
    restoreCanvasStub();
  });

  it("cancels superseded render when file changes while first render is pending", async () => {
    const { container, rerender } = render(
      <PdfViewer
        file={makePdfBlob("one")}
        pageNumber={1}
        pageCount={1}
        onPageChange={() => {}}
        fields={[]}
        highlighted={null}
        onHighlight={() => {}}
      />,
    );

    visibleCanvas = container.querySelector("canvas");

    await waitFor(() => {
      expect(renderTasks.length).toBeGreaterThanOrEqual(1);
    });
    const first = renderTasks[0]!;

    rerender(
      <PdfViewer
        file={makePdfBlob("two")}
        pageNumber={1}
        pageCount={1}
        onPageChange={() => {}}
        fields={[]}
        highlighted={null}
        onHighlight={() => {}}
      />,
    );

    await waitFor(() => {
      expect(first.cancel).toHaveBeenCalled();
      expect(renderTasks.length).toBeGreaterThanOrEqual(2);
    });

    const second = renderTasks[renderTasks.length - 1]!;
    second.resolve();

    await waitFor(() => {
      expect(visibleDrawImageCalls).toBe(1);
    });

    first.resolve();
    await waitFor(() => {
      expect(visibleDrawImageCalls).toBe(1);
    });
  });

  it("does not resize canvas from a stale render that finishes late", async () => {
    const { container, rerender } = render(
      <PdfViewer
        file={makePdfBlob("one")}
        pageNumber={1}
        pageCount={1}
        onPageChange={() => {}}
        fields={[]}
        highlighted={null}
        onHighlight={() => {}}
      />,
    );

    visibleCanvas = container.querySelector("canvas");

    await waitFor(() => expect(renderTasks.length).toBe(1));
    const first = renderTasks[0]!;

    rerender(
      <PdfViewer
        file={makePdfBlob("two")}
        pageNumber={1}
        pageCount={1}
        onPageChange={() => {}}
        fields={[]}
        highlighted={null}
        onHighlight={() => {}}
      />,
    );

    await waitFor(() => expect(renderTasks.length).toBe(2));
    const second = renderTasks[1]!;
    second.resolve();

    await waitFor(() => {
      expect(container.querySelector("canvas")?.width).toBe(500);
    });

    first.resolve();
    await new Promise((r) => setTimeout(r, 0));
    expect(container.querySelector("canvas")?.width).toBe(500);
  });

  it("uses normalised rotation from page.rotate", async () => {
    pageRotate = -90;
    pageWidthBase = 100;
    const rotationArgs: number[] = [];
    getDocumentMock.mockImplementation(() => {
      const loadingTask = {
        promise: Promise.resolve({
          getPage: vi.fn(async () => ({
            rotate: pageRotate,
            getViewport: vi.fn(
              ({ scale, rotation }: { scale: number; rotation?: number }) => {
                rotationArgs.push(rotation ?? 0);
                return {
                  width: pageWidthBase * scale,
                  height: 200 * scale,
                };
              },
            ),
            render: vi.fn(
              ({ canvasContext }: { canvasContext: Fake2dContext }) => {
                const task = createRenderTask(canvasContext);
                return { cancel: task.cancel, promise: task.promise };
              },
            ),
          })),
          destroy: pdfDestroy,
        }),
        destroy: loadingDestroy,
      };
      return loadingTask;
    });

    const { container } = render(
      <PdfViewer
        file={makePdfBlob()}
        pageNumber={1}
        pageCount={1}
        onPageChange={() => {}}
        fields={[
          {
            name: "rot",
            bbox: { page: 1, x0: 0, y0: 0, x1: 10, y1: 10 },
            confidence: 1,
          },
        ]}
        highlighted={null}
        onHighlight={() => {}}
      />,
    );
    visibleCanvas = container.querySelector("canvas");

    await waitFor(() => expect(renderTasks.length).toBe(1));
    renderTasks[0]!.resolve();

    await waitFor(() => {
      expect(screen.getByTitle("rot")).toBeInTheDocument();
    });
    expect(rotationArgs.filter((r) => r === 270).length).toBeGreaterThan(0);
    const btn = screen.getByTitle("rot");
    expect(btn).toHaveStyle({ width: "10px", height: "10px" });
  });

  it("cancels render and destroys document on unmount", async () => {
    const { unmount } = render(
      <PdfViewer
        file={makePdfBlob()}
        pageNumber={1}
        pageCount={1}
        onPageChange={() => {}}
        fields={[]}
        highlighted={null}
        onHighlight={() => {}}
      />,
    );

    await waitFor(() => expect(renderTasks.length).toBe(1));
    const first = renderTasks[0]!;

    unmount();

    expect(first.cancel).toHaveBeenCalled();
    await waitFor(() => {
      expect(pdfDestroy).toHaveBeenCalled();
    });
  });
});
