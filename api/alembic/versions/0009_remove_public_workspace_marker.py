"""Retire the unauthenticated public workspace marker."""

from alembic import op
import sqlalchemy as sa


revision = "0009_remove_public_workspace_marker"
down_revision = "0008_retention_controls"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {item["name"] for item in sa.inspect(op.get_bind()).get_columns("organizations")}
    if "is_sample" in columns:
        op.execute(sa.text("UPDATE organizations SET deleted_at = CURRENT_TIMESTAMP, verification_status = 'rejected' WHERE is_sample = true AND deleted_at IS NULL"))
        with op.batch_alter_table("organizations") as batch:
            batch.drop_column("is_sample")


def downgrade() -> None:
    columns = {item["name"] for item in sa.inspect(op.get_bind()).get_columns("organizations")}
    if "is_sample" not in columns:
        with op.batch_alter_table("organizations") as batch:
            batch.add_column(sa.Column("is_sample", sa.Boolean(), nullable=False, server_default=sa.false()))
