"""Add source versioning, passage locations and reviewable rules."""

from alembic import op
import sqlalchemy as sa


revision = "0002_approved_sources_and_rules"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    source_columns = {column["name"] for column in inspector.get_columns("brand_guideline_sources")}
    if "family_id" not in source_columns:
        with op.batch_alter_table("brand_guideline_sources") as batch:
            batch.add_column(sa.Column("family_id", sa.String(36), nullable=True))
            batch.add_column(sa.Column("original_filename", sa.String(240), server_default="source-document", nullable=False))
            batch.add_column(sa.Column("content_type", sa.String(120), server_default="application/octet-stream", nullable=False))
            batch.add_column(sa.Column("sha256", sa.String(64), server_default="", nullable=False))
            batch.add_column(sa.Column("size_bytes", sa.Integer(), server_default="0", nullable=False))
            batch.add_column(sa.Column("approved_by", sa.String(36), nullable=True))
            batch.add_column(sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True))
            batch.alter_column("effective_from", existing_type=sa.DateTime(timezone=True), type_=sa.Date(), existing_nullable=True)
            batch.alter_column("effective_to", existing_type=sa.DateTime(timezone=True), type_=sa.Date(), existing_nullable=True)
            batch.drop_constraint("uq_source_org_version", type_="unique")
            batch.drop_constraint("brand_guideline_sources_created_by_fkey", type_="foreignkey")
            batch.create_foreign_key("brand_guideline_sources_created_by_fkey", "users", ["created_by"], ["id"], ondelete="RESTRICT")
            batch.create_foreign_key("brand_guideline_sources_approved_by_fkey", "users", ["approved_by"], ["id"], ondelete="SET NULL")
            batch.create_unique_constraint("uq_source_org_id", ["organization_id", "id"])
            batch.create_check_constraint("ck_sources_status", "status IN ('draft','approved','archived')")
            batch.create_check_constraint("ck_source_effective_window", "effective_to IS NULL OR effective_from IS NULL OR effective_to >= effective_from")

        op.execute("UPDATE brand_guideline_sources SET family_id = id WHERE family_id IS NULL")
        with op.batch_alter_table("brand_guideline_sources") as batch:
            batch.alter_column("family_id", existing_type=sa.String(36), nullable=False)
            batch.create_unique_constraint("uq_source_family_version", ["organization_id", "family_id", "version"])
            batch.create_index("ix_sources_org_family", ["organization_id", "family_id", "version"])

    inspector = sa.inspect(op.get_bind())
    passage_columns = {column["name"] for column in inspector.get_columns("source_passages")}
    if "location_label" not in passage_columns:
        with op.batch_alter_table("source_passages") as batch:
            batch.add_column(sa.Column("location_label", sa.String(120), nullable=True))
            batch.add_column(sa.Column("start_offset", sa.Integer(), nullable=True))
            batch.add_column(sa.Column("end_offset", sa.Integer(), nullable=True))
            batch.drop_constraint("source_passages_source_id_fkey", type_="foreignkey")
            batch.create_foreign_key("fk_passage_source_tenant", "brand_guideline_sources", ["organization_id", "source_id"], ["organization_id", "id"], ondelete="CASCADE")
            batch.create_unique_constraint("uq_source_passage_org_id", ["organization_id", "id"])

    inspector = sa.inspect(op.get_bind())
    rule_constraints = inspector.get_check_constraints("rules")
    rule_checks = " ".join(constraint.get("sqltext", "") for constraint in rule_constraints)
    rule_fks = {foreign_key.get("name") for foreign_key in inspector.get_foreign_keys("rules")}
    if "rejected" not in rule_checks or "fk_rule_passage_tenant" not in rule_fks:
        with op.batch_alter_table("rules") as batch:
            batch.drop_constraint("ck_rules_status", type_="check")
            batch.drop_constraint("rules_source_passage_id_fkey", type_="foreignkey")
            batch.create_check_constraint("ck_rules_status", "status IN ('draft','suggested','active','archived','rejected')")
            batch.create_check_constraint("ck_rules_valid_window", "valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from")
            batch.create_foreign_key("fk_rule_passage_tenant", "source_passages", ["organization_id", "source_passage_id"], ["organization_id", "id"], ondelete="RESTRICT")
            batch.alter_column("valid_from", existing_type=sa.DateTime(timezone=True), type_=sa.Date(), existing_nullable=True)
            batch.alter_column("valid_to", existing_type=sa.DateTime(timezone=True), type_=sa.Date(), existing_nullable=True)


def downgrade() -> None:
    with op.batch_alter_table("rules") as batch:
        batch.drop_constraint("fk_rule_passage_tenant", type_="foreignkey")
        batch.drop_constraint("ck_rules_status", type_="check")
        batch.create_check_constraint("ck_rules_status", "status IN ('draft','active','archived')")
        batch.create_foreign_key("rules_source_passage_id_fkey", "source_passages", ["source_passage_id"], ["id"], ondelete="SET NULL")
        batch.alter_column("valid_from", existing_type=sa.Date(), type_=sa.DateTime(timezone=True), existing_nullable=True)
        batch.alter_column("valid_to", existing_type=sa.Date(), type_=sa.DateTime(timezone=True), existing_nullable=True)

    with op.batch_alter_table("source_passages") as batch:
        batch.drop_constraint("uq_source_passage_org_id", type_="unique")
        batch.drop_constraint("fk_passage_source_tenant", type_="foreignkey")
        batch.create_foreign_key("source_passages_source_id_fkey", "brand_guideline_sources", ["source_id"], ["id"], ondelete="CASCADE")
        batch.drop_column("end_offset")
        batch.drop_column("start_offset")
        batch.drop_column("location_label")

    with op.batch_alter_table("brand_guideline_sources") as batch:
        batch.drop_index("ix_sources_org_family")
        batch.drop_constraint("uq_source_family_version", type_="unique")
        batch.drop_constraint("ck_sources_status", type_="check")
        batch.drop_constraint("uq_source_org_id", type_="unique")
        batch.drop_constraint("brand_guideline_sources_approved_by_fkey", type_="foreignkey")
        batch.drop_constraint("brand_guideline_sources_created_by_fkey", type_="foreignkey")
        batch.create_foreign_key("brand_guideline_sources_created_by_fkey", "users", ["created_by"], ["id"], ondelete="RESTRICT")
        batch.create_unique_constraint("uq_source_org_version", ["organization_id", "version"])
        batch.alter_column("effective_from", existing_type=sa.Date(), type_=sa.DateTime(timezone=True), existing_nullable=True)
        batch.alter_column("effective_to", existing_type=sa.Date(), type_=sa.DateTime(timezone=True), existing_nullable=True)
        batch.drop_column("approved_at")
        batch.drop_column("approved_by")
        batch.drop_column("size_bytes")
        batch.drop_column("sha256")
        batch.drop_column("content_type")
        batch.drop_column("original_filename")
        batch.drop_column("family_id")
