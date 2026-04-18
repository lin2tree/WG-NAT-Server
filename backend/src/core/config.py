"""Application configuration using Pydantic Settings"""
from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    APP_NAME: str = "WireGuard VPN Manager"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    DATABASE_URL: str = "postgresql://vpn_admin:vpn_secret@localhost:5432/vpn_manager"
    
    VM_TOKEN: str = "vm_default_token"
    ADMIN_JWT_SECRET: str = "admin_jwt_secret_change_in_production"
    ADMIN_JWT_ALGORITHM: str = "HS256"
    ADMIN_JWT_EXPIRE_HOURS: int = 24
    
    LOG_LEVEL: str = "INFO"
    LOG_RETENTION_DAYS: int = 90
    
    WIREGUARD_VPN_SUBNET: str = "10"
    WIREGUARD_SERVER_PORT: int = 2588
    WIREGUARD_CLIENT_COUNT: int = 5
    WIREGUARD_KEEPALIVE: int = 25
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


settings = get_settings()
