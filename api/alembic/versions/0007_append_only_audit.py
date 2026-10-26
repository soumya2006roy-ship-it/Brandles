"""Make audit records immutable and allow org-free authentication events."""

from alembic import op
import sqlalchemy as sa


revision = "0007_append_only_audit"
down_revision = "0006_product_surfaces_and_sample_workspace"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("audit_events") as batch:
        batch.alter_column("organization_id", existing_type=sa.String(length=36), nullable=True)
    dialect = op.get_bind().dialect.name
    if dialect == "sqlite":
        op.execute("CREATE TRIGGER IF NOT EXISTS audit_events_no_update BEFORE UPDATE ON audit_events BEGIN SELECT RAISE(ABORT, 'audit events are append-only'); END")
        op.execute("CREATE TRIGGER IF NOT EXISTS audit_events_no_delete BEFORE DELETE ON audit_events BEGIN SELECT RAISE(ABORT, 'audit events are append-only'); END")
    elif dialect == "postgresql":
        op.execute("CREATE OR REPLACE FUNCTION brandlens_reject_audit_mutation() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'audit events are append-only'; END; $$")
        op.execute("CREATE TRIGGER audit_events_append_only BEFORE UPDATE OR DELETE ON audit_events FOR EACH ROW EXECUTE FUNCTION brandlens_reject_audit_mutation()")


def downgrade() -> None:
    dialect = op.get_bind().dialect.name
    if dialect == "sqlite":
        op.execute("DROP TRIGGER IF EXISTS audit_events_no_update")
        op.execute("DROP TRIGGER IF EXISTS audit_events_no_delete")
    elif dialect == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS audit_events_append_only ON audit_events")
        op.execute("DROP FUNCTION IF EXISTS brandlens_reject_audit_mutation()")
    with op.batch_alter_table("audit_events") as batch:
        batch.alter_column("organization_id", existing_type=sa.String(length=36), nullable=False)
