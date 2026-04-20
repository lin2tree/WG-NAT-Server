"""VPN configuration service"""
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from ..core.config import settings
from ..models.vpn_config import VpnConfig, VpnStatus
from ..models.vpn_archive import VpnArchive
from ..models.resource_pool import ResourcePool
from ..models.public_ip import PublicIP
from .wireguard_service import WireGuardService


class VpnConfigService:
    """Service for managing VPN configurations"""
    
    def __init__(self, db: Session):
        self.db = db
        self.wireguard = WireGuardService()
    
    def check_ip_in_resource_pool(self, ip: str) -> ResourcePool | None:
        """Check if IP is in resource pool"""
        return self.db.query(ResourcePool).filter(
            ResourcePool.internal_ip == ip,
            ResourcePool.deleted_at.is_(None),
        ).first()
    
    def get_public_ip_for_vm(self, resource_pool: ResourcePool) -> str:
        """Get public IP for VM from resource pool or default"""
        if resource_pool.public_ip_id and resource_pool.public_ip:
            return resource_pool.public_ip.ip_address
        
        default_public_ip = self.db.query(PublicIP).filter(
            PublicIP.is_default == True,
        ).first()
        
        if default_public_ip:
            return default_public_ip.ip_address
        
        return "YOUR_PUBLIC_IP"
    
    def get_config_by_ip(self, vm_ip: str) -> VpnConfig | None:
        """Get VPN config by VM IP"""
        return self.db.query(VpnConfig).filter(
            VpnConfig.vm_ip == vm_ip,
        ).first()
    
    def get_or_create_config(
        self,
        vm_ip: str,
        public_ip: str = "YOUR_PUBLIC_IP",
    ) -> VpnConfig:
        """Get existing config or create new one"""
        existing_config = self.get_config_by_ip(vm_ip)
        
        if existing_config:
            if existing_config.status == VpnStatus.STARTED.value:
                raise ValueError("配置已启动，无法重新获取")
            return existing_config
        
        resource_pool = self.check_ip_in_resource_pool(vm_ip)
        if not resource_pool:
            raise ValueError("该IP未在资源池中配置")
        
        actual_public_ip = self.get_public_ip_for_vm(resource_pool)
        
        config_data = self.wireguard.generate_full_config(
            vm_ip=vm_ip,
            public_port=resource_pool.public_port,
            public_ip=actual_public_ip,
        )
        
        new_config = VpnConfig(
            vm_ip=vm_ip,
            server_private_key=config_data["server_private_key"],
            server_public_key=config_data["server_public_key"],
            client_configs=config_data["client_configs"],
            status=VpnStatus.INIT.value,
        )
        
        self.db.add(new_config)
        self.db.commit()
        self.db.refresh(new_config)
        
        return new_config
    
    def update_status(self, config: VpnConfig, new_status: VpnStatus) -> None:
        """Update config status"""
        config.status = new_status.value
        if new_status == VpnStatus.STARTED:
            config.started_at = datetime.utcnow()
        self.db.commit()
    
    def report_ready(self, vm_ip: str) -> VpnConfig:
        """Report VM is ready with WireGuard running"""
        config = self.get_config_by_ip(vm_ip)
        
        if not config:
            raise ValueError("记录已销毁")
        
        if config.status == VpnStatus.INIT.value:
            self.update_status(config, VpnStatus.STARTED)
        
        return config
    
    def archive_config(self, config: VpnConfig) -> VpnArchive:
        """Archive a VPN config (move to archive table)"""
        archive = VpnArchive.from_vpn_config(config)
        
        self.db.add(archive)
        self.db.delete(config)
        self.db.commit()
        
        return archive
    
    def get_server_config_for_vm(self, config: VpnConfig) -> dict[str, Any]:
        """Get server config formatted for VM"""
        vpn_subnet = self.wireguard.calculate_vpn_subnet(config.vm_ip)
        server_vpn_ip = f"{vpn_subnet}.254"
        
        client_public_keys = [c["public_key"] for c in config.client_configs]
        client_vpn_ips = [c["vpn_ip"] for c in config.client_configs]
        
        server_config = self.wireguard.generate_server_config(
            private_key=config.server_private_key,
            vpn_ip=server_vpn_ip,
            listen_port=settings.WIREGUARD_SERVER_PORT,
            client_public_keys=client_public_keys,
            client_vpn_ips=client_vpn_ips,
        )
        
        return {
            "vm_ip": config.vm_ip,
            "vpn_ip": server_vpn_ip,
            "private_key": config.server_private_key,
            "public_key": config.server_public_key,
            "listen_port": settings.WIREGUARD_SERVER_PORT,
            "config_file": server_config,
            "peers": [
                {
                    "public_key": c["public_key"],
                    "allowed_ips": f"{c['vpn_ip']}/32",
                }
                for c in config.client_configs
            ],
        }
