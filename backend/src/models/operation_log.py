"""OperationLog model for API request logging"""
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class OperationLog(Base):
    """Log of all API requests and responses"""
    
    __tablename__ = "operation_logs"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_time: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow, 
        nullable=False
    )
    source_ip: Mapped[str] = mapped_column(String(45), nullable=False)
    request_path: Mapped[str] = mapped_column(String(255), nullable=False)
    request_method: Mapped[str] = mapped_column(String(10), nullable=False)
    request_params: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, 
        nullable=True
    )
    response_status: Mapped[int] = mapped_column(Integer, nullable=False)
    response_time_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    
    __table_args__ = (
        Index("idx_operation_logs_time", "request_time"),
        Index("idx_operation_logs_ip", "source_ip"),
        Index("idx_operation_logs_path", "request_path"),
    )
    
    def __repr__(self) -> str:
        return f"<OperationLog(id={self.id}, {self.request_method} {self.request_path}, status={self.response_status})>"
    
    @classmethod
    def create(
        cls,
        source_ip: str,
        request_path: str,
        request_method: str,
        response_status: int,
        response_time_ms: int,
        request_params: dict[str, Any] | None = None,
        error_message: str | None = None,
    ) -> "OperationLog":
        """Create a new operation log entry"""
        return cls(
            request_time=datetime.utcnow(),
            source_ip=source_ip,
            request_path=request_path,
            request_method=request_method,
            request_params=request_params,
            response_status=response_status,
            response_time_ms=response_time_ms,
            error_message=error_message,
        )
