"""Integration tests for VM API endpoints"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from src.main import app
from src.models.vpn_config import VpnConfig, VpnStatus
from src.models.resource_pool import ResourcePool


client = TestClient(app)


class TestVmConfigApi:
    """Integration tests for VM config API"""
    
    def test_get_config_success(self, mock_db_session):
        """Test successful config retrieval"""
        with patch('src.api.deps.verify_vm_request') as mock_verify, \
             patch('src.api.deps.get_db', return_value=mock_db_session):
            
            mock_verify.return_value = "192.168.1.100"
            
            mock_resource_pool = ResourcePool(
                id=1,
                internal_ip="192.168.1.100",
                public_port=10001,
            )
            mock_db_session.query.return_value.filter.return_value.first.side_effect = [
                None,
                mock_resource_pool,
            ]
            
            response = client.get(
                "/api/vm/config",
                headers={"X-VM-Token": "test_token"},
            )
            
            assert response.status_code == 200
    
    def test_get_config_ip_not_in_pool(self, mock_db_session):
        """Test config request with IP not in resource pool"""
        with patch('src.api.deps.verify_vm_request') as mock_verify, \
             patch('src.api.deps.get_db', return_value=mock_db_session):
            
            mock_verify.return_value = "192.168.1.999"
            mock_db_session.query.return_value.filter.return_value.first.return_value = None
            
            response = client.get(
                "/api/vm/config",
                headers={"X-VM-Token": "test_token"},
            )
            
            assert response.status_code == 400
            assert "该IP未在资源池中配置" in response.json().get("detail", "")
    
    def test_get_config_already_started(self, mock_db_session):
        """Test config request when already started"""
        with patch('src.api.deps.verify_vm_request') as mock_verify, \
             patch('src.api.deps.get_db', return_value=mock_db_session):
            
            mock_verify.return_value = "192.168.1.100"
            
            existing_config = VpnConfig(
                id=1,
                vm_ip="192.168.1.100",
                server_private_key="private==",
                server_public_key="public==",
                client_configs=[],
                status=VpnStatus.STARTED.value,
            )
            mock_db_session.query.return_value.filter.return_value.first.return_value = existing_config
            
            response = client.get(
                "/api/vm/config",
                headers={"X-VM-Token": "test_token"},
            )
            
            assert response.status_code == 400
            assert "配置已启动" in response.json().get("detail", "")
    
    def test_get_config_idempotent(self, mock_db_session):
        """Test that config request is idempotent for init status"""
        with patch('src.api.deps.verify_vm_request') as mock_verify, \
             patch('src.api.deps.get_db', return_value=mock_db_session):
            
            mock_verify.return_value = "192.168.1.100"
            
            existing_config = VpnConfig(
                id=1,
                vm_ip="192.168.1.100",
                server_private_key="existing_private==",
                server_public_key="existing_public==",
                client_configs=[],
                status=VpnStatus.INIT.value,
            )
            mock_db_session.query.return_value.filter.return_value.first.return_value = existing_config
            
            response1 = client.get(
                "/api/vm/config",
                headers={"X-VM-Token": "test_token"},
            )
            response2 = client.get(
                "/api/vm/config",
                headers={"X-VM-Token": "test_token"},
            )
            
            assert response1.status_code == 200
            assert response2.status_code == 200
            assert response1.json() == response2.json()


class TestVmReadyApi:
    """Integration tests for VM ready API"""
    
    def test_report_ready_success(self, mock_db_session):
        """Test successful ready report"""
        with patch('src.api.deps.verify_vm_request') as mock_verify, \
             patch('src.api.deps.get_db', return_value=mock_db_session):
            
            mock_verify.return_value = "192.168.1.100"
            
            existing_config = VpnConfig(
                id=1,
                vm_ip="192.168.1.100",
                server_private_key="private==",
                server_public_key="public==",
                client_configs=[],
                status=VpnStatus.INIT.value,
            )
            mock_db_session.query.return_value.filter.return_value.first.return_value = existing_config
            
            response = client.post(
                "/api/vm/ready",
                headers={"X-VM-Token": "test_token"},
            )
            
            assert response.status_code == 200
            assert "started" in response.json().get("message", "").lower()
    
    def test_report_ready_config_destroyed(self, mock_db_session):
        """Test ready report when config was destroyed"""
        with patch('src.api.deps.verify_vm_request') as mock_verify, \
             patch('src.api.deps.get_db', return_value=mock_db_session):
            
            mock_verify.return_value = "192.168.1.100"
            mock_db_session.query.return_value.filter.return_value.first.return_value = None
            
            response = client.post(
                "/api/vm/ready",
                headers={"X-VM-Token": "test_token"},
            )
            
            assert response.status_code == 400
            assert "记录已销毁" in response.json().get("detail", "")
    
    def test_report_ready_idempotent(self, mock_db_session):
        """Test that ready report is idempotent"""
        with patch('src.api.deps.verify_vm_request') as mock_verify, \
             patch('src.api.deps.get_db', return_value=mock_db_session):
            
            mock_verify.return_value = "192.168.1.100"
            
            existing_config = VpnConfig(
                id=1,
                vm_ip="192.168.1.100",
                server_private_key="private==",
                server_public_key="public==",
                client_configs=[],
                status=VpnStatus.STARTED.value,
            )
            mock_db_session.query.return_value.filter.return_value.first.return_value = existing_config
            
            response1 = client.post(
                "/api/vm/ready",
                headers={"X-VM-Token": "test_token"},
            )
            response2 = client.post(
                "/api/vm/ready",
                headers={"X-VM-Token": "test_token"},
            )
            
            assert response1.status_code == 200
            assert response2.status_code == 200


@pytest.fixture
def mock_db_session():
    """Create mock database session"""
    session = MagicMock()
    return session
