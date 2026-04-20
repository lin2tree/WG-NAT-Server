"""Frontend Application API routes"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import io

from ..core.config import settings
from ..core.database import get_db
from ..api.deps import verify_3rd_request
from ..models.vpn_config import VpnConfig, VpnStatus
from ..models.vpn_archive import VpnArchive
from ..services.vpn_config_service import VpnConfigService
from ..services.log_service import LogService

router = APIRouter()


@router.get("/configs/{vm_ip}")
async def get_client_configs(
    vm_ip: str,
    request: Request,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_3rd_request),
):
    """Get client configurations for a VM
    
    Returns all client configs for users to download.
    Only returns configs for started VMs.
    """
    vpn_service = VpnConfigService(db)
    config = vpn_service.get_config_by_ip(vm_ip)
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration for {vm_ip} not found",
        )
    
    if config.status != VpnStatus.STARTED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Configuration for {vm_ip} is not started",
        )
    
    return {
        "success": True,
        "data": {
            "vm_ip": config.vm_ip,
            "status": config.status,
            "server_public_key": config.server_public_key,
            "clients": [
                {
                    "name": c["name"],
                    "vpn_ip": c["vpn_ip"],
                    "public_key": c["public_key"],
                }
                for c in config.client_configs
            ],
        },
    }


@router.post("/configs/{vm_ip}/destroy")
async def destroy_config(
    vm_ip: str,
    request: Request,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_3rd_request),
):
    """Destroy VPN configuration for a VM
    
    Moves config to archive table. VM should stop WireGuard first.
    """
    vpn_service = VpnConfigService(db)
    config = vpn_service.get_config_by_ip(vm_ip)
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration for {vm_ip} not found",
        )
    
    archive = vpn_service.archive_config(config)
    
    return {
        "success": True,
        "message": f"Configuration for {vm_ip} has been destroyed",
        "data": {
            "vm_ip": archive.vm_ip,
            "deleted_at": archive.deleted_at.isoformat(),
        },
    }


@router.get("/configs/{vm_ip}/download/{client_name}")
async def download_client_config(
    vm_ip: str,
    client_name: str,
    request: Request,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_3rd_request),
):
    """Download a specific client configuration file"""
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
    
    config_content = client_config["config_file"]
    
    return StreamingResponse(
        io.BytesIO(config_content.encode()),
        media_type="text/plain",
        headers={
            "Content-Disposition": f"attachment; filename={client_name}.conf"
        },
    )
