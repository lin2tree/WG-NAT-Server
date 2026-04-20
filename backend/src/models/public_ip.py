"""Public IP address model"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class PublicIP(Base):
    """Public IP addresses for VPN endpoints"""
    
    __tablename__ = "public_ips"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ip_address: Mapped[str] = mapped_column(String(45), nullable=False, unique=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        Index("idx_public_ips_address", "ip_address"),
        Index("idx_public_ips_default", "is_default"),
    )
    
    def __repr__(self) -> str:
        return f"<PublicIP(id={self.id}, ip={self.ip_address}, default={self.is_default})>"
