"""Add optional account recovery question fields.

New signups populate these values. Existing accounts keep using email reset.
"""

from alembic import op
import sqlalchemy as sa


revision = "0011_account_recovery_questions"
down_revision = "0010_expand_finding_status"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("recovery_question", sa.String(length=32), nullable=True))
    op.add_column("users", sa.Column("recovery_answer_hash", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "recovery_answer_hash")
    op.drop_column("users", "recovery_question")
