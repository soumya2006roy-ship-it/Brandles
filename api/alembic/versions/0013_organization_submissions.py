"""Keep organisation submission notes and review resubmissions."""

from alembic import op
import sqlalchemy as sa


revision = "0013_organization_submissions"
down_revision = "0012_question_gated_password_reset"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "organization_submissions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("organization_id", sa.String(length=36), nullable=False),
        sa.Column("submitted_by_user_id", sa.String(length=36), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["submitted_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_org_submissions_org_created", "organization_submissions", ["organization_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_org_submissions_org_created", table_name="organization_submissions")
    op.drop_table("organization_submissions")
