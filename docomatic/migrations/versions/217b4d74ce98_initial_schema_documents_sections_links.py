"""Initial schema: documents, sections, links

Revision ID: 217b4d74ce98
Revises: 
Create Date: 2025-11-11 18:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = "217b4d74ce98"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Detect database type
    bind = op.get_bind()
    is_postgresql = bind.dialect.name == "postgresql"
    is_sqlite = bind.dialect.name == "sqlite"

    # Use JSONB for PostgreSQL, JSON for SQLite
    if is_postgresql:
        metadata_type = postgresql.JSONB(astext_type=sa.Text())
    else:
        metadata_type = sa.JSON()

    # Use appropriate timestamp defaults
    if is_sqlite:
        created_at_default = sa.text("(datetime('now'))")
        updated_at_default = sa.text("(datetime('now'))")
        timestamp_type = sa.DateTime()
    else:
        created_at_default = sa.text("now()")
        updated_at_default = sa.text("now()")
        timestamp_type = sa.DateTime(timezone=True)

    # Create documents table
    op.create_table(
        "documents",
        sa.Column("id", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("created_at", timestamp_type, server_default=created_at_default, nullable=False),
        sa.Column("updated_at", timestamp_type, server_default=updated_at_default, nullable=False),
        sa.Column("metadata", metadata_type, nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_documents_title"), "documents", ["title"], unique=False)

    # Create sections table
    op.create_table(
        "sections",
        sa.Column("id", sa.String(length=255), nullable=False),
        sa.Column("document_id", sa.String(length=255), nullable=False),
        sa.Column("parent_section_id", sa.String(length=255), nullable=True),
        sa.Column("heading", sa.String(length=500), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("created_at", timestamp_type, server_default=created_at_default, nullable=False),
        sa.Column("updated_at", timestamp_type, server_default=updated_at_default, nullable=False),
        sa.Column("metadata", metadata_type, nullable=True),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["parent_section_id"],
            ["sections.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_sections_document_id"), "sections", ["document_id"], unique=False)
    op.create_index(op.f("ix_sections_parent_section_id"), "sections", ["parent_section_id"], unique=False)
    op.create_index(op.f("ix_sections_order_index"), "sections", ["order_index"], unique=False)

    # Create links table
    op.create_table(
        "links",
        sa.Column("id", sa.String(length=255), nullable=False),
        sa.Column("section_id", sa.String(length=255), nullable=True),
        sa.Column("document_id", sa.String(length=255), nullable=True),
        sa.Column("link_type", sa.String(length=50), nullable=False),
        sa.Column("link_target", sa.String(length=500), nullable=False),
        sa.Column("link_metadata", metadata_type, nullable=True),
        sa.Column("created_at", timestamp_type, server_default=created_at_default, nullable=False),
        sa.Column("updated_at", timestamp_type, server_default=updated_at_default, nullable=False),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["section_id"],
            ["sections.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_links_section_id"), "links", ["section_id"], unique=False)
    op.create_index(op.f("ix_links_document_id"), "links", ["document_id"], unique=False)
    op.create_index(op.f("ix_links_link_type"), "links", ["link_type"], unique=False)
    op.create_index(op.f("ix_links_link_target"), "links", ["link_target"], unique=False)

    # Create full-text search index for PostgreSQL only
    if is_postgresql:
        try:
            op.execute("""
                CREATE INDEX sections_search_idx ON sections 
                USING gin(to_tsvector('english', heading || ' ' || body))
            """)
        except Exception:
            # Index might already exist, ignore
            pass


def downgrade() -> None:
    # Detect database type
    bind = op.get_bind()
    is_postgresql = bind.dialect.name == "postgresql"

    # Drop full-text search index (PostgreSQL only)
    if is_postgresql:
        try:
            op.execute("DROP INDEX IF EXISTS sections_search_idx")
        except Exception:
            # Index might not exist, ignore
            pass

    # Drop indexes
    op.drop_index(op.f("ix_links_link_target"), table_name="links")
    op.drop_index(op.f("ix_links_link_type"), table_name="links")
    op.drop_index(op.f("ix_links_document_id"), table_name="links")
    op.drop_index(op.f("ix_links_section_id"), table_name="links")
    op.drop_index(op.f("ix_sections_order_index"), table_name="sections")
    op.drop_index(op.f("ix_sections_parent_section_id"), table_name="sections")
    op.drop_index(op.f("ix_sections_document_id"), table_name="sections")
    op.drop_index(op.f("ix_documents_title"), table_name="documents")

    # Drop tables
    op.drop_table("links")
    op.drop_table("sections")
    op.drop_table("documents")
