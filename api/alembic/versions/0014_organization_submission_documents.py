"""Add private document metadata to organisation submissions."""

from alembic import op
import sqlalchemy as sa


revision = "0014_organization_submission_documents"
down_revision = "0013_organization_submissions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("organization_submissions") as batch:
        batch.add_column(sa.Column("document_ref", sa.String(length=500), nullable=True))
        batch.add_column(sa.Column("original_filename", sa.String(length=240), nullable=True))
        batch.add_column(sa.Column("content_type", sa.String(length=120), nullable=True))
        batch.add_column(sa.Column("sha256", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("size_bytes", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    with op.batch_alter_table("organization_submissions") as batch:
        batch.drop_column("size_bytes")
        batch.drop_column("sha256")
        batch.drop_column("content_type")
        batch.drop_column("original_filename")
        batch.drop_column("document_ref")
