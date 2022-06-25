"""drop admin channel

Revision ID: 3411c3047e1a
Revises: c897b93f45ce
Create Date: 2022-06-25 14:35:27.278772

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3411c3047e1a'
down_revision = 'c897b93f45ce'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column('guilds', 'admin_channel')


def downgrade() -> None:
    op.add_column('guilds', sa.Column('admin_channel', sa.Integer, nullable=False))
