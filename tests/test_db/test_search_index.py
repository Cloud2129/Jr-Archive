from __future__ import annotations

from sqlalchemy import text


def test_create_all_creates_search_index_table_and_triggers(database, app_paths):
    with database.engine.connect() as connection:
        tables = {
            row[0]
            for row in connection.execute(
                text("SELECT name FROM sqlite_master WHERE type IN ('table', 'view')")
            )
        }
        triggers = {
            row[0]
            for row in connection.execute(text("SELECT name FROM sqlite_master WHERE type = 'trigger'"))
        }

    assert "document_search_index" in tables
    assert {
        "document_search_index_ai",
        "document_search_index_au",
        "document_search_index_ad",
        "document_search_index_tags_ai",
        "document_search_index_tags_ad",
    } <= triggers


def test_create_all_is_idempotent(database, app_paths):
    database.create_all()
    database.create_all()
