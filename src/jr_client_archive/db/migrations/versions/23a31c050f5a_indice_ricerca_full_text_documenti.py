"""indice ricerca full-text documenti

Revision ID: 23a31c050f5a
Revises: 6509b93e71a8
Create Date: 2026-06-26 07:47:50.008546

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from jr_client_archive.db.search_index import CREATE_SEARCH_INDEX_SQL, DROP_SEARCH_INDEX_SQL, CREATE_TRIGGERS_SQL


# revision identifiers, used by Alembic.
revision: str = '23a31c050f5a'
down_revision: Union[str, None] = '6509b93e71a8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Same DDL ``Database.create_all`` runs for a brand-new database (see
    # jr_client_archive.db.search_index) - kept in one place so existing
    # installations upgrading via Alembic get the identical FTS5 index.
    for statement in (CREATE_SEARCH_INDEX_SQL, *CREATE_TRIGGERS_SQL):
        op.execute(statement)


def downgrade() -> None:
    for statement in DROP_SEARCH_INDEX_SQL:
        op.execute(statement)
