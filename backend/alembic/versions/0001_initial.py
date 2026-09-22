"""Initial schema for the speech-to-text platform."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(200), nullable=False),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "api_clients",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("owner_name", sa.String(200), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "api_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("api_clients.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("key_prefix", sa.String(32), nullable=False),
        sa.Column("key_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("rate_limit_per_minute", sa.Integer(), nullable=False),
        sa.Column("daily_audio_limit_seconds", sa.Integer(), nullable=True),
        sa.Column("monthly_audio_limit_seconds", sa.Integer(), nullable=True),
        sa.Column("allowed_models", postgresql.JSONB(), nullable=True),
        sa.Column("allowed_languages", postgresql.JSONB(), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "models",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False, unique=True),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("engine", sa.String(64), nullable=False),
        sa.Column("whisper_model_id", sa.String(255), nullable=False),
        sa.Column("language_label", sa.String(64), nullable=False),
        sa.Column("size_label", sa.String(64), nullable=False),
        sa.Column("vram_mb", sa.Integer(), nullable=False),
        sa.Column("compute_type", sa.String(32), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("api_clients.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("api_key_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("api_keys.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("stored_path", sa.String(1024), nullable=False),
        sa.Column("normalized_path", sa.String(1024), nullable=True),
        sa.Column("mime_type", sa.String(128), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("language", sa.String(16), nullable=True),
        sa.Column("detected_language", sa.String(16), nullable=True),
        sa.Column("task", sa.String(32), nullable=False),
        sa.Column("model_name", sa.String(128), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("webhook_url", sa.String(2000), nullable=True),
        sa.Column("options", postgresql.JSONB(), nullable=False),
        sa.Column("text_result", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("max_retries", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processing_time_ms", sa.Integer(), nullable=True),
        sa.Column("queue_time_ms", sa.Integer(), nullable=True),
        sa.Column("audio_deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_jobs_status_created", "jobs", ["status", "created_at"])
    op.create_index("ix_jobs_api_key_id", "jobs", ["api_key_id"])
    op.create_index("ix_jobs_client_id", "jobs", ["client_id"])
    op.create_table(
        "job_segments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("segment_index", sa.Integer(), nullable=False),
        sa.Column("start_sec", sa.Float(), nullable=False),
        sa.Column("end_sec", sa.Float(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("words", postgresql.JSONB(), nullable=True),
    )
    op.create_index("ix_job_segments_job_id", "job_segments", ["job_id"])
    op.create_table(
        "usage_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("api_key_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("api_keys.id", ondelete="SET NULL"), nullable=True),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("api_clients.id", ondelete="SET NULL"), nullable=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("audio_seconds", sa.Float(), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("processing_time_ms", sa.Integer(), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_usage_key_recorded", "usage_records", ["api_key_id", "recorded_at"])
    op.create_table(
        "system_settings",
        sa.Column("key", sa.String(128), primary_key=True),
        sa.Column("value", postgresql.JSONB(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "webhook_deliveries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=True),
        sa.Column("url", sa.String(2000), nullable=False),
        sa.Column("event", sa.String(64), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("response_code", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("actor_type", sa.String(32), nullable=False),
        sa.Column("actor_id", sa.String(64), nullable=True),
        sa.Column("action", sa.String(128), nullable=False),
        sa.Column("resource_type", sa.String(64), nullable=False),
        sa.Column("resource_id", sa.String(64), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=False),
        sa.Column("ip", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("webhook_deliveries")
    op.drop_table("system_settings")
    op.drop_index("ix_usage_key_recorded", table_name="usage_records")
    op.drop_table("usage_records")
    op.drop_index("ix_job_segments_job_id", table_name="job_segments")
    op.drop_table("job_segments")
    op.drop_index("ix_jobs_client_id", table_name="jobs")
    op.drop_index("ix_jobs_api_key_id", table_name="jobs")
    op.drop_index("ix_jobs_status_created", table_name="jobs")
    op.drop_table("jobs")
    op.drop_table("models")
    op.drop_table("api_keys")
    op.drop_table("api_clients")
    op.drop_table("users")
