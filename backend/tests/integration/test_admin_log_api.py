"""Integration tests for Admin Log API endpoints"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

from src.main import app
from src.models.operation_log import OperationLog
from src.models.user import User, UserRole


client = TestClient(app)


class TestAdminLogApi:
    """Integration tests for admin log API"""
    
    def test_list_logs_success(self, mock_db_session):
        """Test successful log listing"""
        with patch('src.api.deps.get_current_user') as mock_user, \
             patch('src.api.deps.get_db', return_value=mock_db_session):
            
            mock_user.return_value = User(
                id=1,
                username="admin",
                password_hash="hash",
                role=UserRole.ADMIN.value,
            )
            
            mock_logs = [
                OperationLog(
                    id=1,
                    request_time=datetime.now(),
                    source_ip="192.168.1.100",
                    request_path="/api/vm/config",
                    request_method="GET",
                    response_status=200,
                    response_time_ms=50,
                ),
                OperationLog(
                    id=2,
                    request_time=datetime.now(),
                    source_ip="192.168.1.101",
                    request_path="/api/vm/ready",
                    request_method="POST",
                    response_status=200,
                    response_time_ms=30,
                ),
            ]
            mock_db_session.query.return_value.count.return_value = 2
            mock_db_session.query.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = mock_logs
            
            response = client.get(
                "/api/admin/logs",
                headers={"Authorization": "Bearer test_token"},
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["total"] == 2
    
    def test_list_logs_with_time_filter(self, mock_db_session):
        """Test log listing with time filter"""
        with patch('src.api.deps.get_current_user') as mock_user, \
             patch('src.api.deps.get_db', return_value=mock_db_session):
            
            mock_user.return_value = User(
                id=1,
                username="admin",
                password_hash="hash",
                role=UserRole.ADMIN.value,
            )
            
            now = datetime.now()
            mock_logs = [
                OperationLog(
                    id=1,
                    request_time=now,
                    source_ip="192.168.1.100",
                    request_path="/api/vm/config",
                    request_method="GET",
                    response_status=200,
                    response_time_ms=50,
                ),
            ]
            mock_db_session.query.return_value.filter.return_value.filter.return_value.count.return_value = 1
            mock_db_session.query.return_value.filter.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = mock_logs
            
            start_time = (now - timedelta(hours=1)).isoformat()
            end_time = now.isoformat()
            
            response = client.get(
                f"/api/admin/logs?start_time={start_time}&end_time={end_time}",
                headers={"Authorization": "Bearer test_token"},
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["data"]["total"] == 1
    
    def test_list_logs_with_ip_filter(self, mock_db_session):
        """Test log listing with IP filter"""
        with patch('src.api.deps.get_current_user') as mock_user, \
             patch('src.api.deps.get_db', return_value=mock_db_session):
            
            mock_user.return_value = User(
                id=1,
                username="admin",
                password_hash="hash",
                role=UserRole.ADMIN.value,
            )
            
            mock_logs = [
                OperationLog(
                    id=1,
                    request_time=datetime.now(),
                    source_ip="192.168.1.100",
                    request_path="/api/vm/config",
                    request_method="GET",
                    response_status=200,
                    response_time_ms=50,
                ),
            ]
            mock_db_session.query.return_value.filter.return_value.filter.return_value.count.return_value = 1
            mock_db_session.query.return_value.filter.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = mock_logs
            
            response = client.get(
                "/api/admin/logs?source_ip=192.168.1.100",
                headers={"Authorization": "Bearer test_token"},
            )
            
            assert response.status_code == 200
    
    def test_list_logs_with_path_filter(self, mock_db_session):
        """Test log listing with path filter"""
        with patch('src.api.deps.get_current_user') as mock_user, \
             patch('src.api.deps.get_db', return_value=mock_db_session):
            
            mock_user.return_value = User(
                id=1,
                username="admin",
                password_hash="hash",
                role=UserRole.ADMIN.value,
            )
            
            mock_logs = [
                OperationLog(
                    id=1,
                    request_time=datetime.now(),
                    source_ip="192.168.1.100",
                    request_path="/api/vm/config",
                    request_method="GET",
                    response_status=200,
                    response_time_ms=50,
                ),
            ]
            mock_db_session.query.return_value.filter.return_value.filter.return_value.count.return_value = 1
            mock_db_session.query.return_value.filter.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = mock_logs
            
            response = client.get(
                "/api/admin/logs?request_path=/api/vm",
                headers={"Authorization": "Bearer test_token"},
            )
            
            assert response.status_code == 200
    
    def test_list_logs_pagination(self, mock_db_session):
        """Test log listing pagination"""
        with patch('src.api.deps.get_current_user') as mock_user, \
             patch('src.api.deps.get_db', return_value=mock_db_session):
            
            mock_user.return_value = User(
                id=1,
                username="admin",
                password_hash="hash",
                role=UserRole.ADMIN.value,
            )
            
            mock_logs = [
                OperationLog(
                    id=i,
                    request_time=datetime.now(),
                    source_ip=f"192.168.1.{100+i}",
                    request_path="/api/vm/config",
                    request_method="GET",
                    response_status=200,
                    response_time_ms=50,
                )
                for i in range(10)
            ]
            mock_db_session.query.return_value.count.return_value = 100
            mock_db_session.query.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = mock_logs
            
            response = client.get(
                "/api/admin/logs?page=2&page_size=10",
                headers={"Authorization": "Bearer test_token"},
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["data"]["page"] == 2
            assert data["data"]["page_size"] == 10


@pytest.fixture
def mock_db_session():
    """Create mock database session"""
    session = MagicMock()
    return session
