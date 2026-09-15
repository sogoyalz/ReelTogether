"""Accounts, revocable sessions, and private watchlists."""
from alembic import op
import sqlalchemy as sa
revision = "20260913_0004"
down_revision = "20260913_0003"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("accounts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(32), unique=True, nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False))
    op.create_table("login_sessions",
        sa.Column("token_hash", sa.String(64), primary_key=True),
        sa.Column("account_id", sa.Integer(), sa.ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("csrf_token", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False))
    op.create_index("ix_login_sessions_account_id", "login_sessions", ["account_id"])
    op.create_index("ix_login_sessions_expires_at", "login_sessions", ["expires_at"])
    op.create_table("watchlist_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("account_id", sa.Integer(), sa.ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("movie_id", sa.Integer(), sa.ForeignKey("movies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("added_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("account_id", "movie_id", name="uq_watchlist_account_movie"))
    for column in ("account_id", "movie_id"):
        op.create_index(f"ix_watchlist_entries_{column}", "watchlist_entries", [column])


def downgrade():
    op.drop_table("watchlist_entries")
    op.drop_table("login_sessions")
    op.drop_table("accounts")
