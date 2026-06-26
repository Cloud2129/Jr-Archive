"""Small form for classifying a 'TO_VERIFY' document.

Collects the fields the naming pattern and the catalog need
(document_type/category/description/document_date/tags) into a
``DocumentCatalogUpdate``; the actual rename + status flip happens in
``catalog_document`` (application layer), not here.
"""

from __future__ import annotations

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QPlainTextEdit,
    QVBoxLayout,
)

from jr_client_archive.domain.document import DocumentCatalogUpdate, DocumentRead


class DocumentCatalogDialog(QDialog):
    def __init__(self, document: DocumentRead, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Classifica - {document.original_filename}")

        self._document_type = QLineEdit(document.document_type or "")
        self._category = QLineEdit(document.category or "")
        self._description = QPlainTextEdit(document.description or "")
        self._document_date = QDateEdit()
        self._document_date.setCalendarPopup(True)
        if document.document_date:
            self._document_date.setDate(
                QDate(document.document_date.year, document.document_date.month, document.document_date.day)
            )
        else:
            self._document_date.setDate(QDate.currentDate())
        self._tags = QLineEdit(", ".join(document.tags))

        form = QFormLayout()
        form.addRow("Tipo documento", self._document_type)
        form.addRow("Categoria", self._category)
        form.addRow("Descrizione", self._description)
        form.addRow("Data documento", self._document_date)
        form.addRow("Tag (separati da virgola)", self._tags)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def payload(self) -> DocumentCatalogUpdate:
        tags = [tag.strip() for tag in self._tags.text().split(",") if tag.strip()]
        return DocumentCatalogUpdate(
            document_type=self._document_type.text().strip() or None,
            category=self._category.text().strip() or None,
            description=self._description.toPlainText().strip() or None,
            document_date=self._document_date.date().toPython(),
            tags=tags,
        )
