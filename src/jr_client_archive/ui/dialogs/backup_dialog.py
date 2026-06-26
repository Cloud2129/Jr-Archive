"""Fase 7 - backup & restore.

A backup is a single zip snapshot of the whole data root (database +
client document tree) under ``AppPaths.backups_dir``. Restoring never
deletes anything: whatever is currently on disk gets moved aside into a
dedicated safety folder before the chosen backup is extracted in its
place (see ``services.backup_service``), so a restore is always
reversible by hand even if the wrong backup gets picked.

``restored`` is exposed for ``MainWindow`` to check after ``exec()``: a
restore can swap out the entire database/document tree, so the dashboard
needs a full reload, unlike every other dialog here.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from jr_client_archive.application.backup_commands import create_backup, list_backups, restore_backup
from jr_client_archive.db.base import Database
from jr_client_archive.domain.backup import BackupInfo


class BackupDialog(QDialog):
    def __init__(self, database: Database, *, username: str, parent=None) -> None:
        super().__init__(parent)
        self._database = database
        self._username = username
        self.restored = False

        self.setWindowTitle("Backup e ripristino")
        self.resize(480, 360)

        self._backup_list = QListWidget()

        create_button = QPushButton("Crea backup adesso")
        create_button.clicked.connect(self._on_create_clicked)
        restore_button = QPushButton("Ripristina backup selezionato...")
        restore_button.clicked.connect(self._on_restore_clicked)

        actions_layout = QHBoxLayout()
        actions_layout.addWidget(create_button)
        actions_layout.addWidget(restore_button)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.accept)
        buttons.accepted.connect(self.accept)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Backup disponibili"))
        layout.addWidget(self._backup_list)
        layout.addLayout(actions_layout)
        layout.addWidget(buttons)

        self._reload_backups()

    def _reload_backups(self) -> None:
        self._backup_list.clear()
        backups = list_backups()
        if not backups:
            self._backup_list.addItem("Nessun backup presente.")
            return
        for backup in backups:
            size_mb = backup.size_bytes / (1024 * 1024)
            item = QListWidgetItem(f"{backup.created_at:%d/%m/%Y %H:%M:%S} - {backup.path.name} ({size_mb:.1f} MB)")
            item.setData(Qt.ItemDataRole.UserRole, backup)
            self._backup_list.addItem(item)

    def _selected_backup(self) -> BackupInfo | None:
        item = self._backup_list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _on_create_clicked(self) -> None:
        try:
            create_backup(self._database, username=self._username)
        except Exception as exc:
            QMessageBox.critical(self, "Errore", f"Impossibile creare il backup:\n{exc}")
            return
        self._reload_backups()
        QMessageBox.information(self, "Backup", "Backup creato con successo.")

    def _on_restore_clicked(self) -> None:
        backup = self._selected_backup()
        if backup is None:
            QMessageBox.information(self, "Ripristino", "Seleziona prima un backup dall'elenco.")
            return

        reply = QMessageBox.question(
            self,
            "Conferma ripristino",
            "I dati attuali (database e documenti) verranno spostati in una cartella di sicurezza "
            "e sostituiti dal contenuto del backup selezionato. Continuare?",
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            result = restore_backup(self._database, backup.path, username=self._username)
        except Exception as exc:
            QMessageBox.critical(self, "Errore", f"Impossibile ripristinare il backup:\n{exc}")
            return

        self.restored = True
        self._reload_backups()
        QMessageBox.information(
            self,
            "Ripristino completato",
            f"Ripristino completato. I dati precedenti sono stati conservati in:\n{result.safety_backup_dir}",
        )
