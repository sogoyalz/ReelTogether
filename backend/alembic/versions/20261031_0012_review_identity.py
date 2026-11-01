"""Persist provider review IDs without deleting legacy review evidence."""
from alembic import op
import sqlalchemy as sa
revision = '20261031_0012'
down_revision = '20261031_0011'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('review_sentiments') as batch:
        batch.add_column(sa.Column('source_review_id', sa.String(128), nullable=True))
        batch.create_unique_constraint('uq_review_provider_identity', ['movie_id', 'source', 'source_review_id'])


def downgrade():
    with op.batch_alter_table('review_sentiments') as batch:
        batch.drop_constraint('uq_review_provider_identity', type_='unique')
        batch.drop_column('source_review_id')
