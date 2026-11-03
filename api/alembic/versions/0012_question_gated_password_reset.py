"""Require recovery-question reset tokens."""

from alembic import op
import sqlalchemy as sa


revision = "0012_question_gated_password_reset"
down_revision = "0011_account_recovery_questions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("auth_tokens") as batch:
        batch.drop_constraint("ck_auth_tokens_purpose", type_="check")
        batch.create_check_constraint(
            "ck_auth_tokens_purpose",
            "purpose IN ('email_verification','password_reset','password_reset_question')",
        )


def downgrade() -> None:
    op.execute(sa.text("UPDATE auth_tokens SET purpose = 'password_reset' WHERE purpose = 'password_reset_question'"))
    with op.batch_alter_table("auth_tokens") as batch:
        batch.drop_constraint("ck_auth_tokens_purpose", type_="check")
        batch.create_check_constraint(
            "ck_auth_tokens_purpose",
            "purpose IN ('email_verification','password_reset')",
        )
