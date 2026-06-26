"""Pydantic DTOs for the Document entity.

``DocumentRead.from_orm_document`` exists instead of a plain
``model_validate(document)`` because ``Document.tags`` is a relationship to
``Tag`` ORM objects, not a list of strings - the UI only ever needs the tag
names, so the conversion happens once, here, rather than in every caller.
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from jr_client_archive.domain.enums import DocumentStatus


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    client_id: int
    folder_id: int
    original_filename: str
    stored_filename: str
    relative_path: str
    extension: str
    size_bytes: int
    checksum_sha256: str
    document_type: str | None = None
    category: str | None = None
    description: str | None = None
    document_date: date | None = None
    uploaded_at: datetime
    uploaded_by: str | None = None
    status: DocumentStatus
    tags: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_orm_document(cls, document) -> "DocumentRead":
        data = {
            column: getattr(document, column)
            for column in (
                "id",
                "client_id",
                "folder_id",
                "original_filename",
                "stored_filename",
                "relative_path",
                "extension",
                "size_bytes",
                "checksum_sha256",
                "document_type",
                "category",
                "description",
                "document_date",
                "uploaded_at",
                "uploaded_by",
                "status",
                "created_at",
                "updated_at",
            )
        }
        data["tags"] = [tag.name for tag in document.tags]
        return cls.model_validate(data)


class DocumentCatalogUpdate(BaseModel):
    document_type: str | None = None
    category: str | None = None
    description: str | None = None
    document_date: date | None = None
    tags: list[str] = Field(default_factory=list)
