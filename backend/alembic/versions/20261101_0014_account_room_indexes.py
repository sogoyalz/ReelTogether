"""Index ownership lookups without rewriting retained room or vote data."""
from alembic import op
revision = '20261101_0014'
down_revision = '20261031_0013'
branch_labels = None
depends_on = None


def upgrade():
    op.create_index('ix_night_members_account_room', 'night_members', ['account_id', 'room_id'])
    op.create_index('ix_movie_nights_host_expiry', 'movie_nights', ['host_id', 'expires_at'])
    op.create_index('ix_night_votes_account', 'night_votes', ['account_id'])


def downgrade():
    op.drop_index('ix_night_votes_account', table_name='night_votes')
    op.drop_index('ix_movie_nights_host_expiry', table_name='movie_nights')
    op.drop_index('ix_night_members_account_room', table_name='night_members')
