"""Add private document metadata to organisation submissions."""

from alembic import op
import sqlalchemy as sa


revision = "0014_organization_submission_documents"
down_revision = "0013_organization_submissions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    existing_columns = {column["name"] for column in sa.inspect(bind).get_columns("organization_submissions")}
    columns = (
        sa.Column("document_ref", sa.String(length=500), nullable=True),
        sa.Column("original_filename", sa.String(length=240), nullable=True),
        sa.Column("content_type", sa.String(length=120), nullable=True),
        sa.Column("sha256", sa.String(length=64), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=False, server_default="0"),
    )
    missing_columns = [column for column in columns if column.name not in existing_columns]
    if missing_columns:
        with op.batch_alter_table("organization_submissions") as batch:
            for column in missing_columns:
                batch.add_column(column)


def downgrade() -> None:
    bind = op.get_bind()
    existing_columns = {column["name"] for column in sa.inspect(bind).get_columns("organization_submissions")}
    removable_columns = [
        name
        for name in ("size_bytes", "sha256", "content_type", "original_filename", "document_ref")
        if name in existing_columns
    ]
    if removable_columns:
        with op.batch_alter_table("organization_submissions") as batch:
            for name in removable_columns:
                batch.drop_column(name)
