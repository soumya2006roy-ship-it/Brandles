"""Add sample workspace isolation and per-membership notification settings."""

from alembic import op
import sqlalchemy as sa


revision = "0006_product_surfaces_and_sample_workspace"
down_revision = "0005_review_submissions_notifications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    org_columns = {item["name"] for item in sa.inspect(op.get_bind()).get_columns("organizations")}
    if "is_sample" not in org_columns:
        with op.batch_alter_table("organizations") as batch:
            batch.add_column(sa.Column("is_sample", sa.Boolean(), nullable=False, server_default=sa.false()))
    member_columns = {item["name"] for item in sa.inspect(op.get_bind()).get_columns("memberships")}
    if "notification_preferences" not in member_columns:
        with op.batch_alter_table("memberships") as batch:
            batch.add_column(sa.Column("notification_preferences", sa.JSON(), nullable=False, server_default=sa.text("'{\"in_app\": true, \"email\": true}'")))


def downgrade() -> None:
    member_columns = {item["name"] for item in sa.inspect(op.get_bind()).get_columns("memberships")}
    if "notification_preferences" in member_columns:
        with op.batch_alter_table("memberships") as batch:
            batch.drop_column("notification_preferences")
    org_columns = {item["name"] for item in sa.inspect(op.get_bind()).get_columns("organizations")}
    if "is_sample" in org_columns:
        with op.batch_alter_table("organizations") as batch:
            batch.drop_column("is_sample")
