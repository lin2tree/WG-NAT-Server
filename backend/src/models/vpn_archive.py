"""VpnArchive model for archived (deleted) VPN configurations"""
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class VpnArchive(Base):
    """Archived VPN configuration (status: deleted)"""
    
    __tablename__ = "vpn_archives"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    vm_ip: Mapped[str] = mapped_column(String(45), nullable=False)
    server_private_key: Mapped[str] = mapped_column(Text, nullable=False)
    server_public_key: Mapped[str] = mapped_column(Text, nullable=False)
    client_configs: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, 
        nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), 
        nullable=False, 
        default="deleted"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    deleted_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow, 
        nullable=False
    )
    
    __table_args__ = (
        Index("idx_vpn_archives_ip", "vm_ip"),
        Index("idx_vpn_archives_deleted_at", "deleted_at"),
    )
    
    def __repr__(self) -> str:
        return f"<VpnArchive(id={self.id}, ip={self.vm_ip}, deleted={self.deleted_at})>"
    
    @classmethod
    def from_vpn_config(cls, vpn_config) -> "VpnArchive":
        """Create archive from VpnConfig"""
        return cls(
            vm_ip=vpn_config.vm_ip,
            server_private_key=vpn_config.server_private_key,
            server_public_key=vpn_config.server_public_key,
            client_configs=vpn_config.client_configs,
            status="deleted",
            created_at=vpn_config.created_at,
            started_at=vpn_config.started_at,
            deleted_at=datetime.utcnow(),
        )
