"""Admin API routes"""
import io
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..core.config import settings
from ..core.database import get_db
from ..api.deps import get_current_user, get_current_root_user
from ..models.user import User
from ..models.vpn_config import VpnConfig, VpnStatus
from ..models.vpn_archive import VpnArchive
from ..services.vpn_config_service import VpnConfigService
from ..services.resource_pool_service import ResourcePoolService
from ..services.log_service import LogService

router = APIRouter()


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
    
    return {
        "success": True,
        "data": {
            "start_port": port_range.start_port,
            "end_port": port_range.end_port,
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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all resource pool mappings"""
    pool_service = ResourcePoolService(db)
    result = pool_service.list_mappings(page=page, page_size=page_size)
    
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
                detail="Mapping not found",
            )
        return {
            "success": True,
            "message": "Mapping deleted successfully",
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


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
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List VPN configurations"""
    query = db.query(VpnConfig)
    
    if status_filter:
        query = query.filter(VpnConfig.status == status_filter)
    if vm_ip:
        query = query.filter(VpnConfig.vm_ip.ilike(f"%{vm_ip}%"))
    
    total = query.count()
    items = query.order_by(VpnConfig.created_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()
    
    return {
        "success": True,
        "data": {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": [
                {
                    "id": c.id,
                    "vm_ip": c.vm_ip,
                    "status": c.status,
                    "created_at": c.created_at.isoformat(),
                    "started_at": c.started_at.isoformat() if c.started_at else None,
                }
                for c in items
            ],
        },
    }


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
