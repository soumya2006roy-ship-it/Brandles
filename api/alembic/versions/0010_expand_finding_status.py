"""Allow full finding workflow status values."""

from alembic import op
import sqlalchemy as sa


revision = "0010_expand_finding_status"
down_revision = "0009_remove_public_workspace_marker"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("findings") as batch:
        batch.alter_column("status", existing_type=sa.String(length=16), type_=sa.String(length=32), existing_nullable=False)


def downgrade() -> None:
    # Preserve the longer workflow labels; shrinking would truncate them.
    pass
