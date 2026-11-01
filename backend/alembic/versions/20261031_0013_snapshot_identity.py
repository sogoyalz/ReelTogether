"""Enforce one snapshot per label while preserving duplicate legacy observations."""
from alembic import op
import sqlalchemy as sa
revision = '20261031_0013'
down_revision = '20261031_0012'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    snapshots = sa.table('movie_analytics', sa.column('id', sa.Integer), sa.column('movie_id', sa.Integer), sa.column('snapshot_label', sa.String))
    duplicates = bind.execute(sa.select(snapshots.c.movie_id, snapshots.c.snapshot_label).group_by(
        snapshots.c.movie_id, snapshots.c.snapshot_label).having(sa.func.count() > 1)).all()
    for movie_id, label in duplicates:
        ids = list(bind.scalars(sa.select(snapshots.c.id).where(snapshots.c.movie_id == movie_id,
            snapshots.c.snapshot_label == label).order_by(snapshots.c.id.desc())))
        for snapshot_id in ids[1:]:
            archived = f'archived:{snapshot_id}:{label[:30]}'
            if bind.execute(sa.select(snapshots.c.id).where(snapshots.c.movie_id == movie_id, snapshots.c.snapshot_label == archived)).first():
                raise RuntimeError('Snapshot archive label collision; inspect before upgrading')
            bind.execute(snapshots.update().where(snapshots.c.id == snapshot_id).values(snapshot_label=archived))
    with op.batch_alter_table('movie_analytics') as batch:
        batch.create_unique_constraint('uq_movie_analytics_label', ['movie_id', 'snapshot_label'])
        batch.create_index('ix_movie_analytics_movie_date', ['movie_id', 'snapshot_date'])


def downgrade():
    with op.batch_alter_table('movie_analytics') as batch:
        batch.drop_index('ix_movie_analytics_movie_date')
        batch.drop_constraint('uq_movie_analytics_label', type_='unique')
    # Archived labels are retained to avoid reviving ambiguous latest snapshots.
