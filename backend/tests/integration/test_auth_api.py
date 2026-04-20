"""Integration tests for Auth API endpoints"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from datetime import datetime

from src.main import app
from src.models.user import User, UserRole


client = TestClient(app)


class TestAuthApi:
    """Integration tests for auth API"""
    
    def test_login_success(self, mock_db_session):
        """Test successful login"""
        with patch('src.api.deps.get_db', return_value=mock_db_session), \
             patch('src.core.security.verify_password', return_value=True):
            
            mock_user = User(
                id=1,
                username="admin",
                password_hash="hashed_password",
                role=UserRole.ADMIN.value,
                created_at=datetime.now(),
            )
            mock_db_session.query.return_value.filter.return_value.first.return_value = mock_user
            
            response = client.post(
                "/api/auth/login",
                data={"username": "admin", "password": "password"},
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data
            assert data["token_type"] == "bearer"
            assert data["user"]["username"] == "admin"
    
    def test_login_invalid_username(self, mock_db_session):
        """Test login with invalid username"""
        with patch('src.api.deps.get_db', return_value=mock_db_session):
            
            mock_db_session.query.return_value.filter.return_value.first.return_value = None
            
            response = client.post(
                "/api/auth/login",
                data={"username": "nonexistent", "password": "password"},
            )
            
            assert response.status_code == 401
    
    def test_login_invalid_password(self, mock_db_session):
        """Test login with invalid password"""
        with patch('src.api.deps.get_db', return_value=mock_db_session), \
             patch('src.core.security.verify_password', return_value=False):
            
            mock_user = User(
                id=1,
                username="admin",
                password_hash="hashed_password",
                role=UserRole.ADMIN.value,
                created_at=datetime.now(),
            )
            mock_db_session.query.return_value.filter.return_value.first.return_value = mock_user
            
            response = client.post(
                "/api/auth/login",
                data={"username": "admin", "password": "wrong_password"},
            )
            
            assert response.status_code == 401
    
    def test_logout_success(self):
        """Test successful logout"""
        response = client.post(
            "/api/auth/logout",
            headers={"Authorization": "Bearer test_token"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "logged out" in data["message"].lower()
    
    def test_get_current_user_success(self, mock_db_session):
        """Test getting current user info"""
        with patch('src.api.deps.get_current_user') as mock_user:
            
            mock_user.return_value = User(
                id=1,
                username="admin",
                password_hash="hashed_password",
                role=UserRole.ADMIN.value,
                created_at=datetime.now(),
            )
            
            response = client.get(
                "/api/auth/me",
                headers={"Authorization": "Bearer test_token"},
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["username"] == "admin"
            assert data["role"] == "admin"
    
    def test_get_current_user_root(self, mock_db_session):
        """Test getting current user info for admin"""
        with patch('src.api.deps.get_current_user') as mock_user:
            
            mock_user.return_value = User(
                id=1,
                username="admin",
                password_hash="hashed_password",
                role=UserRole.ADMIN.value,
                created_at=datetime.now(),
            )
            
            response = client.get(
                "/api/auth/me",
                headers={"Authorization": "Bearer test_token"},
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["role"] == "admin"


@pytest.fixture
def mock_db_session():
    """Create mock database session"""
    session = MagicMock()
    return session
