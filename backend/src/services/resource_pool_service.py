"""Resource pool service"""
import random
import re
from datetime import datetime
from ipaddress import IPv4Address, IPv4Network
from typing import Any

import sqlalchemy as sa
from sqlalchemy.orm import Session

from ..models.port_range import PortRange
from ..models.resource_pool import ResourcePool
from ..models.vpn_config import VpnConfig
from ..models.public_ip import PublicIP


class ResourcePoolService:
    """Service for managing resource pool"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_default_public_ip(self) -> PublicIP | None:
        """Get default public IP"""
        return self.db.query(PublicIP).filter(PublicIP.is_default == True).first()
    
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
    
    def _get_existing_b_class(self) -> str | None:
        """Get B-class address of existing IPs in resource pool"""
        existing = self.db.query(ResourcePool).filter(
            ResourcePool.deleted_at.is_(None),
        ).first()
        
        if not existing:
            return None
        
        ip = IPv4Address(existing.internal_ip)
        return f"{ip.packed[0]}.{ip.packed[1]}"
    
    def _validate_b_class_address(self, ip_list: list[str]) -> tuple[bool, str]:
        """Validate that all IPs have same B-class address (first two octets)
        
        Returns:
            (is_valid, error_message)
        """
        if len(ip_list) == 0:
            return True, ""
        
        first_ip = IPv4Address(ip_list[0])
        first_b_class = f"{first_ip.packed[0]}.{first_ip.packed[1]}"
        
        for ip_str in ip_list[1:]:
            ip = IPv4Address(ip_str)
            b_class = f"{ip.packed[0]}.{ip.packed[1]}"
            if b_class != first_b_class:
                return False, f"导入的IP不在同一个B类地址段: {ip_str} 与 {ip_list[0]} 不一致"
        
        existing_b_class = self._get_existing_b_class()
        if existing_b_class and existing_b_class != first_b_class:
            return False, f"导入的IP与已存在的IP不在同一个B类地址段: 导入的是 {first_b_class}.x.x，已存在的是 {existing_b_class}.x.x"
        
        return True, ""
    
    def _parse_ip_input(self, input_str: str) -> list[str]:
        """Parse IP input in various formats
        
        Supported formats:
        1. Single IP: 192.168.1.100
        2. IP range: 192.168.1.100-192.168.1.110
        3. CIDR notation: 192.168.1.0/24
        """
        input_str = input_str.strip()
        ips = []
        
        if '/' in input_str:
            try:
                network = IPv4Network(input_str, strict=False)
                ips = [str(ip) for ip in network.hosts()]
            except ValueError:
                raise ValueError(f"无效的 CIDR 格式: {input_str}")
        elif '-' in input_str:
            parts = input_str.split('-')
            if len(parts) != 2:
                raise ValueError(f"无效的 IP 范围格式: {input_str}")
            
            try:
                start_ip = IPv4Address(parts[0].strip())
                end_ip = IPv4Address(parts[1].strip())
                
                if int(end_ip) < int(start_ip):
                    raise ValueError(f"结束 IP 不能小于起始 IP: {input_str}")
                
                current = int(start_ip)
                end = int(end_ip)
                while current <= end:
                    ips.append(str(IPv4Address(current)))
                    current += 1
            except ValueError as e:
                raise ValueError(f"无效的 IP 地址: {input_str}")
        else:
            try:
                IPv4Address(input_str)
                ips = [input_str]
            except ValueError:
                raise ValueError(f"无效的 IP 地址: {input_str}")
        
        return ips
    
    def import_ips(self, input_list: list[str]) -> list[ResourcePool]:
        """Import IP addresses and allocate ports
        
        Supports multiple input formats:
        1. Single IP: 192.168.1.100
        2. IP range: 192.168.1.100-192.168.1.110
        3. CIDR notation: 192.168.1.0/24
        """
        all_ips = []
        for input_str in input_list:
            ips = self._parse_ip_input(input_str)
            all_ips.extend(ips)
        
        all_ips = list(set(all_ips))
        
        is_valid, error_msg = self._validate_b_class_address(all_ips)
        if not is_valid:
            raise ValueError(error_msg)
        
        port_range = self.get_port_range()
        if not port_range:
            raise ValueError("端口范围未配置")
        
        default_public_ip = self.get_default_public_ip()
        if not default_public_ip:
            raise ValueError("未配置默认公网IP，请先导入公网IP")
        
        db_allocated = self._get_allocated_ports()
        batch_allocated = set()
        
        available_ports = list(set(range(port_range.start_port, port_range.end_port + 1)) - db_allocated)
        
        if len(available_ports) < len(all_ips):
            raise ValueError(f"可用端口不足，需要 {len(all_ips)} 个，仅有 {len(available_ports)} 个可用")
        
        random.shuffle(available_ports)
        
        mappings = []
        port_index = 0
        for ip in all_ips:
            existing = self.db.query(ResourcePool).filter(
                ResourcePool.internal_ip == ip,
            ).first()
            
            if existing:
                continue
            
            port = available_ports[port_index]
            port_index += 1
            
            mapping = ResourcePool(
                internal_ip=ip,
                public_ip_id=default_public_ip.id,
                public_port=port,
            )
            self.db.add(mapping)
            mappings.append(mapping)
        
        self.db.commit()
        return mappings
    
    def update_public_ip(self, mapping_id: int, public_ip_id: int) -> ResourcePool:
        """Update public IP for a mapping"""
        mapping = self.db.query(ResourcePool).filter(
            ResourcePool.id == mapping_id,
            ResourcePool.deleted_at.is_(None),
        ).first()
        
        if not mapping:
            raise ValueError("映射不存在")
        
        public_ip = self.db.query(PublicIP).filter(PublicIP.id == public_ip_id).first()
        if not public_ip:
            raise ValueError("公网IP不存在")
        
        mapping.public_ip_id = public_ip_id
        mapping.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(mapping)
        return mapping
    
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
    
    def delete_mappings_batch(self, mapping_ids: list[int]) -> dict:
        """Delete multiple IP mappings (soft delete)"""
        deleted = []
        failed = []
        
        for mapping_id in mapping_ids:
            mapping = self.db.query(ResourcePool).filter(
                ResourcePool.id == mapping_id,
            ).first()
            
            if not mapping:
                failed.append({"id": mapping_id, "reason": "映射不存在"})
                continue
            
            active_config = self.db.query(VpnConfig).filter(
                VpnConfig.vm_ip == mapping.internal_ip,
            ).first()
            
            if active_config:
                failed.append({"id": mapping_id, "ip": mapping.internal_ip, "reason": "存在活跃配置"})
                continue
            
            mapping.deleted_at = datetime.utcnow()
            deleted.append({"id": mapping_id, "ip": mapping.internal_ip})
        
        self.db.commit()
        return {"deleted": deleted, "failed": failed}
    
    def list_mappings(
        self,
        page: int = 1,
        page_size: int = 20,
        internal_ip: str | None = None,
        public_port: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> dict[str, Any]:
        """List all IP mappings with search and sort support"""
        query = self.db.query(ResourcePool).filter(
            ResourcePool.deleted_at.is_(None),
        )
        
        if internal_ip:
            query = query.filter(ResourcePool.internal_ip.ilike(f"%{internal_ip}%"))
        
        if public_port:
            query = query.filter(ResourcePool.public_port.cast(sa.String).like(f"%{public_port}%"))
        
        if sort_by == "internal_ip":
            from sqlalchemy import func
            ip_parts = func.split_part(ResourcePool.internal_ip, '.', 1).cast(sa.Integer)
            ip_parts2 = func.split_part(ResourcePool.internal_ip, '.', 2).cast(sa.Integer)
            ip_parts3 = func.split_part(ResourcePool.internal_ip, '.', 3).cast(sa.Integer)
            ip_parts4 = func.split_part(ResourcePool.internal_ip, '.', 4).cast(sa.Integer)
            
            if sort_order == "asc":
                query = query.order_by(ip_parts.asc(), ip_parts2.asc(), ip_parts3.asc(), ip_parts4.asc())
            else:
                query = query.order_by(ip_parts.desc(), ip_parts2.desc(), ip_parts3.desc(), ip_parts4.desc())
        else:
            sort_column = getattr(ResourcePool, sort_by, ResourcePool.created_at)
            if sort_order == "asc":
                query = query.order_by(sort_column.asc())
            else:
                query = query.order_by(sort_column.desc())
        
        total = query.count()
        items = query.offset((page - 1) * page_size).limit(page_size).all()
        
        for item in items:
            active_config = self.db.query(VpnConfig).filter(
                VpnConfig.vm_ip == item.internal_ip,
            ).first()
            item.has_config = active_config is not None
            
            if item.public_ip:
                item.public_ip_address = item.public_ip.ip_address
            else:
                item.public_ip_address = None
        
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
        
        lines = ["内网IP,公网IP,公网端口"]
        for m in mappings:
            pub_ip = m.public_ip.ip_address if m.public_ip else ""
            lines.append(f"{m.internal_ip},{pub_ip},{m.public_port}")
        
        return "\n".join(lines)
