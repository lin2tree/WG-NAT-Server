"""Dependency injection utilities for API routes"""
from typing import Generator

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.security import verify_token, verify_vm_token, verify_3rd_token
from ..core.config import settings
from ..models.user import User, UserRole


security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """Get current authenticated user from JWT token"""
    token = credentials.credentials
    payload = verify_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
    
    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    
    return user


def get_current_root_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get current user and verify admin role"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return current_user


def _is_trusted_proxy(client_ip: str) -> bool:
    """Check if the client IP is in the trusted proxy list"""
    if not settings.TRUSTED_PROXIES:
        return False
    trusted_proxies = [ip.strip() for ip in settings.TRUSTED_PROXIES.split(",")]
    return client_ip in trusted_proxies


def verify_vm_request(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    """Verify VM token and return source IP address
    
    Security: Only trust X-Forwarded-For/X-Real-IP headers from trusted proxies.
    For direct connections, use the actual client IP to prevent IP spoofing.
    """
    token = credentials.credentials
    
    if not verify_vm_token(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid VM token",
        )
    
    client_ip = request.client.host if request.client else None
    if client_ip is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot determine client IP",
        )
    
    if _is_trusted_proxy(client_ip):
        source_ip = (
            request.headers.get("x-forwarded-for", "").split(",")[0].strip()
            or request.headers.get("x-real-ip")
            or client_ip
        )
    else:
        source_ip = client_ip
    
    return source_ip


def verify_3rd_request(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> bool:
    """Verify third-party application token
    
    Third-party applications use a pre-configured token (3RD_TOKEN).
    This is separate from VM Token and JWT Token.
    """
    token = credentials.credentials
    
    if not verify_3rd_token(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid third-party token",
        )
    
    return True
