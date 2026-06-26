"""Fase 8 - shows the current demo/license status and lets the user paste
a signed license key to activate the full version.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from jr_client_archive.application.license_commands import activate_license
from jr_client_archive.application.license_queries import get_license_status
from jr_client_archive.db.base import Database


class LicenseDialog(QDialog):
    def __init__(self, database: Database, *, username: str, parent=None) -> None:
        super().__init__(parent)
        self._database = database
        self._username = username

        self.setWindowTitle("Licenza")
        self.resize(480, 360)

        self._status_label = QLabel()
        self._status_label.setWordWrap(True)

        self._key_input = QPlainTextEdit()
        self._key_input.setPlaceholderText("Incolla qui la chiave di licenza...")

        activate_button = QPushButton("Attiva licenza")
        activate_button.clicked.connect(self._on_activate_clicked)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.accept)
        buttons.accepted.connect(self.accept)

        layout = QVBoxLayout(self)
        layout.addWidget(self._status_label)
        layout.addWidget(QLabel("Chiave di licenza"))
        layout.addWidget(self._key_input)
        layout.addWidget(activate_button)
        layout.addWidget(buttons)

        self._reload_status()

    def _reload_status(self) -> None:
        status = get_license_status(self._database)
        if status.is_activated:
            self._status_label.setText(f"Licenza attiva{f' a nome di {status.licensee}' if status.licensee else ''}.")
        elif status.is_demo_expired:
            self._status_label.setText(
                "Periodo di valutazione terminato. L'archivio e' in sola lettura: "
                "i dati restano consultabili ma non e' possibile modificarli finche' non si attiva una licenza."
            )
        else:
            self._status_label.setText(
                f"Versione demo - {status.days_remaining} giorni rimanenti. "
                f"Limite di {status.max_demo_clients} clienti durante la valutazione."
            )

    def _on_activate_clicked(self) -> None:
        license_key = self._key_input.toPlainText().strip()
        if not license_key:
            QMessageBox.information(self, "Licenza", "Incolla prima una chiave di licenza valida.")
            return

        try:
            activate_license(self._database, license_key, username=self._username)
        except Exception as exc:
            QMessageBox.critical(self, "Errore", f"Chiave di licenza non valida:\n{exc}")
            return

        self._reload_status()
        QMessageBox.information(self, "Licenza", "Licenza attivata con successo.")
