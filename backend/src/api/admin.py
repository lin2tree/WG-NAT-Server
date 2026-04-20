"""Admin API routes"""
import io
import zipfile
from datetime import datetime
from ipaddress import IPv4Address
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from ..core.config import settings
from ..core.database import get_db
from ..api.deps import get_current_user, get_current_root_user
from ..models.user import User
from ..models.vpn_config import VpnConfig, VpnStatus
from ..models.vpn_archive import VpnArchive
from ..models.resource_pool import ResourcePool
from ..models.public_ip import PublicIP
from ..services.vpn_config_service import VpnConfigService
from ..services.resource_pool_service import ResourcePoolService
from ..services.log_service import LogService

router = APIRouter()


class ImportPublicIPRequest(BaseModel):
    ip_address: str
    
    @field_validator('ip_address')
    @classmethod
    def validate_ip_address(cls, v: str) -> str:
        try:
            ip = IPv4Address(v)
        except ValueError:
            raise ValueError('无效的IP地址格式')
        
        first_octet = int(v.split('.')[0])
        
        if first_octet == 0:
            raise ValueError('0.x.x.x 是保留地址')
        if first_octet == 127:
            raise ValueError('127.x.x.x 是回环地址')
        if first_octet >= 224 and first_octet <= 239:
            raise ValueError('224.x.x.x - 239.x.x.x 是组播地址')
        if first_octet >= 240:
            raise ValueError('240.x.x.x - 255.x.x.x 是保留地址')
        if v == '255.255.255.255':
            raise ValueError('255.255.255.255 是广播地址')
        if v.startswith('169.254.'):
            raise ValueError('169.254.x.x 是链路本地地址')
        
        if first_octet == 10:
            raise ValueError('10.x.x.x 是私有地址，不能作为公网IP')
        if first_octet == 172:
            second_octet = int(v.split('.')[1])
            if 16 <= second_octet <= 31:
                raise ValueError('172.16.x.x - 172.31.x.x 是私有地址，不能作为公网IP')
        if v.startswith('192.168.'):
            raise ValueError('192.168.x.x 是私有地址，不能作为公网IP')
        
        return v
    description: str | None = None
    is_default: bool = False


class SetDefaultPublicIPRequest(BaseModel):
    ip_id: int


@router.get("/public-ips")
async def list_public_ips(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all public IP addresses"""
    public_ips = db.query(PublicIP).order_by(PublicIP.is_default.desc(), PublicIP.created_at).all()
    return {
        "success": True,
        "data": [
            {
                "id": ip.id,
                "ip_address": ip.ip_address,
                "is_default": ip.is_default,
                "description": ip.description,
                "created_at": ip.created_at.isoformat(),
            }
            for ip in public_ips
        ],
    }


@router.post("/public-ips")
async def import_public_ip(
    request: ImportPublicIPRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_root_user),
):
    """Import a public IP address (Root only)"""
    existing = db.query(PublicIP).filter(PublicIP.ip_address == request.ip_address).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该公网IP已存在",
        )
    
    if request.is_default:
        db.query(PublicIP).update({PublicIP.is_default: False})
    
    public_ip = PublicIP(
        ip_address=request.ip_address,
        is_default=request.is_default,
        description=request.description,
    )
    db.add(public_ip)
    db.commit()
    db.refresh(public_ip)
    
    return {
        "success": True,
        "message": "公网IP导入成功",
        "data": {
            "id": public_ip.id,
            "ip_address": public_ip.ip_address,
            "is_default": public_ip.is_default,
        },
    }


@router.put("/public-ips/{ip_id}/default")
async def set_default_public_ip(
    ip_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_root_user),
):
    """Set a public IP as default (Root only)"""
    public_ip = db.query(PublicIP).filter(PublicIP.id == ip_id).first()
    if not public_ip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="公网IP不存在",
        )
    
    db.query(PublicIP).update({PublicIP.is_default: False})
    public_ip.is_default = True
    db.commit()
    
    return {
        "success": True,
        "message": f"已将 {public_ip.ip_address} 设为默认公网IP",
    }


@router.delete("/public-ips/{ip_id}")
async def delete_public_ip(
    ip_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_root_user),
):
    """Delete a public IP address (Root only)"""
    public_ip = db.query(PublicIP).filter(PublicIP.id == ip_id).first()
    if not public_ip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="公网IP不存在",
        )
    
    mappings_count = db.query(ResourcePool).filter(
        ResourcePool.public_ip_id == ip_id,
        ResourcePool.deleted_at.is_(None),
    ).count()
    
    if mappings_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"该公网IP仍有 {mappings_count} 个映射关联，无法删除",
        )
    
    db.delete(public_ip)
    db.commit()
    
    return {
        "success": True,
        "message": "公网IP删除成功",
    }


@router.get("/port-range")
async def get_port_range(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get port range configuration"""
    pool_service = ResourcePoolService(db)
    port_range = pool_service.get_port_range()
    
    if not port_range:
        return {
            "success": True,
            "data": None,
            "message": "Port range not configured",
        }
    
    total_ports = port_range.end_port - port_range.start_port + 1
    allocated_ports = len(pool_service._get_allocated_ports())
    available_ports = total_ports - allocated_ports
    
    return {
        "success": True,
        "data": {
            "start_port": port_range.start_port,
            "end_port": port_range.end_port,
            "total_ports": total_ports,
            "allocated_ports": allocated_ports,
            "available_ports": available_ports,
            "created_at": port_range.created_at.isoformat(),
        },
    }


@router.post("/port-range")
async def set_port_range(
    start_port: int,
    end_port: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_root_user),
):
    """Set port range configuration (Root only)"""
    pool_service = ResourcePoolService(db)
    
    try:
        port_range = pool_service.set_port_range(start_port, end_port)
        return {
            "success": True,
            "message": "Port range updated successfully",
            "data": {
                "start_port": port_range.start_port,
                "end_port": port_range.end_port,
            },
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/resource-pool")
async def list_resource_pool(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    internal_ip: str | None = Query(None),
    public_port: str | None = Query(None),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all resource pool mappings with search and sort support"""
    pool_service = ResourcePoolService(db)
    result = pool_service.list_mappings(
        page=page,
        page_size=page_size,
        internal_ip=internal_ip,
        public_port=public_port,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    
    return {
        "success": True,
        "data": result,
    }


@router.post("/resource-pool/import")
async def import_ips(
    ip_list: list[str],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_root_user),
):
    """Import IP addresses (Root only)"""
    pool_service = ResourcePoolService(db)
    
    try:
        mappings = pool_service.import_ips(ip_list)
        return {
            "success": True,
            "message": f"Imported {len(mappings)} IP addresses",
            "data": [
                {
                    "id": m.id,
                    "internal_ip": m.internal_ip,
                    "public_port": m.public_port,
                }
                for m in mappings
            ],
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.put("/resource-pool/{mapping_id}/public-ip")
async def update_mapping_public_ip(
    mapping_id: int,
    public_ip_id: int = Query(..., description="Public IP ID to assign"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_root_user),
):
    """Update public IP for a mapping (Root only)"""
    pool_service = ResourcePoolService(db)
    
    try:
        mapping = pool_service.update_public_ip(mapping_id, public_ip_id)
        return {
            "success": True,
            "message": "公网IP更新成功",
            "data": {
                "id": mapping.id,
                "internal_ip": mapping.internal_ip,
                "public_ip_id": mapping.public_ip_id,
            },
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/resource-pool/{mapping_id}")
async def delete_mapping(
    mapping_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_root_user),
):
    """Delete IP mapping (Root only)"""
    pool_service = ResourcePoolService(db)
    
    try:
        success = pool_service.delete_mapping(mapping_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="映射不存在",
            )
        return {
            "success": True,
            "message": "删除成功",
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


class BatchDeleteRequest(BaseModel):
    ids: list[int]


@router.post("/resource-pool/batch-delete")
async def delete_mappings_batch(
    request: BatchDeleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_root_user),
):
    """Batch delete IP mappings (Root only)"""
    pool_service = ResourcePoolService(db)
    
    result = pool_service.delete_mappings_batch(request.ids)
    
    return {
        "success": True,
        "message": f"成功删除 {len(result['deleted'])} 条记录",
        "data": result,
    }


@router.get("/resource-pool/export")
async def export_mappings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export IP mappings as CSV"""
    pool_service = ResourcePoolService(db)
    csv_content = pool_service.export_mappings()
    
    return StreamingResponse(
        io.BytesIO(csv_content.encode()),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=resource_pool.csv"
        },
    )


@router.get("/configs")
async def list_configs(
    status_filter: str | None = Query(None, alias="status"),
    vm_ip: str | None = Query(None),
    public_port: str | None = Query(None),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List VPN configurations with search and sort support"""
    from sqlalchemy import func
    
    query = db.query(VpnConfig)
    
    if status_filter:
        query = query.filter(VpnConfig.status == status_filter)
    if vm_ip:
        query = query.filter(VpnConfig.vm_ip.ilike(f"%{vm_ip}%"))
    
    if sort_by == "vm_ip":
        ip_parts = func.split_part(VpnConfig.vm_ip, '.', 1).cast(sa.Integer)
        ip_parts2 = func.split_part(VpnConfig.vm_ip, '.', 2).cast(sa.Integer)
        ip_parts3 = func.split_part(VpnConfig.vm_ip, '.', 3).cast(sa.Integer)
        ip_parts4 = func.split_part(VpnConfig.vm_ip, '.', 4).cast(sa.Integer)
        
        if sort_order == "asc":
            query = query.order_by(ip_parts.asc(), ip_parts2.asc(), ip_parts3.asc(), ip_parts4.asc())
        else:
            query = query.order_by(ip_parts.desc(), ip_parts2.desc(), ip_parts3.desc(), ip_parts4.desc())
    else:
        sort_column = getattr(VpnConfig, sort_by, VpnConfig.created_at)
        if sort_order == "asc":
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())
    
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    
    total_configs = db.query(VpnConfig).count()
    init_count = db.query(VpnConfig).filter(VpnConfig.status == "init").count()
    started_count = db.query(VpnConfig).filter(VpnConfig.status == "started").count()
    
    result_items = []
    for c in items:
        resource = db.query(ResourcePool).filter(
            ResourcePool.internal_ip == c.vm_ip,
            ResourcePool.deleted_at.is_(None),
        ).first()
        
        pub_port = resource.public_port if resource else None
        
        if public_port and pub_port:
            if public_port not in str(pub_port):
                continue
        
        result_items.append({
            "id": c.id,
            "vm_ip": c.vm_ip,
            "vm_port": settings.WIREGUARD_SERVER_PORT,
            "pub_ip": settings.PUBLIC_IP,
            "pub_port": pub_port,
            "status": c.status,
            "created_at": c.created_at.isoformat(),
            "started_at": c.started_at.isoformat() if c.started_at else None,
        })
    
    return {
        "success": True,
        "data": {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": result_items,
            "stats": {
                "total": total_configs,
                "init": init_count,
                "started": started_count,
            },
        },
    }


@router.get("/configs/export")
async def export_configs(
    status_filter: str | None = Query(None, alias="status"),
    vm_ip: str | None = Query(None),
    public_port: int | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_root_user),
):
    """Export VPN configurations as CSV (Root only)"""
    query = db.query(VpnConfig)
    
    if status_filter:
        query = query.filter(VpnConfig.status == status_filter)
    if vm_ip:
        query = query.filter(VpnConfig.vm_ip.ilike(f"%{vm_ip}%"))
    
    items = query.order_by(VpnConfig.created_at.desc()).all()
    
    lines = ["VM IP,VM Port,Pub IP,Pub Port,Status,Init Time,Start Time"]
    for c in items:
        resource = db.query(ResourcePool).filter(
            ResourcePool.internal_ip == c.vm_ip,
            ResourcePool.deleted_at.is_(None),
        ).first()
        
        pub_port = resource.public_port if resource else ""
        
        if public_port is not None and pub_port != public_port:
            continue
        
        started_at = c.started_at.isoformat() if c.started_at else ""
        lines.append(f"{c.vm_ip},{settings.WIREGUARD_SERVER_PORT},{settings.PUBLIC_IP},{pub_port},{c.status},{c.created_at.isoformat()},{started_at}")
    
    csv_content = "\n".join(lines)
    csv_bytes = io.BytesIO(csv_content.encode('utf-8-sig'))
    
    return StreamingResponse(
        csv_bytes,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": "attachment; filename=vpn_configs.csv"
        },
    )


@router.get("/configs/{vm_ip}")
async def get_config_detail(
    vm_ip: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get VPN configuration details"""
    vpn_service = VpnConfigService(db)
    config = vpn_service.get_config_by_ip(vm_ip)
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration for {vm_ip} not found",
        )
    
    show_secrets = current_user.can_view_secrets()
    
    return {
        "success": True,
        "data": {
            "vm_ip": config.vm_ip,
            "status": config.status,
            "server_public_key": config.server_public_key,
            "server_private_key": config.server_private_key if show_secrets else "***",
            "created_at": config.created_at.isoformat(),
            "started_at": config.started_at.isoformat() if config.started_at else None,
            "clients": [
                {
                    "name": c["name"],
                    "vpn_ip": c["vpn_ip"],
                    "public_key": c["public_key"],
                    "private_key": c["private_key"] if show_secrets else "***",
                }
                for c in config.client_configs
            ],
        },
    }


@router.get("/configs/{vm_ip}/download/server")
async def download_server_config(
    vm_ip: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_root_user),
):
    """Download server configuration file (Root only)"""
    vpn_service = VpnConfigService(db)
    config = vpn_service.get_config_by_ip(vm_ip)
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration for {vm_ip} not found",
        )
    
    server_config = vpn_service.get_server_config_for_vm(config)
    
    return StreamingResponse(
        io.BytesIO(server_config["config_file"].encode()),
        media_type="text/plain",
        headers={
            "Content-Disposition": f"attachment; filename=wg0_{vm_ip}.conf"
        },
    )


@router.get("/configs/{vm_ip}/download/client/{client_name}")
async def download_client_config(
    vm_ip: str,
    client_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_root_user),
):
    """Download client configuration file (Root only)"""
    vpn_service = VpnConfigService(db)
    config = vpn_service.get_config_by_ip(vm_ip)
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration for {vm_ip} not found",
        )
    
    client_config = None
    for c in config.client_configs:
        if c["name"] == client_name:
            client_config = c
            break
    
    if not client_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client {client_name} not found",
        )
    
    return StreamingResponse(
        io.BytesIO(client_config["config_file"].encode()),
        media_type="text/plain",
        headers={
            "Content-Disposition": f"attachment; filename={client_name}.conf"
        },
    )


@router.get("/configs/{vm_ip}/download/clients")
async def download_all_client_configs(
    vm_ip: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_root_user),
):
    """Download all client configurations as ZIP (Root only)"""
    vpn_service = VpnConfigService(db)
    config = vpn_service.get_config_by_ip(vm_ip)
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration for {vm_ip} not found",
        )
    
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for client_config in config.client_configs:
            zipf.writestr(
                f"{client_config['name']}.conf",
                client_config["config_file"]
            )
    
    zip_buffer.seek(0)
    
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename=clients_{vm_ip}.zip"
        },
    )


@router.get("/configs/{vm_ip}/clients")
async def get_client_configs_masked(
    vm_ip: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get client configurations with masked keys"""
    vpn_service = VpnConfigService(db)
    config = vpn_service.get_config_by_ip(vm_ip)
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration for {vm_ip} not found",
        )
    
    def mask_key(key: str) -> str:
        if len(key) <= 8:
            return "****"
        return key[:4] + "****" + key[-4:]
    
    masked_configs = []
    for c in config.client_configs:
        masked_configs.append({
            "name": c["name"],
            "vpn_ip": c["vpn_ip"],
            "private_key_masked": mask_key(c["private_key"]),
            "public_key": c["public_key"],
            "config_file_masked": c["config_file"].replace(
                c["private_key"], mask_key(c["private_key"])
            ),
        })
    
    return {
        "success": True,
        "data": {
            "vm_ip": vm_ip,
            "server_public_key": config.server_public_key,
            "clients": masked_configs,
        },
    }


@router.get("/configs/{vm_ip}/history")
async def get_config_history(
    vm_ip: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get configuration history for a VM"""
    archives = db.query(VpnArchive).filter(
        VpnArchive.vm_ip == vm_ip,
    ).order_by(VpnArchive.deleted_at.desc()).all()
    
    return {
        "success": True,
        "data": [
            {
                "id": a.id,
                "vm_ip": a.vm_ip,
                "created_at": a.created_at.isoformat(),
                "deleted_at": a.deleted_at.isoformat(),
            }
            for a in archives
        ],
    }


@router.get("/logs")
async def list_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    start_time: datetime | None = Query(None),
    end_time: datetime | None = Query(None),
    source_ip: str | None = Query(None),
    request_path: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List operation logs"""
    log_service = LogService(db)
    result = log_service.list_logs(
        page=page,
        page_size=page_size,
        start_time=start_time,
        end_time=end_time,
        source_ip=source_ip,
        request_path=request_path,
    )
    
    return {
        "success": True,
        "data": result,
    }


@router.get("/archives")
async def list_archives(
    vm_ip: str | None = Query(None),
    public_port: str | None = Query(None),
    sort_by: str = Query("deleted_at"),
    sort_order: str = Query("desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List archived VPN configurations with search and sort support"""
    from sqlalchemy import func
    
    query = db.query(VpnArchive)
    
    if vm_ip:
        query = query.filter(VpnArchive.vm_ip.ilike(f"%{vm_ip}%"))
    
    if sort_by == "vm_ip":
        ip_parts = func.split_part(VpnArchive.vm_ip, '.', 1).cast(sa.Integer)
        ip_parts2 = func.split_part(VpnArchive.vm_ip, '.', 2).cast(sa.Integer)
        ip_parts3 = func.split_part(VpnArchive.vm_ip, '.', 3).cast(sa.Integer)
        ip_parts4 = func.split_part(VpnArchive.vm_ip, '.', 4).cast(sa.Integer)
        
        if sort_order == "asc":
            query = query.order_by(ip_parts.asc(), ip_parts2.asc(), ip_parts3.asc(), ip_parts4.asc())
        else:
            query = query.order_by(ip_parts.desc(), ip_parts2.desc(), ip_parts3.desc(), ip_parts4.desc())
    else:
        sort_column = getattr(VpnArchive, sort_by, VpnArchive.deleted_at)
        if sort_order == "asc":
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())
    
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    
    total_archives = db.query(VpnArchive).count()
    
    result_items = []
    for a in items:
        resource = db.query(ResourcePool).filter(
            ResourcePool.internal_ip == a.vm_ip,
        ).first()
        
        pub_port = resource.public_port if resource else None
        if public_port and pub_port:
            if public_port not in str(pub_port):
                continue
        
        result_items.append({
            "id": a.id,
            "vm_ip": a.vm_ip,
            "vm_port": settings.WIREGUARD_SERVER_PORT,
            "pub_ip": settings.PUBLIC_IP,
            "pub_port": pub_port,
            "status": a.status,
            "created_at": a.created_at.isoformat(),
            "started_at": a.started_at.isoformat() if a.started_at else None,
            "deleted_at": a.deleted_at.isoformat(),
        })
    
    return {
        "success": True,
        "data": {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": result_items,
            "stats": {
                "total": total_archives,
            },
        },
    }


@router.get("/archives/export")
async def export_archives(
    vm_ip: str | None = Query(None),
    public_port: int | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_root_user),
):
    """Export archived VPN configurations as CSV (Root only)"""
    query = db.query(VpnArchive)
    
    if vm_ip:
        query = query.filter(VpnArchive.vm_ip.ilike(f"%{vm_ip}%"))
    
    items = query.order_by(VpnArchive.deleted_at.desc()).all()
    
    lines = ["VM IP,VM Port,Pub IP,Pub Port,Status,Init Time,Start Time,Deleted Time"]
    for a in items:
        resource = db.query(ResourcePool).filter(
            ResourcePool.internal_ip == a.vm_ip,
        ).first()
        
        pub_port = resource.public_port if resource else ""
        
        if public_port is not None and pub_port != public_port:
            continue
        
        started_at = a.started_at.isoformat() if a.started_at else ""
        lines.append(f"{a.vm_ip},{settings.WIREGUARD_SERVER_PORT},{settings.PUBLIC_IP},{pub_port},{a.status},{a.created_at.isoformat()},{started_at},{a.deleted_at.isoformat()}")
    
    csv_content = "\n".join(lines)
    csv_bytes = io.BytesIO(csv_content.encode('utf-8-sig'))
    
    return StreamingResponse(
        csv_bytes,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": "attachment; filename=vpn_archives.csv"
        },
    )


@router.post("/cleanup")
async def run_cleanup(
    days: int = Query(90, ge=0, le=365),
    current_user: User = Depends(get_current_root_user),
):
    """Manually trigger cleanup of soft-deleted data (Root only)
    
    Args:
        days: Clean up data deleted more than this many days ago.
              Use 0 to clean up all soft-deleted data.
    """
    from ..tasks import cleanup_soft_deleted_data, cleanup_logs
    
    resource_result = cleanup_soft_deleted_data(days=days)
    log_result = cleanup_logs(days=days)
    
    return {
        "success": True,
        "data": {
            "resources": resource_result,
            "logs": log_result,
        },
    }
