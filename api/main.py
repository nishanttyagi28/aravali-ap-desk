"""FastAPI application matching openapi.yaml."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import Depends, FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as StarletteHTTPException

from api.deps import (
    MAX_UPLOAD_BYTES,
    PDF_MAGIC,
    UPLOAD_DIR,
    AppState,
    build_state,
    cors_origins,
    get_db,
    get_state,
)
from api.services import (
    AlreadyPosted,
    NotPostable,
    apply_review,
    compute_metrics,
    ensure_vendors,
    ingest_upload,
    post_invoice,
    review_queue,
)
from db.repository import get_invoice_row, latest_decision
from docai.contracts.decision import DecisionOutcome
from docai.contracts.errors import ErrorResponse
from docai.contracts.extracted import ExtractedInvoice
from docai.contracts.ledger import LedgerEntry
from docai.contracts.metrics import Metrics
from docai.contracts.review import ReviewAction, ReviewQueueItem, ReviewResult
from docai.contracts.validation import IssueCode
from ledger.posting import InvoiceNotFound


def _default_extractor(path: Path):
    from docai.extract import extract_file

    return extract_file(path)


def create_app(state: AppState | None = None) -> FastAPI:
    app = FastAPI(title="Aravali AP Desk API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins(),
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.app_state = state or build_state()

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        _request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        if isinstance(exc.detail, dict) and "code" in exc.detail:
            body = ErrorResponse.model_validate(exc.detail)
        else:
            body = ErrorResponse(
                code="http_error",
                message=str(exc.detail),
            )
        return JSONResponse(status_code=exc.status_code, content=body.model_dump(mode="json"))

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        body = ErrorResponse(
            code="validation_error",
            message="Request validation failed",
            detail={"errors": exc.errors()},
        )
        return JSONResponse(status_code=422, content=body.model_dump(mode="json"))

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
        body = ErrorResponse(code="internal_error", message="Internal server error")
        return JSONResponse(status_code=500, content=body.model_dump(mode="json"))

    @app.post(
        "/invoices",
        response_model=None,
        responses={
            413: {"description": "Upload exceeds 10 MB"},
            415: {"description": "Not a PDF"},
            422: {"description": "Validation failed"},
            500: {"description": "Internal server error"},
        },
    )
    async def upload_invoice(
        request: Request,
        session: Annotated[Session, Depends(get_db)],
        state: Annotated[AppState, Depends(get_state)],
        file: Annotated[UploadFile, File()],
    ) -> JSONResponse:
        master = ensure_vendors(session, state.vendor_master_path)
        content = await file.read()
        if len(content) > MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=413,
                detail=ErrorResponse(
                    code="payload_too_large",
                    message="Upload exceeds 10 MB",
                ).model_dump(mode="json"),
            )
        if not content.startswith(PDF_MAGIC):
            raise HTTPException(
                status_code=415,
                detail=ErrorResponse(
                    code="unsupported_media_type",
                    message="Not a PDF",
                ).model_dump(mode="json"),
            )
        extract_fn = state.extract_fn or _default_extractor
        try:
            invoice, decision = ingest_upload(
                session,
                content,
                file.filename or "upload.pdf",
                extract_fn,
                master,
                UPLOAD_DIR,
            )
        except Exception as exc:
            body = ErrorResponse(
                code="extraction_failed",
                message=str(exc),
            )
            raise HTTPException(status_code=422, detail=body.model_dump(mode="json")) from exc
        payload = {
            "invoice": invoice.model_dump(mode="json"),
            "decision": decision.model_dump(mode="json"),
        }
        return JSONResponse(content=payload)

    @app.get(
        "/invoices/{invoice_id}",
        responses={
            404: {"description": "Unknown invoice_id"},
            500: {"description": "Internal server error"},
        },
    )
    def get_invoice(
        invoice_id: UUID,
        session: Annotated[Session, Depends(get_db)],
    ) -> dict:
        row = get_invoice_row(session, invoice_id)
        if row is None:
            raise HTTPException(
                status_code=404,
                detail=ErrorResponse(code="not_found", message="Unknown invoice_id").model_dump(
                    mode="json"
                ),
            )
        decision = latest_decision(session, invoice_id)
        inv = ExtractedInvoice.model_validate(row.payload)
        return {
            "invoice": inv.model_dump(mode="json"),
            "decision": decision.model_dump(mode="json") if decision else None,
        }

    @app.get(
        "/invoices/{invoice_id}/file",
        responses={
            404: {"description": "Unknown invoice_id"},
            500: {"description": "Internal server error"},
        },
    )
    def get_invoice_file(
        invoice_id: UUID,
        session: Annotated[Session, Depends(get_db)],
    ) -> FileResponse:
        row = get_invoice_row(session, invoice_id)
        if row is None:
            raise HTTPException(
                status_code=404,
                detail=ErrorResponse(code="not_found", message="Unknown invoice_id").model_dump(
                    mode="json"
                ),
            )
        path = Path(row.file_path)
        if not path.is_file():
            raise HTTPException(
                status_code=404,
                detail=ErrorResponse(code="not_found", message="Original file missing").model_dump(
                    mode="json"
                ),
            )
        return FileResponse(path, media_type="application/pdf", filename=row.source_file)

    @app.get("/review-queue", responses={500: {"description": "Internal server error"}})
    def list_review_queue(
        session: Annotated[Session, Depends(get_db)],
        state: Annotated[AppState, Depends(get_state)],
        decision: Annotated[list[DecisionOutcome] | None, Query()] = None,
        issue_code: Annotated[list[IssueCode] | None, Query()] = None,
    ) -> list[ReviewQueueItem]:
        master = ensure_vendors(session, state.vendor_master_path)
        return review_queue(session, master, decision, issue_code)

    @app.post(
        "/invoices/{invoice_id}/review",
        responses={
            404: {"description": "Unknown invoice_id"},
            409: {"description": "Conflict"},
            422: {"description": "Validation failed"},
            500: {"description": "Internal server error"},
        },
    )
    def review_invoice(
        invoice_id: UUID,
        body: ReviewAction,
        session: Annotated[Session, Depends(get_db)],
        state: Annotated[AppState, Depends(get_state)],
    ) -> ReviewResult:
        master = ensure_vendors(session, state.vendor_master_path)
        try:
            return apply_review(session, invoice_id, body, master)
        except KeyError:
            raise HTTPException(
                status_code=404,
                detail=ErrorResponse(code="not_found", message="Unknown invoice_id").model_dump(
                    mode="json"
                ),
            ) from None
        except ValueError as exc:
            if str(exc) == "block_conflict":
                raise HTTPException(
                    status_code=409,
                    detail=ErrorResponse(
                        code="review_conflict",
                        message="Cannot approve while BLOCK-level issues remain",
                    ).model_dump(mode="json"),
                ) from exc
            raise

    @app.post(
        "/invoices/{invoice_id}/post",
        responses={
            404: {"description": "Unknown invoice_id"},
            409: {"description": "Not postable or already posted"},
            500: {"description": "Internal server error"},
        },
    )
    def post_invoice_endpoint(
        invoice_id: UUID,
        session: Annotated[Session, Depends(get_db)],
    ) -> LedgerEntry:
        try:
            return post_invoice(session, invoice_id)
        except InvoiceNotFound:
            raise HTTPException(
                status_code=404,
                detail=ErrorResponse(code="not_found", message="Unknown invoice_id").model_dump(
                    mode="json"
                ),
            ) from None
        except AlreadyPosted:
            raise HTTPException(
                status_code=409,
                detail=ErrorResponse(
                    code="already_posted",
                    message="Invoice already posted",
                ).model_dump(mode="json"),
            ) from None
        except NotPostable as exc:
            raise HTTPException(
                status_code=409,
                detail=ErrorResponse(
                    code="not_postable",
                    message=str(exc),
                ).model_dump(mode="json"),
            ) from None

    @app.get("/metrics", responses={500: {"description": "Internal server error"}})
    def get_metrics(session: Annotated[Session, Depends(get_db)]) -> Metrics:
        return compute_metrics(session)

    return app


app = create_app()
