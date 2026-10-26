"""Persist campaign scan snapshots for findings and approval."""

from alembic import op
import sqlalchemy as sa


revision = "0004_campaign_scans_and_reviews"
down_revision = "0003_campaigns_and_asset_versions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {item["name"] for item in sa.inspect(op.get_bind()).get_columns("scans")}
    if "asset_versions" not in columns:
        with op.batch_alter_table("scans") as batch:
            batch.add_column(sa.Column("asset_versions", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
    columns = {item["name"] for item in sa.inspect(op.get_bind()).get_columns("scans")}
    with op.batch_alter_table("scans") as batch:
        if "progress" not in columns:
            batch.add_column(sa.Column("progress", sa.Integer(), nullable=False, server_default="0"))
        if "cancel_requested" not in columns:
            batch.add_column(sa.Column("cancel_requested", sa.Boolean(), nullable=False, server_default=sa.false()))
        if "completed_asset_ids" not in columns:
            batch.add_column(sa.Column("completed_asset_ids", sa.JSON(), nullable=False, server_default=sa.text("'[]'")))
    review_columns = {item["name"] for item in sa.inspect(op.get_bind()).get_columns("reviews")}
    if "submission_id" not in review_columns:
        with op.batch_alter_table("reviews") as batch:
            batch.add_column(sa.Column("submission_id", sa.String(36), nullable=True))
            batch.create_index("ix_reviews_submission_id", ["submission_id"])


def downgrade() -> None:
    columns = {item["name"] for item in sa.inspect(op.get_bind()).get_columns("scans")}
    if "asset_versions" in columns:
        with op.batch_alter_table("scans") as batch:
            if "cancel_requested" in columns:
                batch.drop_column("cancel_requested")
            if "completed_asset_ids" in columns:
                batch.drop_column("completed_asset_ids")
            if "progress" in columns:
                batch.drop_column("progress")
            batch.drop_column("asset_versions")
    review_columns = {item["name"] for item in sa.inspect(op.get_bind()).get_columns("reviews")}
    if "submission_id" in review_columns:
        with op.batch_alter_table("reviews") as batch:
            batch.drop_index("ix_reviews_submission_id")
            batch.drop_column("submission_id")
