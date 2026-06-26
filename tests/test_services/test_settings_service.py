from __future__ import annotations

from jr_client_archive.config.settings import AppSettings, SettingsService


def test_load_returns_defaults_on_empty_database(database):
    session = database.create_session()
    settings = SettingsService(session).load()
    assert settings == AppSettings()


def test_save_then_load_roundtrips(database):
    session = database.create_session()
    service = SettingsService(session)

    custom = AppSettings(theme="dark_blue", default_username="studio.legale", log_level="DEBUG")
    service.save(custom)

    reloaded = SettingsService(database.create_session()).load()
    assert reloaded == custom
