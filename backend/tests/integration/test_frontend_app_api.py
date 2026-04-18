"""Integration tests for Frontend App API endpoints"""
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


client = TestClient(app)


class TestFrontendAppConfigApi:
    """Integration tests for Frontend App config API"""
    
    def test_get_client_configs_success(self, mock_db_session):
        """Test successful client configs retrieval"""
        with patch('src.api.deps.verify_frontend_app_token') as mock_verify, \
             patch('src.api.deps.get_db', return_value=mock_db_session):
            
            mock_verify.return_value = True
            
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
            )
            mock_db_session.query.return_value.filter.return_value.first.return_value = mock_config
            
            response = client.get(
                "/api/frontend/configs/192.168.1.100",
                headers={"Authorization": "Bearer test_token"},
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["vm_ip"] == "192.168.1.100"
            assert len(data["data"]["clients"]) == 1
    
    def test_get_client_configs_not_found(self, mock_db_session):
        """Test client configs retrieval when not found"""
        with patch('src.api.deps.verify_frontend_app_token') as mock_verify, \
             patch('src.api.deps.get_db', return_value=mock_db_session):
            
            mock_verify.return_value = True
            mock_db_session.query.return_value.filter.return_value.first.return_value = None
            
            response = client.get(
                "/api/frontend/configs/192.168.1.100",
                headers={"Authorization": "Bearer test_token"},
            )
            
            assert response.status_code == 404
    
    def test_get_client_configs_not_started(self, mock_db_session):
        """Test client configs retrieval when not started"""
        with patch('src.api.deps.verify_frontend_app_token') as mock_verify, \
             patch('src.api.deps.get_db', return_value=mock_db_session):
            
            mock_verify.return_value = True
            
            mock_config = VpnConfig(
                id=1,
                vm_ip="192.168.1.100",
                server_private_key="server_private==",
                server_public_key="server_public==",
                client_configs=[],
                status=VpnStatus.INIT.value,
            )
            mock_db_session.query.return_value.filter.return_value.first.return_value = mock_config
            
            response = client.get(
                "/api/frontend/configs/192.168.1.100",
                headers={"Authorization": "Bearer test_token"},
            )
            
            assert response.status_code == 400


class TestFrontendAppDestroyApi:
    """Integration tests for Frontend App destroy API"""
    
    def test_destroy_config_success(self, mock_db_session):
        """Test successful config destruction"""
        with patch('src.api.deps.verify_frontend_app_token') as mock_verify, \
             patch('src.api.deps.get_db', return_value=mock_db_session):
            
            mock_verify.return_value = True
            
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
            
            response = client.post(
                "/api/frontend/configs/192.168.1.100/destroy",
                headers={"Authorization": "Bearer test_token"},
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "destroyed" in data["message"].lower()
    
    def test_destroy_config_not_found(self, mock_db_session):
        """Test config destruction when not found"""
        with patch('src.api.deps.verify_frontend_app_token') as mock_verify, \
             patch('src.api.deps.get_db', return_value=mock_db_session):
            
            mock_verify.return_value = True
            mock_db_session.query.return_value.filter.return_value.first.return_value = None
            
            response = client.post(
                "/api/frontend/configs/192.168.1.100/destroy",
                headers={"Authorization": "Bearer test_token"},
            )
            
            assert response.status_code == 404
    
    def test_destroy_config_init_status(self, mock_db_session):
        """Test config destruction when in init status"""
        with patch('src.api.deps.verify_frontend_app_token') as mock_verify, \
             patch('src.api.deps.get_db', return_value=mock_db_session):
            
            mock_verify.return_value = True
            
            mock_config = VpnConfig(
                id=1,
                vm_ip="192.168.1.100",
                server_private_key="server_private==",
                server_public_key="server_public==",
                client_configs=[],
                status=VpnStatus.INIT.value,
                created_at=datetime.now(),
            )
            mock_db_session.query.return_value.filter.return_value.first.return_value = mock_config
            
            response = client.post(
                "/api/frontend/configs/192.168.1.100/destroy",
                headers={"Authorization": "Bearer test_token"},
            )
            
            assert response.status_code == 200


class TestFrontendAppDownloadApi:
    """Integration tests for Frontend App download API"""
    
    def test_download_client_config_success(self, mock_db_session):
        """Test successful client config download"""
        with patch('src.api.deps.verify_frontend_app_token') as mock_verify, \
             patch('src.api.deps.get_db', return_value=mock_db_session):
            
            mock_verify.return_value = True
            
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
            )
            mock_db_session.query.return_value.filter.return_value.first.return_value = mock_config
            
            response = client.get(
                "/api/frontend/configs/192.168.1.100/download/client1",
                headers={"Authorization": "Bearer test_token"},
            )
            
            assert response.status_code == 200
            assert "attachment" in response.headers.get("content-disposition", "")
    
    def test_download_client_config_not_found(self, mock_db_session):
        """Test client config download when client not found"""
        with patch('src.api.deps.verify_frontend_app_token') as mock_verify, \
             patch('src.api.deps.get_db', return_value=mock_db_session):
            
            mock_verify.return_value = True
            
            mock_config = VpnConfig(
                id=1,
                vm_ip="192.168.1.100",
                server_private_key="server_private==",
                server_public_key="server_public==",
                client_configs=[],
                status=VpnStatus.STARTED.value,
            )
            mock_db_session.query.return_value.filter.return_value.first.return_value = mock_config
            
            response = client.get(
                "/api/frontend/configs/192.168.1.100/download/nonexistent",
                headers={"Authorization": "Bearer test_token"},
            )
            
            assert response.status_code == 404


@pytest.fixture
def mock_db_session():
    """Create mock database session"""
    session = MagicMock()
    return session
