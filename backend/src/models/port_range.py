"""PortRange model for UDP port range configuration"""
from sqlalchemy import CheckConstraint, Integer
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class PortRange(Base, TimestampMixin):
    """UDP port range configuration for public port allocation"""
    
    __tablename__ = "port_ranges"
    __table_args__ = (
        CheckConstraint(
            "start_port < end_port AND start_port >= 1024 AND end_port <= 65535",
            name="valid_port_range"
        ),
    )
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    start_port: Mapped[int] = mapped_column(Integer, nullable=False)
    end_port: Mapped[int] = mapped_column(Integer, nullable=False)
    
    def __repr__(self) -> str:
        return f"<PortRange(id={self.id}, range={self.start_port}-{self.end_port})>"
    
    def contains_port(self, port: int) -> bool:
        """Check if port is within the configured range"""
        return self.start_port <= port <= self.end_port
    
    @property
    def total_ports(self) -> int:
        """Get total number of ports in range"""
        return self.end_port - self.start_port + 1
