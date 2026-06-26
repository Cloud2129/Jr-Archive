"""licenza & demo

Revision ID: fe435e96ab6a
Revises: 23a31c050f5a
Create Date: 2026-06-26 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fe435e96ab6a'
down_revision: Union[str, None] = '23a31c050f5a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'license_state',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('first_launch_at', sa.DateTime(), nullable=False),
        sa.Column('license_key', sa.String(length=2048), nullable=True),
        sa.Column('activated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('license_state')
