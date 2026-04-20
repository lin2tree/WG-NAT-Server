"""Authentication API routes"""
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status, Form
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..core.database import get_db
from ..core.security import verify_password, create_access_token, get_password_hash
from ..core.config import settings
from ..core.rsa import rsa_key_manager
from ..models.user import User, UserRole
from ..api.deps import get_current_user, get_current_root_user

router = APIRouter()


class CreateUserRequest(BaseModel):
    username: str
    password: str
    role: str = "user"


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class ChangePasswordByRootRequest(BaseModel):
    new_password: str


@router.get("/public-key")
async def get_public_key():
    """Get RSA public key for password encryption"""
    return {"public_key": rsa_key_manager.get_public_key_pem()}


@router.post("/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Login and get access token"""
    user = db.query(User).filter(User.username == form_data.username).first()
    
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(hours=settings.ADMIN_JWT_EXPIRE_HOURS),
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.ADMIN_JWT_EXPIRE_HOURS * 3600,
        "user": {
            "id": user.id,
            "username": user.username,
            "role": user.role,
        },
    }


@router.post("/login/encrypted")
async def login_encrypted(
    username: str = Form(...),
    encrypted_password: str = Form(...),
    db: Session = Depends(get_db),
):
    """Login with RSA encrypted password and get access token"""
    try:
        password = rsa_key_manager.decrypt(encrypted_password)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to decrypt password",
        )
    
    user = db.query(User).filter(User.username == username).first()
    
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(hours=settings.ADMIN_JWT_EXPIRE_HOURS),
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.ADMIN_JWT_EXPIRE_HOURS * 3600,
        "user": {
            "id": user.id,
            "username": user.username,
            "role": user.role,
        },
    }


@router.post("/logout")
async def logout():
    """Logout (client should discard token)"""
    return {"message": "Successfully logged out"}


@router.get("/me")
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
):
    """Get current user information"""
    return {
        "id": current_user.id,
        "username": current_user.username,
        "role": current_user.role,
        "created_at": current_user.created_at,
    }


@router.get("/users")
async def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List users - Admin sees all, User sees only self"""
    if current_user.role == "admin":
        users = db.query(User).order_by(User.created_at.desc()).all()
    else:
        users = [current_user]
    
    return {
        "success": True,
        "data": [
            {
                "id": u.id,
                "username": u.username,
                "role": u.role,
                "created_at": u.created_at.isoformat(),
            }
            for u in users
        ],
    }


@router.post("/users")
async def create_user(
    request: CreateUserRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_root_user),
):
    """Create a new user (Root only)"""
    existing = db.query(User).filter(User.username == request.username).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在",
        )
    
    if request.role not in [UserRole.ADMIN.value, UserRole.USER.value]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的角色类型",
        )
    
    user = User(
        username=request.username,
        password_hash=get_password_hash(request.password),
        role=request.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return {
        "success": True,
        "message": "用户创建成功",
        "data": {
            "id": user.id,
            "username": user.username,
            "role": user.role,
        },
    }


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_root_user),
):
    """Delete a user (Root only)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )
    
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能删除自己的账号",
        )
    
    db.delete(user)
    db.commit()
    
    return {
        "success": True,
        "message": "用户删除成功",
    }


@router.put("/users/{user_id}/password")
async def change_user_password_by_root(
    user_id: int,
    request: ChangePasswordByRootRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_root_user),
):
    """Change user password (Root only)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )
    
    user.password_hash = get_password_hash(request.new_password)
    db.commit()
    
    return {
        "success": True,
        "message": "密码修改成功",
    }


@router.put("/me/password")
async def change_own_password(
    request: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Change own password"""
    if not verify_password(request.old_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="原密码错误",
        )
    
    current_user.password_hash = get_password_hash(request.new_password)
    db.commit()
    
    return {
        "success": True,
        "message": "密码修改成功",
    }
