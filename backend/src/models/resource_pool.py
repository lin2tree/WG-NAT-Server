"""ResourcePool model for IP to port mapping"""
from datetime import datetime
from ipaddress import IPv4Address

from sqlalchemy import DateTime, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class ResourcePool(Base):
    """Mapping between internal IP addresses and public UDP ports"""
    
    __tablename__ = "resource_pools"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    internal_ip: Mapped[str] = mapped_column(String(45), nullable=False, unique=True)
    public_port: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow, 
        nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    
    __table_args__ = (
        Index("idx_resource_pools_ip", "internal_ip"),
        Index("idx_resource_pools_port", "public_port"),
    )
    
    def __repr__(self) -> str:
        return f"<ResourcePool(id={self.id}, ip={self.internal_ip}, port={self.public_port})>"
    
    @property
    def is_deleted(self) -> bool:
        """Check if this mapping has been soft-deleted"""
        return self.deleted_at is not None
    
    @property
    def ip_address(self) -> IPv4Address:
        """Get internal IP as IPv4Address object"""
        return IPv4Address(self.internal_ip)
