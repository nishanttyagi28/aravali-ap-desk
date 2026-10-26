"""API metrics snapshot."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class Metrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    invoices_processed: int = Field(ge=0)
    allow_count: int = Field(ge=0)
    review_count: int = Field(ge=0)
    block_count: int = Field(ge=0)
    posted_count: int = Field(ge=0)
    queue_depth: int = Field(ge=0)
