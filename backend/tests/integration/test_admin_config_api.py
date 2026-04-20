"""Integration tests for Admin VPN Config API endpoints"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from datetime import datetime

from src.main import app
from src.models.vpn_config import VpnConfig, VpnStatus
from src.models.vpn_archive import VpnArchive
from src.models.user import User, UserRole


client = TestClient(app)


class TestAdminConfigListApi:
    """Integration tests for admin config list API"""
    
    def test_list_configs_success(self, mock_db_session):
        """Test successful config listing"""
        with patch('src.api.deps.get_current_user') as mock_user, \
             patch('src.api.deps.get_db', return_value=mock_db_session):
            
            mock_user.return_value = User(
                id=1,
                username="admin",
                password_hash="hash",
                role=UserRole.ADMIN.value,
            )
            
            mock_configs = [
                VpnConfig(
                    id=1,
                    vm_ip="192.168.1.100",
                    server_private_key="private1==",
                    server_public_key="public1==",
                    client_configs=[],
                    status=VpnStatus.STARTED.value,
                    created_at=datetime.now(),
                ),
                VpnConfig(
                    id=2,
                    vm_ip="192.168.1.101",
                    server_private_key="private2==",
                    server_public_key="public2==",
                    client_configs=[],
                    status=VpnStatus.INIT.value,
                    created_at=datetime.now(),
                ),
            ]
            mock_db_session.query.return_value.count.return_value = 2
            mock_db_session.query.return_value.offset.return_value.limit.return_value.all.return_value = mock_configs
            
            response = client.get(
                "/api/admin/configs",
                headers={"Authorization": "Bearer test_token"},
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["total"] == 2
            assert len(data["data"]["items"]) == 2
    
    def test_list_configs_with_status_filter(self, mock_db_session):
        """Test config listing with status filter"""
        with patch('src.api.deps.get_current_user') as mock_user, \
             patch('src.api.deps.get_db', return_value=mock_db_session):
            
            mock_user.return_value = User(
                id=1,
                username="admin",
                password_hash="hash",
                role=UserRole.ADMIN.value,
            )
            
            mock_configs = [
                VpnConfig(
                    id=1,
                    vm_ip="192.168.1.100",
                    server_private_key="private==",
                    server_public_key="public==",
                    client_configs=[],
                    status=VpnStatus.STARTED.value,
                    created_at=datetime.now(),
                ),
            ]
            mock_db_session.query.return_value.filter.return_value.count.return_value = 1
            mock_db_session.query.return_value.filter.return_value.offset.return_value.limit.return_value.all.return_value = mock_configs
            
            response = client.get(
                "/api/admin/configs?status=started",
                headers={"Authorization": "Bearer test_token"},
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["data"]["total"] == 1
    
    def test_list_configs_with_ip_filter(self, mock_db_session):
        """Test config listing with IP filter"""
        with patch('src.api.deps.get_current_user') as mock_user, \
             patch('src.api.deps.get_db', return_value=mock_db_session):
            
            mock_user.return_value = User(
                id=1,
                username="admin",
                password_hash="hash",
                role=UserRole.ADMIN.value,
            )
            
            mock_configs = [
                VpnConfig(
                    id=1,
                    vm_ip="192.168.1.100",
                    server_private_key="private==",
                    server_public_key="public==",
                    client_configs=[],
                    status=VpnStatus.STARTED.value,
                    created_at=datetime.now(),
                ),
            ]
            mock_db_session.query.return_value.filter.return_value.count.return_value = 1
            mock_db_session.query.return_value.filter.return_value.offset.return_value.limit.return_value.all.return_value = mock_configs
            
            response = client.get(
                "/api/admin/configs?vm_ip=192.168.1",
                headers={"Authorization": "Bearer test_token"},
            )
            
            assert response.status_code == 200


class TestAdminConfigDetailApi:
    """Integration tests for admin config detail API"""
    
    def test_get_config_detail_success(self, mock_db_session):
        """Test successful config detail retrieval"""
        with patch('src.api.deps.get_current_user') as mock_user, \
             patch('src.api.deps.get_db', return_value=mock_db_session):
            
            mock_user.return_value = User(
                id=1,
                username="admin",
                password_hash="hash",
                role=UserRole.ADMIN.value,
            )
            
            mock_config = VpnConfig(
                id=1,
                vm_ip="192.168.1.100",
                server_private_key="server_private==",
                server_public_key="server_public==",
                client_configs=[
                    {
                        "name": "client1",
                        "private_key": "client1_private==",
                        "public_key": "client1_public==",
                        "vpn_ip": "10.1.100.1",
                    },
                ],
                status=VpnStatus.STARTED.value,
                created_at=datetime.now(),
            )
            mock_db_session.query.return_value.filter.return_value.first.return_value = mock_config
            
            response = client.get(
                "/api/admin/configs/192.168.1.100",
                headers={"Authorization": "Bearer test_token"},
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["vm_ip"] == "192.168.1.100"
            assert data["data"]["server_private_key"] == "***"
    
    def test_get_config_detail_root_shows_secrets(self, mock_db_session):
        """Test that root user can see secrets"""
        with patch('src.api.deps.get_current_user') as mock_user, \
             patch('src.api.deps.get_db', return_value=mock_db_session):
            
            mock_user.return_value = User(
                id=1,
                username="root",
                password_hash="hash",
                role=UserRole.ROOT.value,
            )
            
            mock_config = VpnConfig(
                id=1,
                vm_ip="192.168.1.100",
                server_private_key="server_private==",
                server_public_key="server_public==",
                client_configs=[
                    {
                        "name": "client1",
                        "private_key": "client1_private==",
                        "public_key": "client1_public==",
                        "vpn_ip": "10.1.100.1",
                    },
                ],
                status=VpnStatus.STARTED.value,
                created_at=datetime.now(),
            )
            mock_db_session.query.return_value.filter.return_value.first.return_value = mock_config
            
            response = client.get(
                "/api/admin/configs/192.168.1.100",
                headers={"Authorization": "Bearer test_token"},
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["data"]["server_private_key"] == "server_private=="
    
    def test_get_config_detail_not_found(self, mock_db_session):
        """Test config detail retrieval when not found"""
        with patch('src.api.deps.get_current_user') as mock_user, \
             patch('src.api.deps.get_db', return_value=mock_db_session):
            
            mock_user.return_value = User(
                id=1,
                username="admin",
                password_hash="hash",
                role=UserRole.ADMIN.value,
            )
            mock_db_session.query.return_value.filter.return_value.first.return_value = None
            
            response = client.get(
                "/api/admin/configs/192.168.1.100",
                headers={"Authorization": "Bearer test_token"},
            )
            
            assert response.status_code == 404


class TestAdminConfigHistoryApi:
    """Integration tests for admin config history API"""
    
    def test_get_config_history_success(self, mock_db_session):
        """Test successful config history retrieval"""
        with patch('src.api.deps.get_current_user') as mock_user, \
             patch('src.api.deps.get_db', return_value=mock_db_session):
            
            mock_user.return_value = User(
                id=1,
                username="admin",
                password_hash="hash",
                role=UserRole.ADMIN.value,
            )
            
            mock_archives = [
                VpnArchive(
                    id=1,
                    vm_ip="192.168.1.100",
                    server_private_key="private==",
                    server_public_key="public==",
                    client_configs=[],
                    status="deleted",
                    created_at=datetime.now(),
                    deleted_at=datetime.now(),
                ),
            ]
            mock_db_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = mock_archives
            
            response = client.get(
                "/api/admin/configs/192.168.1.100/history",
                headers={"Authorization": "Bearer test_token"},
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["data"]) == 1


class TestAdminDownloadApi:
    """Integration tests for admin download API"""
    
    def test_download_server_config_root_only(self, mock_db_session):
        """Test that only root can download server config"""
        with patch('src.api.deps.get_current_root_user') as mock_root, \
             patch('src.api.deps.get_db', return_value=mock_db_session):
            
            mock_root.return_value = User(
                id=1,
                username="root",
                password_hash="hash",
                role=UserRole.ROOT.value,
            )
            
            mock_config = VpnConfig(
                id=1,
                vm_ip="192.168.1.100",
                server_private_key="server_private==",
                server_public_key="server_public==",
                client_configs=[],
                status=VpnStatus.STARTED.value,
                created_at=datetime.now(),
            )
            mock_db_session.query.return_value.filter.return_value.first.return_value = mock_config
            
            response = client.get(
                "/api/admin/configs/192.168.1.100/download/server",
                headers={"Authorization": "Bearer test_token"},
            )
            
            assert response.status_code == 200
            assert "attachment" in response.headers.get("content-disposition", "")
    
    def test_download_client_config_root_only(self, mock_db_session):
        """Test that only root can download client config"""
        with patch('src.api.deps.get_current_root_user') as mock_root, \
             patch('src.api.deps.get_db', return_value=mock_db_session):
            
            mock_root.return_value = User(
                id=1,
                username="root",
                password_hash="hash",
                role=UserRole.ROOT.value,
            )
            
            mock_config = VpnConfig(
                id=1,
                vm_ip="192.168.1.100",
                server_private_key="server_private==",
                server_public_key="server_public==",
                client_configs=[
                    {
                        "name": "client1",
                        "private_key": "client1_private==",
                        "public_key": "client1_public==",
                        "vpn_ip": "10.1.100.1",
                        "config_file": "[Interface]\nPrivateKey = client1_private==",
                    },
                ],
                status=VpnStatus.STARTED.value,
                created_at=datetime.now(),
            )
            mock_db_session.query.return_value.filter.return_value.first.return_value = mock_config
            
            response = client.get(
                "/api/admin/configs/192.168.1.100/download/client/client1",
                headers={"Authorization": "Bearer test_token"},
            )
            
            assert response.status_code == 200


@pytest.fixture
def mock_db_session():
    """Create mock database session"""
    session = MagicMock()
    return session
