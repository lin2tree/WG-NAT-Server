"""Unit tests for WireGuard key generation service"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
from unittest.mock import patch, MagicMock

from src.services.wireguard_service import WireGuardService


class TestWireGuardService:
    """Tests for WireGuard key generation"""
    
    def test_generate_keypair_returns_tuple(self):
        """Test that generate_keypair returns a tuple of two strings"""
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = [
                MagicMock(stdout="private_key_base64_encoded==\n"),
                MagicMock(stdout="public_key_base64_encoded==\n"),
            ]
            
            service = WireGuardService()
            private_key, public_key = service.generate_keypair()
            
            assert isinstance(private_key, str)
            assert isinstance(public_key, str)
            assert len(private_key) > 0
            assert len(public_key) > 0
    
    def test_generate_keypair_calls_wg_commands(self):
        """Test that generate_keypair calls wg genkey and wg pubkey"""
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = [
                MagicMock(stdout="private_key==\n"),
                MagicMock(stdout="public_key==\n"),
            ]
            
            service = WireGuardService()
            service.generate_keypair()
            
            assert mock_run.call_count == 2
            calls = mock_run.call_args_list
            assert calls[0][0][0] == ["wg", "genkey"]
            assert calls[1][0][0] == ["wg", "pubkey"]
    
    def test_generate_client_configs_returns_five_configs(self):
        """Test that generate_client_configs returns exactly 5 client configs"""
        service = WireGuardService()
        server_public_key = "server_public_key_example=="
        vpn_subnet = "10.1.100"
        public_ip = "203.0.113.1"
        public_port = 10001
        
        with patch.object(service, 'generate_keypair') as mock_keypair:
            mock_keypair.return_value = ("client_private==", "client_public==")
            
            configs = service.generate_client_configs(
                server_public_key=server_public_key,
                vpn_subnet=vpn_subnet,
                public_ip=public_ip,
                public_port=public_port,
            )
            
            assert len(configs) == 5
            for i, config in enumerate(configs):
                assert "name" in config
                assert config["name"] == f"client{i + 1}"
                assert "private_key" in config
                assert "public_key" in config
                assert "vpn_ip" in config
                assert "config_file" in config
    
    def test_generate_server_config_returns_valid_config(self):
        """Test that generate_server_config returns valid WireGuard config"""
        service = WireGuardService()
        
        config = service.generate_server_config(
            private_key="server_private_key==",
            vpn_ip="10.1.100.254",
            listen_port=2588,
            client_public_keys=["client1_pub==", "client2_pub=="],
            client_vpn_ips=["10.1.100.1", "10.1.100.2"],
        )
        
        assert "[Interface]" in config
        assert "PrivateKey = server_private_key==" in config
        assert "Address = 10.1.100.254/24" in config
        assert "ListenPort = 2588" in config
        assert "[Peer]" in config
        assert "client1_pub==" in config
    
    def test_calculate_vpn_subnet_from_ip(self):
        """Test VPN subnet calculation from VM IP"""
        service = WireGuardService()
        
        vpn_subnet = service.calculate_vpn_subnet("192.168.1.100")
        
        assert vpn_subnet == "10.1.100"
    
    def test_calculate_vpn_subnet_different_ips(self):
        """Test VPN subnet calculation for different VM IPs"""
        service = WireGuardService()
        
        assert service.calculate_vpn_subnet("192.168.1.100") == "10.1.100"
        assert service.calculate_vpn_subnet("192.168.2.50") == "10.2.50"
        assert service.calculate_vpn_subnet("10.0.5.200") == "10.5.200"
