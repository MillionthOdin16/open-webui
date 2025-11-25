"""Add mode and config to chat table

Revision ID: 524a2047eae1
Revises: 242a2047eae0
Create Date: 2024-11-25 10:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


revision = "524a2047eae1"
down_revision = "d31026856c01"  # Latest from file list
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = inspector.get_columns("chat")
    column_names = [col["name"] for col in columns]

    if "mode" not in column_names:
        op.add_column("chat", sa.Column("mode", sa.Text(), server_default="standard"))

    if "config" not in column_names:
        op.add_column("chat", sa.Column("config", sa.JSON(), server_default="{}"))


def downgrade():
    with op.batch_alter_table("chat") as batch_op:
        batch_op.drop_column("mode")
        batch_op.drop_column("config")
