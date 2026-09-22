from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utcnow
from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[str] = mapped_column(String(32), default="admin", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class ApiClient(Base):
    __tablename__ = "api_clients"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    owner_name: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    keys: Mapped[list[ApiKey]] = relationship(back_populates="client")


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("api_clients.id", ondelete="RESTRICT"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(32), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    rate_limit_per_minute: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    daily_audio_limit_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    monthly_audio_limit_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    allowed_models: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    allowed_languages: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    client: Mapped[ApiClient] = relationship(back_populates="keys")


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        Index("ix_jobs_status_created", "status", "created_at"),
        Index("ix_jobs_api_key_id", "api_key_id"),
        Index("ix_jobs_client_id", "client_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("api_clients.id", ondelete="RESTRICT"), nullable=False)
    api_key_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("api_keys.id", ondelete="RESTRICT"), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    normalized_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    mime_type: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    detected_language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    task: Mapped[str] = mapped_column(String(32), default="transcribe", nullable=False)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="queued", nullable=False)
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    webhook_url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    options: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    text_result: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    processing_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    queue_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    audio_deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    segments: Mapped[list[JobSegment]] = relationship(
        back_populates="job", cascade="all, delete-orphan", order_by="JobSegment.segment_index"
    )
    client: Mapped[ApiClient] = relationship()
    api_key: Mapped[ApiKey] = relationship()


class JobSegment(Base):
    __tablename__ = "job_segments"
    __table_args__ = (Index("ix_job_segments_job_id", "job_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    segment_index: Mapped[int] = mapped_column(Integer, nullable=False)
    start_sec: Mapped[float] = mapped_column(Float, nullable=False)
    end_sec: Mapped[float] = mapped_column(Float, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    words: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    job: Mapped[Job] = relationship(back_populates="segments")


class SttModel(Base):
    __tablename__ = "models"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    engine: Mapped[str] = mapped_column(String(64), default="faster-whisper", nullable=False)
    whisper_model_id: Mapped[str] = mapped_column(String(255), nullable=False)
    language_label: Mapped[str] = mapped_column(String(64), default="Multilingual", nullable=False)
    size_label: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    vram_mb: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    compute_type: Mapped[str] = mapped_column(String(32), default="float16", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class UsageRecord(Base):
    __tablename__ = "usage_records"
    __table_args__ = (Index("ix_usage_key_recorded", "api_key_id", "recorded_at"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    api_key_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("api_keys.id", ondelete="SET NULL"), nullable=True)
    client_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("api_clients.id", ondelete="SET NULL"), nullable=True)
    job_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True)
    audio_seconds: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    processing_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class SystemSetting(Base):
    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value: Mapped[dict | list | str | int | float | bool | None] = mapped_column(JSONB, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class WebhookDelivery(Base):
    __tablename__ = "webhook_deliveries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), nullable=True)
    url: Mapped[str] = mapped_column(String(2000), nullable=False)
    event: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_type: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    details: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
