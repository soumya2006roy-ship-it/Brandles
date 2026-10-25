"""Add campaign planning fields, validated asset versions and tenant constraints."""

from alembic import op
import sqlalchemy as sa


revision = "0003_campaigns_and_asset_versions"
down_revision = "0002_approved_sources_and_rules"
branch_labels = None
depends_on = None


def _columns(table: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table)}


def _foreign_keys(table: str) -> set[str | None]:
    return {item.get("name") for item in sa.inspect(op.get_bind()).get_foreign_keys(table)}


def upgrade() -> None:
    if "channels" not in _columns("campaigns"):
        with op.batch_alter_table("campaigns") as batch:
            batch.add_column(sa.Column("channels", sa.JSON(), server_default=sa.text("'[]'"), nullable=False))
            batch.add_column(sa.Column("starts_at", sa.Date(), nullable=True))
            batch.add_column(sa.Column("ends_at", sa.Date(), nullable=True))
            batch.add_column(sa.Column("language", sa.String(32), server_default="en", nullable=False))
            batch.create_check_constraint("ck_campaign_date_window", "ends_at IS NULL OR starts_at IS NULL OR ends_at >= starts_at")

    if "asset_group_id" not in _columns("assets"):
        with op.batch_alter_table("assets") as batch:
            batch.add_column(sa.Column("asset_group_id", sa.String(36), nullable=True))
            batch.add_column(sa.Column("current", sa.Boolean(), server_default=sa.true(), nullable=False))
            batch.add_column(sa.Column("supersedes_asset_id", sa.String(36), nullable=True))
            batch.add_column(sa.Column("original_filename", sa.String(240), nullable=True))
            batch.add_column(sa.Column("content_type", sa.String(120), server_default="text/plain", nullable=False))
            batch.add_column(sa.Column("sha256", sa.String(64), server_default="", nullable=False))
            batch.add_column(sa.Column("size_bytes", sa.Integer(), server_default="0", nullable=False))
            batch.add_column(sa.Column("malware_status", sa.String(20), server_default="not_configured", nullable=False))
            batch.add_column(sa.Column("extraction_status", sa.String(20), server_default="not_required", nullable=False))
            batch.add_column(sa.Column("metadata_stripped", sa.Boolean(), server_default=sa.false(), nullable=False))
            batch.add_column(sa.Column("extracted_text", sa.Text(), nullable=True))
            batch.add_column(sa.Column("logo_matches", sa.JSON(), server_default=sa.text("'[]'"), nullable=False))
            batch.create_unique_constraint("uq_asset_org_id", ["organization_id", "id"])
        op.execute("UPDATE assets SET asset_group_id = id WHERE asset_group_id IS NULL")
        with op.batch_alter_table("assets") as batch:
            batch.alter_column("asset_group_id", existing_type=sa.String(36), nullable=False)
            batch.create_unique_constraint("uq_asset_group_version", ["organization_id", "campaign_id", "asset_group_id", "version"])
            batch.create_check_constraint("ck_assets_type", "asset_type IN ('text','image','document')")
            batch.create_check_constraint("ck_asset_version_size", "version > 0 AND size_bytes >= 0")
            batch.create_check_constraint("ck_asset_malware_status", "malware_status IN ('not_configured','not_applicable','clean')")
            batch.create_check_constraint("ck_asset_extraction_status", "extraction_status IN ('complete','not_required','not_configured','unavailable','failed')")
            batch.create_foreign_key("fk_asset_supersedes_tenant", "assets", ["organization_id", "supersedes_asset_id"], ["organization_id", "id"], ondelete="RESTRICT")
            batch.create_index("ix_assets_org_group_current", ["organization_id", "asset_group_id", "current"])

    inspector = sa.inspect(op.get_bind())
    campaigns_unique = {constraint.get("name") for constraint in inspector.get_unique_constraints("campaigns")}
    if "uq_campaign_org_id" not in campaigns_unique:
        with op.batch_alter_table("campaigns") as batch:
            batch.create_unique_constraint("uq_campaign_org_id", ["organization_id", "id"])

    for table, unique_name in (("scans", "uq_scan_org_id"), ("findings", "uq_finding_org_id")):
        names = {constraint.get("name") for constraint in sa.inspect(op.get_bind()).get_unique_constraints(table)}
        if unique_name not in names:
            with op.batch_alter_table(table) as batch:
                batch.create_unique_constraint(unique_name, ["organization_id", "id"])

    if "fk_scan_campaign_tenant" not in _foreign_keys("scans"):
        with op.batch_alter_table("scans") as batch:
            batch.create_foreign_key("fk_scan_campaign_tenant", "campaigns", ["organization_id", "campaign_id"], ["organization_id", "id"], ondelete="CASCADE")
            batch.create_foreign_key("fk_scan_asset_tenant", "assets", ["organization_id", "asset_id"], ["organization_id", "id"], ondelete="CASCADE")

    if "fk_finding_scan_tenant" not in _foreign_keys("findings"):
        with op.batch_alter_table("findings") as batch:
            batch.create_foreign_key("fk_finding_scan_tenant", "scans", ["organization_id", "scan_id"], ["organization_id", "id"], ondelete="CASCADE")
            batch.create_foreign_key("fk_finding_asset_tenant", "assets", ["organization_id", "asset_id"], ["organization_id", "id"], ondelete="CASCADE")
            batch.create_foreign_key("fk_finding_passage_tenant", "source_passages", ["organization_id", "source_passage_id"], ["organization_id", "id"], ondelete="RESTRICT")

    if "fk_guideline_suggestion_source_tenant" not in _foreign_keys("guideline_update_suggestions"):
        with op.batch_alter_table("guideline_update_suggestions") as batch:
            batch.create_foreign_key("fk_guideline_suggestion_source_tenant", "brand_guideline_sources", ["organization_id", "source_id"], ["organization_id", "id"], ondelete="RESTRICT")


def downgrade() -> None:
    if "fk_guideline_suggestion_source_tenant" in _foreign_keys("guideline_update_suggestions"):
        with op.batch_alter_table("guideline_update_suggestions") as batch:
            batch.drop_constraint("fk_guideline_suggestion_source_tenant", type_="foreignkey")
    if "fk_finding_scan_tenant" in _foreign_keys("findings"):
        with op.batch_alter_table("findings") as batch:
            batch.drop_constraint("fk_finding_scan_tenant", type_="foreignkey")
            batch.drop_constraint("fk_finding_asset_tenant", type_="foreignkey")
            batch.drop_constraint("fk_finding_passage_tenant", type_="foreignkey")
    if "fk_scan_campaign_tenant" in _foreign_keys("scans"):
        with op.batch_alter_table("scans") as batch:
            batch.drop_constraint("fk_scan_campaign_tenant", type_="foreignkey")
            batch.drop_constraint("fk_scan_asset_tenant", type_="foreignkey")
    with op.batch_alter_table("findings") as batch:
        batch.drop_constraint("uq_finding_org_id", type_="unique")
    with op.batch_alter_table("scans") as batch:
        batch.drop_constraint("uq_scan_org_id", type_="unique")
    if "asset_group_id" in _columns("assets"):
        with op.batch_alter_table("assets") as batch:
            batch.drop_index("ix_assets_org_group_current")
            batch.drop_constraint("fk_asset_supersedes_tenant", type_="foreignkey")
            batch.drop_constraint("ck_asset_version_size", type_="check")
            batch.drop_constraint("ck_asset_malware_status", type_="check")
            batch.drop_constraint("ck_asset_extraction_status", type_="check")
            batch.drop_constraint("ck_assets_type", type_="check")
            batch.drop_constraint("uq_asset_group_version", type_="unique")
            batch.drop_constraint("uq_asset_org_id", type_="unique")
            for column in ("logo_matches", "extracted_text", "metadata_stripped", "extraction_status", "malware_status", "size_bytes", "sha256", "content_type", "original_filename", "supersedes_asset_id", "current", "asset_group_id"):
                batch.drop_column(column)
    if "channels" in _columns("campaigns"):
        with op.batch_alter_table("campaigns") as batch:
            batch.drop_constraint("ck_campaign_date_window", type_="check")
            for column in ("language", "ends_at", "starts_at", "channels"):
                batch.drop_column(column)
