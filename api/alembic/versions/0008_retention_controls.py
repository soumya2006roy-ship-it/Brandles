"""Add configurable organisation data-retention window."""

from alembic import op
import sqlalchemy as sa


revision = "0008_retention_controls"
down_revision = "0007_append_only_audit"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {item["name"] for item in sa.inspect(op.get_bind()).get_columns("organizations")}
    if "retention_days" not in columns:
        with op.batch_alter_table("organizations") as batch:
            batch.add_column(sa.Column("retention_days", sa.Integer(), nullable=False, server_default="365"))


def downgrade() -> None:
    columns = {item["name"] for item in sa.inspect(op.get_bind()).get_columns("organizations")}
    if "retention_days" in columns:
        with op.batch_alter_table("organizations") as batch:
            batch.drop_column("retention_days")
