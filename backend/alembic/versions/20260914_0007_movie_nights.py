"""Movie night rooms, preferences and private ballots."""
from alembic import op
import sqlalchemy as s
revision='20260914_0007'
down_revision='20260914_0006'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('movie_nights',s.Column('id',s.String(36),primary_key=True),s.Column('host_id',s.Integer(),s.ForeignKey('accounts.id',ondelete='CASCADE'),nullable=False),s.Column('title',s.String(80),nullable=False),s.Column('invite_hash',s.String(64),nullable=False,unique=True),s.Column('expires_at',s.DateTime(),nullable=False),s.Column('state',s.String(16),nullable=False),s.Column('candidates',s.JSON(),nullable=False),s.Column('winner_id',s.Integer(),s.ForeignKey('movies.id',ondelete='SET NULL'),nullable=True),s.Column('version',s.Integer(),nullable=False))
    op.create_table('night_members',s.Column('room_id',s.String(36),s.ForeignKey('movie_nights.id',ondelete='CASCADE'),primary_key=True),s.Column('account_id',s.Integer(),s.ForeignKey('accounts.id',ondelete='CASCADE'),primary_key=True),s.Column('genres',s.JSON(),nullable=False),s.Column('favorites',s.JSON(),nullable=False))
    op.create_table('night_votes',s.Column('room_id',s.String(36),s.ForeignKey('movie_nights.id',ondelete='CASCADE'),primary_key=True),s.Column('account_id',s.Integer(),s.ForeignKey('accounts.id',ondelete='CASCADE'),primary_key=True),s.Column('movie_id',s.Integer(),s.ForeignKey('movies.id',ondelete='CASCADE'),primary_key=True),s.Column('choice',s.String(8),nullable=False))

def downgrade():
    op.drop_table('night_votes');op.drop_table('night_members');op.drop_table('movie_nights')
