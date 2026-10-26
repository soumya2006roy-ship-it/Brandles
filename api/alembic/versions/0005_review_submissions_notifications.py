"""Persist review submissions and exact scan references."""

from alembic import op
import sqlalchemy as sa


revision = "0005_review_submissions_notifications"
down_revision = "0004_campaign_scans_and_reviews"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {item["name"] for item in sa.inspect(op.get_bind()).get_columns("reviews")}
    if "submitted_by_user_id" not in columns or "scan_id" not in columns:
        with op.batch_alter_table("reviews") as batch:
            if "submitted_by_user_id" not in columns:
                batch.add_column(sa.Column("submitted_by_user_id", sa.String(36), nullable=True))
                batch.create_foreign_key("fk_review_submitted_by", "users", ["submitted_by_user_id"], ["id"], ondelete="SET NULL")
            if "scan_id" not in columns:
                batch.add_column(sa.Column("scan_id", sa.String(36), nullable=True))
                batch.create_foreign_key("fk_review_scan_tenant", "scans", ["organization_id", "scan_id"], ["organization_id", "id"], ondelete="CASCADE")
                batch.create_foreign_key("fk_review_asset_tenant", "assets", ["organization_id", "asset_id"], ["organization_id", "id"], ondelete="CASCADE")
            batch.alter_column("reviewer_user_id", existing_type=sa.String(36), nullable=True)
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "notifications" not in tables:
        op.create_table(
            "notifications",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("organization_id", sa.String(length=36), nullable=False),
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.Column("kind", sa.String(length=60), nullable=False),
            sa.Column("payload", sa.JSON(), nullable=False),
            sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_notifications_org_user_created", "notifications", ["organization_id", "user_id", "created_at"])


def downgrade() -> None:
    if "notifications" in sa.inspect(op.get_bind()).get_table_names():
        op.drop_index("ix_notifications_org_user_created", table_name="notifications")
        op.drop_table("notifications")
    foreign_keys = {item.get("name") for item in sa.inspect(op.get_bind()).get_foreign_keys("reviews")}
    columns = {item["name"] for item in sa.inspect(op.get_bind()).get_columns("reviews")}
    if "scan_id" in columns or "submitted_by_user_id" in columns:
        with op.batch_alter_table("reviews") as batch:
            if "fk_review_asset_tenant" in foreign_keys:
                batch.drop_constraint("fk_review_asset_tenant", type_="foreignkey")
            if "fk_review_scan_tenant" in foreign_keys:
                batch.drop_constraint("fk_review_scan_tenant", type_="foreignkey")
            if "fk_review_submitted_by" in foreign_keys:
                batch.drop_constraint("fk_review_submitted_by", type_="foreignkey")
            if "scan_id" in columns:
                batch.drop_column("scan_id")
            if "submitted_by_user_id" in columns:
                batch.drop_column("submitted_by_user_id")
            batch.alter_column("reviewer_user_id", existing_type=sa.String(36), nullable=False)
