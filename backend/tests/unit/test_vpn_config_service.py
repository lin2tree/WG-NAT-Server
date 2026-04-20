"""Unit tests for VPN config service"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch

from src.services.vpn_config_service import VpnConfigService
from src.models.vpn_config import VpnConfig, VpnStatus
from src.models.resource_pool import ResourcePool
from src.models.vpn_archive import VpnArchive


class TestVpnConfigService:
    """Tests for VPN config service"""
    
    def test_get_or_create_config_creates_new_config(self):
        """Test that get_or_create_config creates new config when not exists"""
        mock_db = MagicMock()
        mock_resource_pool = ResourcePool(
            id=1,
            internal_ip="192.168.1.100",
            public_port=10001,
        )
        
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            None,
            mock_resource_pool,
            None,
        ]
        
        mock_config_data = {
            "server_private_key": "private==",
            "server_public_key": "public==",
            "client_configs": [],
        }
        
        with patch.object(VpnConfigService, '__init__', lambda self, db: None):
            service = VpnConfigService(mock_db)
            service.db = mock_db
            service.wireguard = MagicMock()
            service.wireguard.generate_full_config.return_value = mock_config_data
            
            config = service.get_or_create_config("192.168.1.100")
            
            assert config is not None
            assert config.vm_ip == "192.168.1.100"
            mock_db.add.assert_called()
            mock_db.commit.assert_called()
    
    def test_get_or_create_config_returns_existing_config(self):
        """Test that get_or_create_config returns existing config"""
        mock_db = MagicMock()
        existing_config = VpnConfig(
            id=1,
            vm_ip="192.168.1.100",
            server_private_key="private==",
            server_public_key="public==",
            client_configs=[],
            status=VpnStatus.INIT.value,
        )
        mock_db.query.return_value.filter.return_value.first.return_value = existing_config
        
        with patch.object(VpnConfigService, '__init__', lambda self, db: None):
            service = VpnConfigService(mock_db)
            service.db = mock_db
            
            config = service.get_or_create_config("192.168.1.100")
            
            assert config.id == 1
            assert config.vm_ip == "192.168.1.100"
            mock_db.add.assert_not_called()
    
    def test_update_status_to_started(self):
        """Test updating config status to started"""
        mock_db = MagicMock()
        config = VpnConfig(
            id=1,
            vm_ip="192.168.1.100",
            server_private_key="private==",
            server_public_key="public==",
            client_configs=[],
            status=VpnStatus.INIT.value,
        )
        
        with patch.object(VpnConfigService, '__init__', lambda self, db: None):
            service = VpnConfigService(mock_db)
            service.db = mock_db
            
            service.update_status(config, VpnStatus.STARTED)
            
            assert config.status == VpnStatus.STARTED.value
            assert config.started_at is not None
            mock_db.commit.assert_called()
    
    def test_archive_config_moves_to_archive_table(self):
        """Test that archive_config moves config to archive table"""
        mock_db = MagicMock()
        config = VpnConfig(
            id=1,
            vm_ip="192.168.1.100",
            server_private_key="private==",
            server_public_key="public==",
            client_configs=[],
            status=VpnStatus.STARTED.value,
            created_at=datetime.now(),
        )
        
        with patch.object(VpnConfigService, '__init__', lambda self, db: None):
            service = VpnConfigService(mock_db)
            service.db = mock_db
            
            service.archive_config(config)
            
            mock_db.add.assert_called()
            mock_db.delete.assert_called_with(config)
            mock_db.commit.assert_called()
    
    def test_get_config_by_ip_returns_config(self):
        """Test getting config by VM IP"""
        mock_db = MagicMock()
        expected_config = VpnConfig(
            id=1,
            vm_ip="192.168.1.100",
            server_private_key="private==",
            server_public_key="public==",
            client_configs=[],
            status=VpnStatus.INIT.value,
        )
        mock_db.query.return_value.filter.return_value.first.return_value = expected_config
        
        with patch.object(VpnConfigService, '__init__', lambda self, db: None):
            service = VpnConfigService(mock_db)
            service.db = mock_db
            
            config = service.get_config_by_ip("192.168.1.100")
            
            assert config.vm_ip == "192.168.1.100"
    
    def test_get_config_by_ip_returns_none_when_not_found(self):
        """Test getting config by IP returns None when not exists"""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        with patch.object(VpnConfigService, '__init__', lambda self, db: None):
            service = VpnConfigService(mock_db)
            service.db = mock_db
            
            config = service.get_config_by_ip("192.168.1.100")
            
            assert config is None
    
    def test_check_ip_in_resource_pool_returns_true(self):
        """Test checking if IP is in resource pool"""
        mock_db = MagicMock()
        mock_resource_pool = ResourcePool(
            id=1,
            internal_ip="192.168.1.100",
            public_port=10001,
        )
        mock_db.query.return_value.filter.return_value.first.return_value = mock_resource_pool
        
        with patch.object(VpnConfigService, '__init__', lambda self, db: None):
            service = VpnConfigService(mock_db)
            service.db = mock_db
            
            result = service.check_ip_in_resource_pool("192.168.1.100")
            
            assert result is not None
            assert result.internal_ip == "192.168.1.100"
    
    def test_check_ip_in_resource_pool_returns_none(self):
        """Test checking IP not in resource pool"""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        with patch.object(VpnConfigService, '__init__', lambda self, db: None):
            service = VpnConfigService(mock_db)
            service.db = mock_db
            
            result = service.check_ip_in_resource_pool("192.168.1.100")
            
            assert result is None
