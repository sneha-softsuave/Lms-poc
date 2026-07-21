"""Ingestion API schemas."""

from pydantic import BaseModel


class SegmentOut(BaseModel):
    ordinal: int
    page: int | None = None
    section: str | None = None
    text: str

    class Config:
        from_attributes = True


class DocumentOut(BaseModel):
    id: int
    doc_code: str
    filename: str
    storage_uri: str
    method: str
    char_count: int
    status: str

    class Config:
        from_attributes = True


class DocumentDetail(DocumentOut):
    segments: list[SegmentOut] = []
