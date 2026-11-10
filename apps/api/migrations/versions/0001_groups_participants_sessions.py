"""groups, participants y sessions

Revision ID: 0001
Revises:
Create Date: 2026-11-10 11:59:14.608175

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "groups",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("slug", sa.String(length=10), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("budget", sa.Integer(), nullable=True),
        sa.Column("exchange_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=10), server_default="open", nullable=False),
        sa.Column("admin_participant_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("status IN ('open', 'closed', 'drawn')", name=op.f("ck_groups_status")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_groups")),
        sa.UniqueConstraint("slug", name=op.f("uq_groups_slug")),
    )
    op.create_table(
        "participants",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("group_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=40), nullable=False),
        sa.Column("pin_hash", sa.String(length=200), nullable=False),
        sa.Column("failed_attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("wishlist", sa.Text(), server_default="", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["group_id"],
            ["groups.id"],
            name=op.f("fk_participants_group_id_groups"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_participants")),
    )
    # Índice funcional: el nombre es único dentro del grupo sin distinguir mayúsculas.
    op.create_index(
        "uq_participants_group_id_lower_name",
        "participants",
        ["group_id", sa.literal_column("lower(name)")],
        unique=True,
    )
    # groups y participants se referencian entre sí: esta FK va cuando ya existen las dos.
    op.create_foreign_key(
        op.f("fk_groups_admin_participant_id_participants"),
        "groups",
        "participants",
        ["admin_participant_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_table(
        "sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("participant_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["participant_id"],
            ["participants.id"],
            name=op.f("fk_sessions_participant_id_participants"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sessions")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_sessions_token_hash")),
    )


def downgrade() -> None:
    op.drop_table("sessions")
    op.drop_constraint(
        op.f("fk_groups_admin_participant_id_participants"), "groups", type_="foreignkey"
    )
    op.drop_index("uq_participants_group_id_lower_name", table_name="participants")
    op.drop_table("participants")
    op.drop_table("groups")
