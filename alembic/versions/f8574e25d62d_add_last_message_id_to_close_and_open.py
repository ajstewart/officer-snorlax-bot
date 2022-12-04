"""add last message id to close and open

Revision ID: f8574e25d62d
Revises: 9b7158520f28
Create Date: 2022-09-25 16:52:26.857550

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f8574e25d62d'
down_revision = '9b7158520f28'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("schedules") as batch_op:
        batch_op.add_column(sa.Column('last_open_message', sa.Integer))
        batch_op.add_column(sa.Column('last_close_message', sa.Integer))


def downgrade() -> None:
    with op.batch_alter_table("schedules") as batch_op:
        batch_op.drop_column('last_open_message')
        batch_op.drop_column('last_close_message')
