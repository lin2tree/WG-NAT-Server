"""VpnConfig model for active VPN configurations"""
from datetime import datetime
from enum import Enum
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class VpnStatus(str, Enum):
    """VPN configuration status"""
    INIT = "init"
    STARTED = "started"
    ERROR = "error"


class VpnConfig(Base):
    """Active VPN configuration (status: init or started)"""
    
    __tablename__ = "vpn_configs"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    vm_ip: Mapped[str] = mapped_column(String(45), nullable=False, unique=True)
    server_private_key: Mapped[str] = mapped_column(Text, nullable=False)
    server_public_key: Mapped[str] = mapped_column(Text, nullable=False)
    client_configs: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, 
        nullable=False,
        default=list
    )
    status: Mapped[str] = mapped_column(
        String(20), 
        nullable=False, 
        default=VpnStatus.INIT.value
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow, 
        nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    __table_args__ = (
        Index("idx_vpn_configs_ip", "vm_ip"),
        Index("idx_vpn_configs_status", "status"),
    )
    
    def __repr__(self) -> str:
        return f"<VpnConfig(id={self.id}, ip={self.vm_ip}, status={self.status})>"
    
    @property
    def is_init(self) -> bool:
        """Check if config is in init state"""
        return self.status == VpnStatus.INIT.value
    
    @property
    def is_started(self) -> bool:
        """Check if config is in started state"""
        return self.status == VpnStatus.STARTED.value
    
    @property
    def is_error(self) -> bool:
        """Check if config is in error state"""
        return self.status == VpnStatus.ERROR.value
    
    def mark_started(self) -> None:
        """Mark config as started"""
        self.status = VpnStatus.STARTED.value
        self.started_at = datetime.utcnow()
        self.error_message = None
    
    def mark_error(self, error_message: str) -> None:
        """Mark config as error with message"""
        self.status = VpnStatus.ERROR.value
        self.started_at = datetime.utcnow()
        self.error_message = error_message
