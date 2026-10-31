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
    # 0001_initial creates tables from current ORM metadata, so a brand-new
    # database may already include columns introduced by later revisions.
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("users")}
    if "recovery_question" not in columns:
        op.add_column("users", sa.Column("recovery_question", sa.String(length=32), nullable=True))
    if "recovery_answer_hash" not in columns:
        op.add_column("users", sa.Column("recovery_answer_hash", sa.String(length=255), nullable=True))


def downgrade() -> None:
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("users")}
    if "recovery_answer_hash" in columns:
        op.drop_column("users", "recovery_answer_hash")
    if "recovery_question" in columns:
        op.drop_column("users", "recovery_question")
