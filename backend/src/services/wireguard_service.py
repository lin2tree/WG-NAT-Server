"""WireGuard service for key generation and config templates"""
import subprocess
from typing import Any

from jinja2 import Template

from ..core.config import settings


class WireGuardService:
    """Service for WireGuard key generation and configuration"""
    
    SERVER_CONFIG_TEMPLATE = """[Interface]
PrivateKey = {{ private_key }}
Address = {{ vpn_ip }}/24
ListenPort = {{ listen_port }}
PostUp = iptables -I FORWARD -i %i -j ACCEPT; iptables -I FORWARD -o %i -j ACCEPT; iptables -A FORWARD -i %i -o %i -j ACCEPT; iptables -I INPUT -i %i -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
PostDown = iptables -D FORWARD -i %i -j ACCEPT; iptables -D FORWARD -o %i -j ACCEPT; iptables -D FORWARD -i %i -o %i -j ACCEPT; iptables -D INPUT -i %i -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE
{% for peer in peers %}
[Peer]
PublicKey = {{ peer.public_key }}
AllowedIPs = {{ peer.allowed_ips }}
PersistentKeepalive = {{ keepalive }}

{% endfor %}
"""
    
    CLIENT_CONFIG_TEMPLATE = """[Interface]
PrivateKey = {{ private_key }}
Address = {{ vpn_ip }}/24

[Peer]
PublicKey = {{ server_public_key }}
Endpoint = {{ public_ip }}:{{ public_port }}
AllowedIPs = {{ vpn_subnet }}.0/24
PersistentKeepalive = {{ keepalive }}
"""
    
    def generate_keypair(self) -> tuple[str, str]:
        """Generate WireGuard key pair using wg command"""
        private_key_result = subprocess.run(
            ["wg", "genkey"],
            capture_output=True,
            text=True,
            check=True,
        )
        private_key = private_key_result.stdout.strip()
        
        public_key_result = subprocess.run(
            ["wg", "pubkey"],
            input=private_key,
            capture_output=True,
            text=True,
            check=True,
        )
        public_key = public_key_result.stdout.strip()
        
        return private_key, public_key
    
    def calculate_vpn_subnet(self, vm_ip: str) -> str:
        """Calculate VPN subnet from VM IP (A.B.C.D -> 10.C.D)"""
        parts = vm_ip.split(".")
        if len(parts) != 4:
            raise ValueError(f"Invalid IP address: {vm_ip}")
        
        return f"{settings.WIREGUARD_VPN_SUBNET}.{parts[2]}.{parts[3]}"
    
    def generate_server_config(
        self,
        private_key: str,
        vpn_ip: str,
        listen_port: int,
        client_public_keys: list[str],
        client_vpn_ips: list[str],
    ) -> str:
        """Generate WireGuard server configuration"""
        peers = [
            {
                "public_key": key,
                "allowed_ips": f"{ip}/32",
            }
            for key, ip in zip(client_public_keys, client_vpn_ips)
        ]
        
        template = Template(self.SERVER_CONFIG_TEMPLATE)
        return template.render(
            private_key=private_key,
            vpn_ip=vpn_ip,
            listen_port=listen_port,
            peers=peers,
            keepalive=settings.WIREGUARD_KEEPALIVE,
        )
    
    def generate_client_config(
        self,
        private_key: str,
        vpn_ip: str,
        vpn_subnet: str,
        server_public_key: str,
        public_ip: str,
        public_port: int,
    ) -> str:
        """Generate WireGuard client configuration"""
        template = Template(self.CLIENT_CONFIG_TEMPLATE)
        return template.render(
            private_key=private_key,
            vpn_ip=vpn_ip,
            vpn_subnet=vpn_subnet,
            server_public_key=server_public_key,
            public_ip=public_ip,
            public_port=public_port,
            keepalive=settings.WIREGUARD_KEEPALIVE,
        )
    
    def generate_client_configs(
        self,
        server_public_key: str,
        vpn_subnet: str,
        public_ip: str,
        public_port: int,
    ) -> list[dict[str, Any]]:
        """Generate multiple client configurations"""
        configs = []
        
        for i in range(1, settings.WIREGUARD_CLIENT_COUNT + 1):
            client_private_key, client_public_key = self.generate_keypair()
            client_vpn_ip = f"{vpn_subnet}.{i}"
            
            config_file = self.generate_client_config(
                private_key=client_private_key,
                vpn_ip=client_vpn_ip,
                vpn_subnet=vpn_subnet,
                server_public_key=server_public_key,
                public_ip=public_ip,
                public_port=public_port,
            )
            
            configs.append({
                "name": f"wg{i}",
                "private_key": client_private_key,
                "public_key": client_public_key,
                "vpn_ip": client_vpn_ip,
                "config_file": config_file,
            })
        
        return configs
    
    def generate_full_config(
        self,
        vm_ip: str,
        public_port: int,
        public_ip: str = "YOUR_PUBLIC_IP",
    ) -> dict[str, Any]:
        """Generate complete VPN configuration for a VM"""
        server_private_key, server_public_key = self.generate_keypair()
        vpn_subnet = self.calculate_vpn_subnet(vm_ip)
        server_vpn_ip = f"{vpn_subnet}.254"
        
        client_configs = self.generate_client_configs(
            server_public_key=server_public_key,
            vpn_subnet=vpn_subnet,
            public_ip=public_ip,
            public_port=public_port,
        )
        
        client_public_keys = [c["public_key"] for c in client_configs]
        client_vpn_ips = [c["vpn_ip"] for c in client_configs]
        
        server_config = self.generate_server_config(
            private_key=server_private_key,
            vpn_ip=server_vpn_ip,
            listen_port=settings.WIREGUARD_SERVER_PORT,
            client_public_keys=client_public_keys,
            client_vpn_ips=client_vpn_ips,
        )
        
        return {
            "server_private_key": server_private_key,
            "server_public_key": server_public_key,
            "server_vpn_ip": server_vpn_ip,
            "server_config": server_config,
            "client_configs": client_configs,
        }
