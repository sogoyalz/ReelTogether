"""Single-use account recovery code hashes."""
from alembic import op
import sqlalchemy as sa
revision = "20260914_0006"
down_revision = "20260913_0005"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("accounts", sa.Column("recovery_hash", sa.String(64), nullable=True))


def downgrade():
    op.drop_column("accounts", "recovery_hash")
