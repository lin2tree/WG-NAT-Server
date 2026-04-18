"""User model for admin authentication"""
from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class UserRole(str, Enum):
    """User role types"""
    ROOT = "root"
    ADMIN = "admin"


class User(Base):
    """Admin user for management frontend"""
    
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow, 
        nullable=False
    )
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username}, role={self.role})>"
    
    @property
    def is_root(self) -> bool:
        """Check if user has root role"""
        return self.role == UserRole.ROOT.value
    
    @property
    def is_admin(self) -> bool:
        """Check if user has admin role"""
        return self.role == UserRole.ADMIN.value
    
    def can_view_secrets(self) -> bool:
        """Check if user can view secret keys in plain text"""
        return self.is_root
    
    def can_download_server_config(self) -> bool:
        """Check if user can download server config"""
        return self.is_root
