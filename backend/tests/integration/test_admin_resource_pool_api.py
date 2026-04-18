"""Integration tests for Admin Resource Pool API endpoints"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from datetime import datetime

from src.main import app
from src.models.port_range import PortRange
from src.models.resource_pool import ResourcePool
from src.models.user import User, UserRole


client = TestClient(app)


class TestPortRangeApi:
    """Integration tests for port range API"""
    
    def test_get_port_range_success(self, mock_db_session):
        """Test successful port range retrieval"""
        with patch('src.api.deps.get_current_user') as mock_user, \
             patch('src.api.deps.get_db', return_value=mock_db_session):
            
            mock_user.return_value = User(
                id=1,
                username="admin",
                password_hash="hash",
                role=UserRole.ADMIN.value,
            )
            
            mock_port_range = PortRange(
                id=1,
                start_port=10000,
                end_port=20000,
            )
            mock_db_session.query.return_value.first.return_value = mock_port_range
            
            response = client.get(
                "/api/admin/port-range",
                headers={"Authorization": "Bearer test_token"},
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["start_port"] == 10000
            assert data["data"]["end_port"] == 20000
    
    def test_get_port_range_not_configured(self, mock_db_session):
        """Test port range retrieval when not configured"""
        with patch('src.api.deps.get_current_user') as mock_user, \
             patch('src.api.deps.get_db', return_value=mock_db_session):
            
            mock_user.return_value = User(
                id=1,
                username="admin",
                password_hash="hash",
                role=UserRole.ADMIN.value,
            )
            mock_db_session.query.return_value.first.return_value = None
            
            response = client.get(
                "/api/admin/port-range",
                headers={"Authorization": "Bearer test_token"},
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["data"] is None
    
    def test_set_port_range_root_only(self, mock_db_session):
        """Test that only root can set port range"""
        with patch('src.api.deps.get_current_root_user') as mock_root, \
             patch('src.api.deps.get_db', return_value=mock_db_session):
            
            mock_root.return_value = User(
                id=1,
                username="root",
                password_hash="hash",
                role=UserRole.ROOT.value,
            )
            
            mock_port_range = PortRange(
                id=1,
                start_port=10000,
                end_port=20000,
            )
            mock_db_session.query.return_value.first.return_value = None
            
            response = client.post(
                "/api/admin/port-range?start_port=10000&end_port=20000",
                headers={"Authorization": "Bearer test_token"},
            )
            
            assert response.status_code == 200


class TestResourcePoolApi:
    """Integration tests for resource pool API"""
    
    def test_list_resource_pool_success(self, mock_db_session):
        """Test successful resource pool listing"""
        with patch('src.api.deps.get_current_user') as mock_user, \
             patch('src.api.deps.get_db', return_value=mock_db_session):
            
            mock_user.return_value = User(
                id=1,
                username="admin",
                password_hash="hash",
                role=UserRole.ADMIN.value,
            )
            
            mock_mappings = [
                ResourcePool(id=1, internal_ip="192.168.1.100", public_port=10001),
                ResourcePool(id=2, internal_ip="192.168.1.101", public_port=10002),
            ]
            mock_db_session.query.return_value.filter.return_value.count.return_value = 2
            mock_db_session.query.return_value.filter.return_value.offset.return_value.limit.return_value.all.return_value = mock_mappings
            
            response = client.get(
                "/api/admin/resource-pool",
                headers={"Authorization": "Bearer test_token"},
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["total"] == 2
    
    def test_import_ips_root_only(self, mock_db_session):
        """Test that only root can import IPs"""
        with patch('src.api.deps.get_current_root_user') as mock_root, \
             patch('src.api.deps.get_db', return_value=mock_db_session):
            
            mock_root.return_value = User(
                id=1,
                username="root",
                password_hash="hash",
                role=UserRole.ROOT.value,
            )
            
            mock_port_range = PortRange(id=1, start_port=10000, end_port=20000)
            mock_db_session.query.return_value.filter.return_value.first.side_effect = [
                None,
                mock_port_range,
                None,
                None,
            ]
            mock_db_session.query.return_value.filter.return_value.count.return_value = 0
            
            response = client.post(
                "/api/admin/resource-pool/import",
                json=["192.168.1.100", "192.168.1.101"],
                headers={"Authorization": "Bearer test_token"},
            )
            
            assert response.status_code == 200
    
    def test_delete_mapping_root_only(self, mock_db_session):
        """Test that only root can delete mappings"""
        with patch('src.api.deps.get_current_root_user') as mock_root, \
             patch('src.api.deps.get_db', return_value=mock_db_session):
            
            mock_root.return_value = User(
                id=1,
                username="root",
                password_hash="hash",
                role=UserRole.ROOT.value,
            )
            
            mock_mapping = ResourcePool(
                id=1,
                internal_ip="192.168.1.100",
                public_port=10001,
            )
            mock_db_session.query.return_value.filter.return_value.first.return_value = mock_mapping
            
            response = client.delete(
                "/api/admin/resource-pool/1",
                headers={"Authorization": "Bearer test_token"},
            )
            
            assert response.status_code == 200
    
    def test_export_mappings(self, mock_db_session):
        """Test exporting mappings as CSV"""
        with patch('src.api.deps.get_current_user') as mock_user, \
             patch('src.api.deps.get_db', return_value=mock_db_session):
            
            mock_user.return_value = User(
                id=1,
                username="admin",
                password_hash="hash",
                role=UserRole.ADMIN.value,
            )
            
            mock_mappings = [
                ResourcePool(id=1, internal_ip="192.168.1.100", public_port=10001),
            ]
            mock_db_session.query.return_value.filter.return_value.all.return_value = mock_mappings
            
            response = client.get(
                "/api/admin/resource-pool/export",
                headers={"Authorization": "Bearer test_token"},
            )
            
            assert response.status_code == 200
            assert "attachment" in response.headers.get("content-disposition", "")


@pytest.fixture
def mock_db_session():
    """Create mock database session"""
    session = MagicMock()
    return session
