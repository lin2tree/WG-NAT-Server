"""Resource pool service"""
import random
from ipaddress import IPv4Address
from typing import Any

from sqlalchemy.orm import Session

from ..models.port_range import PortRange
from ..models.resource_pool import ResourcePool
from ..models.vpn_config import VpnConfig


class ResourcePoolService:
    """Service for managing resource pool"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_port_range(self) -> PortRange | None:
        """Get current port range configuration"""
        return self.db.query(PortRange).first()
    
    def set_port_range(self, start_port: int, end_port: int) -> PortRange:
        """Set port range configuration"""
        existing = self.get_port_range()
        
        if existing:
            allocated_ports = self._get_allocated_ports()
            for port in allocated_ports:
                if not (start_port <= port <= end_port):
                    raise ValueError(
                        f"Port {port} is already allocated but outside new range"
                    )
            existing.start_port = start_port
            existing.end_port = end_port
            self.db.commit()
            return existing
        
        new_range = PortRange(start_port=start_port, end_port=end_port)
        self.db.add(new_range)
        self.db.commit()
        return new_range
    
    def _get_allocated_ports(self) -> set[int]:
        """Get all allocated ports"""
        mappings = self.db.query(ResourcePool).filter(
            ResourcePool.deleted_at.is_(None),
        ).all()
        return {m.public_port for m in mappings}
    
    def _allocate_port(self) -> int:
        """Allocate an available port from the range"""
        port_range = self.get_port_range()
        if not port_range:
            raise ValueError("端口范围未配置")
        
        allocated = self._get_allocated_ports()
        available = set(range(port_range.start_port, port_range.end_port + 1)) - allocated
        
        if not available:
            raise ValueError("端口范围已用尽，请先扩充端口范围")
        
        return random.choice(list(available))
    
    def _validate_b_class_address(self, ip_list: list[str]) -> bool:
        """Validate that all IPs have same B-class address (first two octets)"""
        if len(ip_list) <= 1:
            return True
        
        existing_mappings = self.db.query(ResourcePool).filter(
            ResourcePool.deleted_at.is_(None),
        ).count()
        
        if existing_mappings == 0:
            return True
        
        first_ip = IPv4Address(ip_list[0])
        first_b_class = f"{first_ip.packed[0]}.{first_ip.packed[1]}"
        
        for ip_str in ip_list[1:]:
            ip = IPv4Address(ip_str)
            b_class = f"{ip.packed[0]}.{ip.packed[1]}"
            if b_class != first_b_class:
                return False
        
        return True
    
    def import_ips(self, ip_list: list[str]) -> list[ResourcePool]:
        """Import IP addresses and allocate ports"""
        if not self._validate_b_class_address(ip_list):
            raise ValueError("IP段B类地址不一致")
        
        mappings = []
        for ip in ip_list:
            existing = self.db.query(ResourcePool).filter(
                ResourcePool.internal_ip == ip,
            ).first()
            
            if existing:
                continue
            
            port = self._allocate_port()
            mapping = ResourcePool(
                internal_ip=ip,
                public_port=port,
            )
            self.db.add(mapping)
            mappings.append(mapping)
        
        self.db.commit()
        return mappings
    
    def delete_mapping(self, mapping_id: int) -> bool:
        """Delete an IP mapping (soft delete)"""
        mapping = self.db.query(ResourcePool).filter(
            ResourcePool.id == mapping_id,
        ).first()
        
        if not mapping:
            return False
        
        active_config = self.db.query(VpnConfig).filter(
            VpnConfig.vm_ip == mapping.internal_ip,
        ).first()
        
        if active_config:
            raise ValueError("该IP存在活跃配置，请先销毁配置")
        
        mapping.deleted_at = datetime.utcnow()
        self.db.commit()
        return True
    
    def list_mappings(
        self,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """List all IP mappings"""
        query = self.db.query(ResourcePool).filter(
            ResourcePool.deleted_at.is_(None),
        )
        
        total = query.count()
        items = query.offset((page - 1) * page_size).limit(page_size).all()
        
        for item in items:
            active_config = self.db.query(VpnConfig).filter(
                VpnConfig.vm_ip == item.internal_ip,
            ).first()
            item.has_config = active_config is not None
        
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": items,
        }
    
    def export_mappings(self) -> str:
        """Export mappings as CSV"""
        mappings = self.db.query(ResourcePool).filter(
            ResourcePool.deleted_at.is_(None),
        ).all()
        
        lines = ["内网IP,公网端口"]
        for m in mappings:
            lines.append(f"{m.internal_ip},{m.public_port}")
        
        return "\n".join(lines)


from datetime import datetime
