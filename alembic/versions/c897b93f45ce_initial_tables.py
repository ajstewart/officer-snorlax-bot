"""Initial tables.

Revision ID: c897b93f45ce
Revises:
Create Date: 2022-06-04 20:11:35.416806

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "c897b93f45ce"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Upgrade to c897b93f45ce revision."""
    op.create_table(
        "guilds",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("tz", sa.String(length=40), nullable=False),
        sa.Column("admin_channel", sa.Integer, nullable=False),
        sa.Column("meowth_raid_category", sa.Integer, nullable=False),
        sa.Column("any_raids_filter", sa.Boolean, nullable=False),
        sa.Column("log_channel", sa.Integer, nullable=False),
        sa.Column("time_channel", sa.Integer, nullable=False),
        sa.Column("join_name_filter", sa.Boolean, nullable=False),
        sa.Column("active", sa.Boolean, nullable=False),
        sa.Column("prefix", sa.String(length=3), nullable=False),
    )

    op.create_table(
        "schedules",
        sa.Column("guild", sa.Integer, sa.ForeignKey("guilds.id"), nullable=False),
        sa.Column("channel", sa.Integer, nullable=False),
        sa.Column("role", sa.Integer, nullable=False),
        sa.Column("channel_name", sa.String(length=40), nullable=False),
        sa.Column("role_name", sa.String(length=30), nullable=False),
        sa.Column("open", sa.String(length=5), nullable=False),
        sa.Column("close", sa.String(length=5), nullable=False),
        sa.Column("open_message", sa.String(length=255), nullable=False),
        sa.Column("close_message", sa.String(length=255), nullable=False),
        sa.Column("warning", sa.Boolean, nullable=False),
        sa.Column("dynamic", sa.Boolean, nullable=False),
        sa.Column("dynamic_close", sa.String(length=5), nullable=False),
        sa.Column("max_num_delays", sa.Integer, nullable=False),
        sa.Column("current_delay_num", sa.Integer, nullable=False),
        sa.Column("silent", sa.Boolean, nullable=False),
        sa.Column("active", sa.Boolean, nullable=False),
    )

    op.create_table(
        "fc_channels",
        sa.Column("guild", sa.Integer, sa.ForeignKey("guilds.id"), nullable=False),
        sa.Column("channel", sa.Integer, nullable=False),
        sa.Column("channel_name", sa.String(length=40), nullable=False),
        sa.Column("secret", sa.Boolean, nullable=False),
    )


def downgrade():
    """Downgrade to c897b93f45ce revision."""
    op.drop_table("fc_channels")
    op.drop_table("schedules")
    op.drop_table("guilds")
