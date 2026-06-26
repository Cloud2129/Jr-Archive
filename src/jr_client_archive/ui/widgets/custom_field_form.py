"""Renders one input widget per custom field definition.

This is the single place that maps a ``CustomFieldType`` to a Qt widget, so
every dialog that needs to show custom fields (new client, client dossier,
tomorrow's "new document" dialog) shares the same behavior instead of each
reinventing its own mapping.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QWidget,
)

from jr_client_archive.domain.custom_field import CustomFieldDefinitionRead
from jr_client_archive.domain.enums import CustomFieldType


class CustomFieldFormWidget(QWidget):
    """A form with one row per definition, pre-filled from ``values``."""

    def __init__(
        self,
        definitions: list[CustomFieldDefinitionRead],
        values: dict[int, Any] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._definitions = definitions
        self._inputs: dict[int, QWidget] = {}
        values = values or {}

        layout = QFormLayout(self)
        for definition in definitions:
            input_widget = self._build_input(definition, values.get(definition.id))
            label = definition.label + (" *" if definition.is_required else "")
            layout.addRow(QLabel(label), input_widget)
            self._inputs[definition.id] = input_widget

    def _build_input(self, definition: CustomFieldDefinitionRead, value: Any) -> QWidget:
        if definition.field_type is CustomFieldType.NUMBER:
            widget = QDoubleSpinBox()
            widget.setRange(-1_000_000_000, 1_000_000_000)
            widget.setDecimals(2)
            if value is not None:
                widget.setValue(float(value))
            return widget
        if definition.field_type is CustomFieldType.DATE:
            widget = QDateEdit()
            widget.setCalendarPopup(True)
            widget.setDate(QDate(value.year, value.month, value.day) if isinstance(value, date) else QDate.currentDate())
            return widget
        if definition.field_type is CustomFieldType.BOOLEAN:
            widget = QCheckBox()
            widget.setChecked(bool(value))
            return widget
        if definition.field_type is CustomFieldType.CHOICE:
            widget = QComboBox()
            widget.addItems(definition.choices or [])
            if value is not None:
                index = widget.findText(str(value))
                if index >= 0:
                    widget.setCurrentIndex(index)
            return widget
        widget = QLineEdit()
        if value is not None:
            widget.setText(str(value))
        return widget

    def validate(self) -> str | None:
        """Returns an error message, or ``None`` if every required field is filled."""
        for definition in self._definitions:
            if not definition.is_required:
                continue
            widget = self._inputs[definition.id]
            if isinstance(widget, QLineEdit) and not widget.text().strip():
                return f"Il campo '{definition.label}' e' obbligatorio."
            if isinstance(widget, QComboBox) and not widget.currentText():
                return f"Il campo '{definition.label}' e' obbligatorio."
        return None

    def values(self) -> dict[int, Any]:
        """Returns ``{field_definition_id: python_value}`` ready for the application layer."""
        result: dict[int, Any] = {}
        for definition in self._definitions:
            widget = self._inputs[definition.id]
            if isinstance(widget, QDoubleSpinBox):
                result[definition.id] = widget.value()
            elif isinstance(widget, QDateEdit):
                result[definition.id] = widget.date().toPython()
            elif isinstance(widget, QCheckBox):
                result[definition.id] = widget.isChecked()
            elif isinstance(widget, QComboBox):
                result[definition.id] = widget.currentText() or None
            elif isinstance(widget, QLineEdit):
                result[definition.id] = widget.text().strip() or None
        return result
