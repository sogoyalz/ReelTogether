"""Durable maintenance queue and persistent schedules."""
from alembic import op
import sqlalchemy as s
revision = "20260915_0009"
down_revision = "20260915_0008"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("background_jobs", s.Column("id", s.String(36), primary_key=True),
        s.Column("name", s.String(40), nullable=False), s.Column("active_name", s.String(40), unique=True),
        s.Column("status", s.String(16), nullable=False), s.Column("queued_at", s.DateTime(), nullable=False),
        s.Column("available_at", s.DateTime(), nullable=False), s.Column("started_at", s.DateTime()),
        s.Column("finished_at", s.DateTime()), s.Column("lease_until", s.DateTime()), s.Column("lease_token", s.String(36)),
        s.Column("attempts", s.Integer(), nullable=False), s.Column("error", s.String(100)), s.Column("result", s.JSON()))
    op.create_index("ix_background_jobs_name", "background_jobs", ["name"])
    op.create_table("job_queue_control", s.Column("id", s.Integer(), primary_key=True), s.Column("version", s.Integer(), nullable=False))
    op.execute("INSERT INTO job_queue_control (id,version) VALUES (1,0)")
    op.create_table("job_schedules", s.Column("name", s.String(40), primary_key=True), s.Column("next_run", s.DateTime(), nullable=False))


def downgrade():
    op.drop_table("job_schedules")
    op.drop_table("job_queue_control")
    op.drop_table("background_jobs")
