from __future__ import annotations

from datetime import date

from sqlalchemy import Boolean, Date, Enum, Float, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from jr_client_archive.db.base import Base
from jr_client_archive.db.models.mixins import TimestampMixin
from jr_client_archive.domain.enums import CustomFieldType, EntityType


class CustomFieldDefinition(TimestampMixin, Base):
    """User-defined field metadata: this is what makes 'infinite custom
    fields without ever touching the schema' possible. Adding a field is an
    INSERT here, not a migration.
    """

    __tablename__ = "custom_field_definitions"
    __table_args__ = (UniqueConstraint("entity_type", "field_key", name="uq_custom_field_key"),)

    id: Mapped[int] = mapped_column(primary_key=True)

    entity_type: Mapped[EntityType] = mapped_column(Enum(EntityType), index=True)
    field_key: Mapped[str] = mapped_column(String(64))
    label: Mapped[str] = mapped_column(String(128))
    field_type: Mapped[CustomFieldType] = mapped_column(Enum(CustomFieldType))

    is_required: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    # Only populated/used when field_type == CHOICE: list[str] of options.
    choices: Mapped[list[str] | None] = mapped_column(JSON)

    values: Mapped[list["CustomFieldValue"]] = relationship(
        back_populates="definition", cascade="all, delete-orphan"
    )


class CustomFieldValue(Base):
    """One value of one custom field on one entity instance.

    Typed columns (rather than a single text blob) keep filtering/sorting
    by custom field fast and let SQLite enforce sensible storage per type,
    while still requiring zero schema changes when a new field is added.
    """

    __tablename__ = "custom_field_values"
    __table_args__ = (
        UniqueConstraint("field_definition_id", "entity_id", name="uq_custom_field_value_entity"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    field_definition_id: Mapped[int] = mapped_column(
        ForeignKey("custom_field_definitions.id", ondelete="CASCADE"), index=True
    )
    entity_type: Mapped[EntityType] = mapped_column(Enum(EntityType), index=True)
    entity_id: Mapped[int] = mapped_column(Integer, index=True)

    value_text: Mapped[str | None] = mapped_column(String(1024))
    value_number: Mapped[float | None] = mapped_column(Float)
    value_date: Mapped[date | None] = mapped_column(Date)
    value_bool: Mapped[bool | None] = mapped_column(Boolean)

    definition: Mapped["CustomFieldDefinition"] = relationship(back_populates="values")
