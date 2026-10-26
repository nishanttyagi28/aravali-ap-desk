"""Ingest document models."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class WordSource(StrEnum):
    TEXT_LAYER = "text_layer"
    OCR = "ocr"


class Word(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str
    page: int = Field(ge=1)
    x0: float
    y0: float
    x1: float
    y1: float
    source: WordSource


class PageInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    width: float = Field(gt=0)
    height: float = Field(gt=0)


class Document(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sha256: str
    page_count: int = Field(ge=1)
    pages: list[PageInfo]
    words: list[Word]
    source_path: str | None = None
