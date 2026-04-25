"""Endpoint model for API routes with monitoring and contracts."""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Endpoint(Base):
	__tablename__ = "endpoints"
	__table_args__ = (UniqueConstraint("api_id", "path", "method", name="uq_endpoint_api_path_method"),)

	id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
	api_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("apis.id", ondelete="CASCADE"), index=True, nullable=False)
	org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False)
	path: Mapped[str] = mapped_column(String(1024), nullable=False)
	method: Mapped[str] = mapped_column(String(16), nullable=False)
	monitoring_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true", default=True)
	consecutive_error_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0", default=0)
	auto_paused: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false", default=False)
	poll_interval_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
	timeout_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
	poll_headers_json: Mapped[dict[str, str] | None] = mapped_column(JSON, nullable=True)
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
	updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

	api = relationship("API", back_populates="endpoints")
	contracts = relationship("Contract", back_populates="endpoint", cascade="all, delete-orphan")
