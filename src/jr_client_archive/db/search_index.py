"""Raw-SQL FTS5 index backing the global document search (Fase 6).

Deliberately outside the SQLAlchemy ORM models: an FTS5 virtual table is a
search index, not an entity with meaningful Python-side columns, and
``Base.metadata`` only knows how to describe ordinary tables. It's also a
*standalone* (non "external content") FTS5 table, fully populated by
triggers, rather than one tied via ``content=`` to ``documents``: the
``tags_text`` column has no 1:1 column on ``documents`` (it's an aggregate
over the many-to-many ``document_tags`` table), which the external-content
mechanism can't express.

The DDL below must exist both for a brand-new database (``Database.
create_all``, which is also what every test fixture uses) and for an
existing installation upgrading via Alembic - see the migration that calls
``ensure_search_index`` too. Every statement is ``IF NOT EXISTS`` so calling
this more than once is always safe.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine

CREATE_SEARCH_INDEX_SQL = """
CREATE VIRTUAL TABLE IF NOT EXISTS document_search_index USING fts5(
    document_id UNINDEXED,
    original_filename,
    stored_filename,
    document_type,
    category,
    description,
    tags_text
)
"""

CREATE_TRIGGERS_SQL = (
    """
    CREATE TRIGGER IF NOT EXISTS document_search_index_ai AFTER INSERT ON documents BEGIN
        DELETE FROM document_search_index WHERE document_id = new.id;
        INSERT INTO document_search_index
            (document_id, original_filename, stored_filename, document_type, category, description, tags_text)
        SELECT d.id, d.original_filename, d.stored_filename, d.document_type, d.category, d.description,
            COALESCE((SELECT group_concat(t.name, ' ') FROM tags t
                      JOIN document_tags dt ON dt.tag_id = t.id WHERE dt.document_id = d.id), '')
        FROM documents d WHERE d.id = new.id;
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS document_search_index_au AFTER UPDATE ON documents BEGIN
        DELETE FROM document_search_index WHERE document_id = new.id;
        INSERT INTO document_search_index
            (document_id, original_filename, stored_filename, document_type, category, description, tags_text)
        SELECT d.id, d.original_filename, d.stored_filename, d.document_type, d.category, d.description,
            COALESCE((SELECT group_concat(t.name, ' ') FROM tags t
                      JOIN document_tags dt ON dt.tag_id = t.id WHERE dt.document_id = d.id), '')
        FROM documents d WHERE d.id = new.id;
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS document_search_index_ad AFTER DELETE ON documents BEGIN
        DELETE FROM document_search_index WHERE document_id = old.id;
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS document_search_index_tags_ai AFTER INSERT ON document_tags BEGIN
        DELETE FROM document_search_index WHERE document_id = new.document_id;
        INSERT INTO document_search_index
            (document_id, original_filename, stored_filename, document_type, category, description, tags_text)
        SELECT d.id, d.original_filename, d.stored_filename, d.document_type, d.category, d.description,
            COALESCE((SELECT group_concat(t.name, ' ') FROM tags t
                      JOIN document_tags dt ON dt.tag_id = t.id WHERE dt.document_id = d.id), '')
        FROM documents d WHERE d.id = new.document_id;
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS document_search_index_tags_ad AFTER DELETE ON document_tags BEGIN
        DELETE FROM document_search_index WHERE document_id = old.document_id;
        INSERT INTO document_search_index
            (document_id, original_filename, stored_filename, document_type, category, description, tags_text)
        SELECT d.id, d.original_filename, d.stored_filename, d.document_type, d.category, d.description,
            COALESCE((SELECT group_concat(t.name, ' ') FROM tags t
                      JOIN document_tags dt ON dt.tag_id = t.id WHERE dt.document_id = d.id), '')
        FROM documents d WHERE d.id = old.document_id;
    END
    """,
)

DROP_SEARCH_INDEX_SQL = (
    "DROP TRIGGER IF EXISTS document_search_index_tags_ad",
    "DROP TRIGGER IF EXISTS document_search_index_tags_ai",
    "DROP TRIGGER IF EXISTS document_search_index_ad",
    "DROP TRIGGER IF EXISTS document_search_index_au",
    "DROP TRIGGER IF EXISTS document_search_index_ai",
    "DROP TABLE IF EXISTS document_search_index",
)


def ensure_search_index(bind: Engine | Connection) -> None:
    statements = (CREATE_SEARCH_INDEX_SQL, *CREATE_TRIGGERS_SQL)
    if isinstance(bind, Engine):
        with bind.begin() as connection:
            for statement in statements:
                connection.execute(text(statement))
    else:
        for statement in statements:
            bind.execute(text(statement))
