"""create guild_schedule_settings table.

Revision ID: 9b7158520f28
Revises: c897b93f45ce
Create Date: 2022-08-26 22:35:28.930715

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "9b7158520f28"
down_revision = "c897b93f45ce"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Updgrade to 9b7158520f28 revision."""
    op.create_table(
        "guild_schedule_settings",
        sa.Column("guild", sa.Integer, sa.ForeignKey("guilds.id"), nullable=False),
        sa.Column("base_open_message", sa.String(length=60), nullable=False),
        sa.Column("base_close_message", sa.String(length=60), nullable=False),
        sa.Column("warning_time", sa.Integer, nullable=False),
        sa.Column("inactive_time", sa.Integer, nullable=False),
        sa.Column("delay_time", sa.Integer, nullable=False),
    )


def downgrade() -> None:
    """Downgrade to c897b93f45ce revision."""
    op.drop_table("guild_schedule_settings")
