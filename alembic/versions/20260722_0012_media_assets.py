"""media assets and profile image URLs

Revision ID: 0012
Revises: 0011, bdff83c8b7ae
Create Date: 2026-07-22

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0012"
down_revision: str | tuple[str, str] | None = ("0011", "bdff83c8b7ae")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("profile_picture_url", sa.Text(), nullable=True))
    op.add_column("schools", sa.Column("logo_url", sa.Text(), nullable=True))
    op.create_table(
        "media_assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_type", sa.String(length=64), nullable=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("asset_type", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=True),
        sa.Column("mime_type", sa.String(length=180), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_media_assets_owner_type", "media_assets", ["owner_type"])
    op.create_index("ix_media_assets_owner_id", "media_assets", ["owner_id"])
    op.create_index("ix_media_assets_asset_type", "media_assets", ["asset_type"])
    op.create_index("ix_media_assets_is_active", "media_assets", ["is_active"])
    op.create_index(
        "ix_media_assets_owner",
        "media_assets",
        ["owner_type", "owner_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_media_assets_owner", table_name="media_assets")
    op.drop_index("ix_media_assets_is_active", table_name="media_assets")
    op.drop_index("ix_media_assets_asset_type", table_name="media_assets")
    op.drop_index("ix_media_assets_owner_id", table_name="media_assets")
    op.drop_index("ix_media_assets_owner_type", table_name="media_assets")
    op.drop_table("media_assets")
    op.drop_column("schools", "logo_url")
    op.drop_column("users", "profile_picture_url")
