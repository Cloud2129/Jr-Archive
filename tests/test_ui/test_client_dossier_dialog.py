from __future__ import annotations

from jr_client_archive.application.client_commands import CreateClientRequest, create_client
from jr_client_archive.application.client_queries import get_client
from jr_client_archive.application.custom_field_commands import create_definition
from jr_client_archive.application.document_queries import list_documents_for_client
from jr_client_archive.application.folder_queries import list_folders_for_client
from jr_client_archive.domain.client import ClientCreate
from jr_client_archive.domain.custom_field import CustomFieldDefinitionCreate
from jr_client_archive.domain.enums import CustomFieldType, DocumentStatus, EntityType
from jr_client_archive.ui.dialogs import client_dossier_dialog as dossier_module
from jr_client_archive.ui.dialogs.client_dossier_dialog import ClientDossierDialog


def _create_client(database):
    return create_client(
        database, CreateClientRequest(client=ClientCreate(first_name="Mario", last_name="Rossi")), username="t"
    )


def test_dossier_loads_anagrafica_and_root_folder(qtbot, database, app_paths):
    client = _create_client(database)
    dialog = ClientDossierDialog(database, client, username="t")
    qtbot.addWidget(dialog)

    assert dialog._first_name.text() == "Mario"
    assert dialog._last_name.text() == "Rossi"
    assert dialog._folder_tree.topLevelItemCount() == 1


def test_dossier_prefills_custom_field_values(qtbot, database, app_paths):
    field = create_definition(
        database,
        CustomFieldDefinitionCreate(
            entity_type=EntityType.CLIENT, field_key="referente", label="Referente", field_type=CustomFieldType.TEXT
        ),
        username="t",
    )
    client = create_client(
        database,
        CreateClientRequest(
            client=ClientCreate(first_name="Mario", last_name="Rossi"),
            custom_field_values={field.id: "Giulia Bianchi"},
        ),
        username="t",
    )
    dialog = ClientDossierDialog(database, client, username="t")
    qtbot.addWidget(dialog)

    assert dialog._custom_field_form.values()[field.id] == "Giulia Bianchi"


def test_dossier_creates_subfolder_under_selected_root(qtbot, database, app_paths, monkeypatch):
    client = _create_client(database)
    dialog = ClientDossierDialog(database, client, username="t")
    qtbot.addWidget(dialog)

    root_item = dialog._folder_tree.topLevelItem(0)
    dialog._folder_tree.setCurrentItem(root_item)

    from PySide6.QtWidgets import QInputDialog

    monkeypatch.setattr(QInputDialog, "getText", staticmethod(lambda *a, **k: ("Contratti", True)))
    dialog._on_new_subfolder()

    folders = list_folders_for_client(database, client.id)
    assert len(folders) == 2
    assert dialog._folder_tree.topLevelItem(0).childCount() == 1


def test_dossier_save_updates_client(qtbot, database, app_paths):
    client = _create_client(database)
    dialog = ClientDossierDialog(database, client, username="t")
    qtbot.addWidget(dialog)

    dialog._phone.setText("123456")
    dialog._on_save()

    updated = get_client(database, client.id)
    assert updated.phone == "123456"


def test_dossier_uploads_document_into_root_folder(qtbot, database, app_paths, monkeypatch, tmp_path):
    client = _create_client(database)
    dialog = ClientDossierDialog(database, client, username="t")
    qtbot.addWidget(dialog)

    source = tmp_path / "fattura.pdf"
    source.write_bytes(b"contenuto")
    monkeypatch.setattr(
        dossier_module.QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: (str(source), ""))
    )

    dialog._on_upload_document()

    documents = list_documents_for_client(database, client.id)
    assert len(documents) == 1
    assert documents[0].status == DocumentStatus.TO_VERIFY
    assert dialog._documents_list.count() == 1


def test_dossier_classifies_selected_document(qtbot, database, app_paths, monkeypatch, tmp_path):
    client = _create_client(database)
    dialog = ClientDossierDialog(database, client, username="t")
    qtbot.addWidget(dialog)

    source = tmp_path / "fattura.pdf"
    source.write_bytes(b"contenuto")
    monkeypatch.setattr(
        dossier_module.QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: (str(source), ""))
    )
    dialog._on_upload_document()
    dialog._documents_list.setCurrentRow(0)

    from jr_client_archive.domain.document import DocumentCatalogUpdate

    monkeypatch.setattr(dossier_module.DocumentCatalogDialog, "exec", lambda self: dossier_module.QDialog.DialogCode.Accepted)
    monkeypatch.setattr(
        dossier_module.DocumentCatalogDialog,
        "payload",
        lambda self: DocumentCatalogUpdate(document_type="Fattura", tags=["urgente"]),
    )

    dialog._on_classify_document()

    documents = list_documents_for_client(database, client.id)
    assert documents[0].status == DocumentStatus.CATALOGUED
    assert documents[0].document_type == "Fattura"


def test_dossier_shows_placeholder_when_no_document_selected(qtbot, database, app_paths):
    client = _create_client(database)
    dialog = ClientDossierDialog(database, client, username="t")
    qtbot.addWidget(dialog)

    assert "Seleziona un documento" in dialog._preview_label.text()
    assert dialog._preview_open_button.isVisible() is False


def test_dossier_preview_renders_image_document(qtbot, database, app_paths, monkeypatch, tmp_path):
    from PIL import Image

    client = _create_client(database)
    dialog = ClientDossierDialog(database, client, username="t")
    qtbot.addWidget(dialog)

    source = tmp_path / "foto.png"
    Image.new("RGB", (200, 150), color="red").save(source)
    monkeypatch.setattr(
        dossier_module.QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: (str(source), ""))
    )
    dialog._on_upload_document()
    dialog._documents_list.setCurrentRow(0)

    assert dialog._preview_label.text() == ""
    assert not dialog._preview_label.pixmap().isNull()
    assert dialog._preview_open_button.isHidden() is False


def test_dossier_preview_falls_back_for_unsupported_document(qtbot, database, app_paths, monkeypatch, tmp_path):
    client = _create_client(database)
    dialog = ClientDossierDialog(database, client, username="t")
    qtbot.addWidget(dialog)

    source = tmp_path / "fattura.pdf"
    source.write_bytes(b"non e' un pdf valido")
    monkeypatch.setattr(
        dossier_module.QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: (str(source), ""))
    )
    dialog._on_upload_document()
    dialog._documents_list.setCurrentRow(0)

    assert "non disponibile" in dialog._preview_label.text()
    assert dialog._preview_open_button.isHidden() is False


def test_dossier_preselects_document_via_select_document_id(qtbot, database, app_paths, monkeypatch, tmp_path):
    client = _create_client(database)
    dialog = ClientDossierDialog(database, client, username="t")
    qtbot.addWidget(dialog)

    monkeypatch.setattr(
        dossier_module.QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: (str(tmp_path / "a.pdf"), ""))
    )
    (tmp_path / "a.pdf").write_bytes(b"a")
    dialog._on_upload_document()
    monkeypatch.setattr(
        dossier_module.QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: (str(tmp_path / "b.pdf"), ""))
    )
    (tmp_path / "b.pdf").write_bytes(b"b")
    dialog._on_upload_document()

    second_document_id = next(
        d.id for d in list_documents_for_client(database, client.id) if d.original_filename == "b.pdf"
    )

    preselecting_dialog = ClientDossierDialog(
        database, client, username="t", select_document_id=second_document_id
    )
    qtbot.addWidget(preselecting_dialog)

    selected = preselecting_dialog._selected_document()
    assert selected is not None
    assert selected.id == second_document_id


def test_dossier_open_external_delegates_to_desktop_services(qtbot, database, app_paths, monkeypatch, tmp_path):
    client = _create_client(database)
    dialog = ClientDossierDialog(database, client, username="t")
    qtbot.addWidget(dialog)

    source = tmp_path / "fattura.pdf"
    source.write_bytes(b"non e' un pdf valido")
    monkeypatch.setattr(
        dossier_module.QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: (str(source), ""))
    )
    dialog._on_upload_document()
    dialog._documents_list.setCurrentRow(0)

    opened = {}
    monkeypatch.setattr(
        dossier_module.QDesktopServices, "openUrl", staticmethod(lambda url: opened.setdefault("url", url))
    )
    dialog._on_open_external()

    assert opened["url"].toLocalFile() == str(dialog._preview_path)
