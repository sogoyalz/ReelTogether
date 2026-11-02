"""Stable restore identity and deletion outbox; no account facts are removed."""
from datetime import datetime
import uuid
from alembic import op
import sqlalchemy as sa
revision = '20261101_0015'
down_revision = '20261101_0014'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('accounts', sa.Column('erasure_key', sa.String(36), nullable=True))
    bind = op.get_bind()
    accounts = sa.table('accounts',sa.column('id',sa.Integer),sa.column('username',sa.String),sa.column('created_at',sa.DateTime),sa.column('erasure_key',sa.String))
    for row in bind.execute(sa.select(accounts.c.id,accounts.c.username,accounts.c.created_at)):
        # Deterministic only for pre-feature rows, so replaying this migration on
        # an older backup produces the same identity as the original upgrade.
        created = row.created_at.isoformat(timespec='microseconds')
        key = str(uuid.uuid5(uuid.NAMESPACE_URL, f'reeltogether/account/{row.id}/{row.username}/{created}'))
        bind.execute(accounts.update().where(accounts.c.id == row.id).values(erasure_key=key))
    with op.batch_alter_table('accounts') as batch:
        batch.alter_column('erasure_key', existing_type=sa.String(36), nullable=False)
        batch.create_unique_constraint('uq_accounts_erasure_key',['erasure_key'])
    op.create_table('account_erasures',sa.Column('erasure_key',sa.String(36),primary_key=True),
        sa.Column('requested_at',sa.DateTime,nullable=False),sa.Column('exported_at',sa.DateTime,nullable=True))


def downgrade():
    op.drop_table('account_erasures')
    with op.batch_alter_table('accounts') as batch:
        batch.drop_constraint('uq_accounts_erasure_key',type_='unique')
        batch.drop_column('erasure_key')
