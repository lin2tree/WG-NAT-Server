"""Third-party Application API routes"""
import time
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import io

from ..core.config import settings
from ..core.database import get_db
from ..api.deps import verify_3rd_request, _is_trusted_proxy
from ..models.vpn_config import VpnConfig, VpnStatus
from ..models.vpn_archive import VpnArchive
from ..services.vpn_config_service import VpnConfigService
from ..services.log_service import LogService

router = APIRouter()


def mask_private_key(private_key: str) -> str:
    """Mask private key for display, showing only first 4 and last 4 characters"""
    if not private_key or len(private_key) < 12:
        return "****"
    return f"{private_key[:4]}****{private_key[-4:]}"


def get_client_ip(request: Request) -> str:
    """Get client IP address from request
    
    Security: Only trust X-Forwarded-For/X-Real-IP headers from trusted proxies.
    """
    client_ip = request.client.host if request.client else None
    if client_ip is None:
        return "unknown"
    
    if _is_trusted_proxy(client_ip):
        source_ip = (
            request.headers.get("x-forwarded-for", "").split(",")[0].strip()
            or request.headers.get("x-real-ip")
            or client_ip
        )
    else:
        source_ip = client_ip
    
    return source_ip


@router.get("/configs/{vm_ip}/info")
async def get_client_configs_info(
    vm_ip: str,
    request: Request,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_3rd_request),
):
    """Get client configurations info for a VM
    
    Returns all client configs overview with masked private keys.
    Only returns configs for started VMs.
    """
    start_time = time.time()
    source_ip = get_client_ip(request)
    log_service = LogService(db)
    request_path = f"/api/3rd/configs/{vm_ip}/info"
    
    try:
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
        
        response_time_ms = int((time.time() - start_time) * 1000)
        log_service.create_log(
            source_ip=source_ip,
            request_path=request_path,
            request_method="GET",
            response_status=200,
            response_time_ms=response_time_ms,
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
                        "private_key_masked": mask_private_key(c.get("private_key", "")),
                        "public_key": c["public_key"],
                    }
                    for c in config.client_configs
                ],
            },
        }
    
    except HTTPException as e:
        response_time_ms = int((time.time() - start_time) * 1000)
        log_service.create_log(
            source_ip=source_ip,
            request_path=request_path,
            request_method="GET",
            response_status=e.status_code,
            response_time_ms=response_time_ms,
            error_message=e.detail,
        )
        raise


@router.get("/configs/{vm_ip}/download")
async def download_client_configs(
    vm_ip: str,
    request: Request,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_3rd_request),
):
    """Download all client configuration files
    
    Returns all client configs in one file.
    Only returns configs for started VMs.
    """
    start_time = time.time()
    source_ip = get_client_ip(request)
    log_service = LogService(db)
    request_path = f"/api/3rd/configs/{vm_ip}/download"
    
    try:
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
        
        all_configs = []
        for c in config.client_configs:
            all_configs.append(f"# Client: {c['name']}")
            all_configs.append(c["config_file"])
            all_configs.append("")
        
        config_content = "\n".join(all_configs)
        
        response_time_ms = int((time.time() - start_time) * 1000)
        log_service.create_log(
            source_ip=source_ip,
            request_path=request_path,
            request_method="GET",
            response_status=200,
            response_time_ms=response_time_ms,
        )
        
        return StreamingResponse(
            io.BytesIO(config_content.encode()),
            media_type="text/plain",
            headers={
                "Content-Disposition": f"attachment; filename=wg.conf"
            },
        )
    
    except HTTPException as e:
        response_time_ms = int((time.time() - start_time) * 1000)
        log_service.create_log(
            source_ip=source_ip,
            request_path=request_path,
            request_method="GET",
            response_status=e.status_code,
            response_time_ms=response_time_ms,
            error_message=e.detail,
        )
        raise


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
    start_time = time.time()
    source_ip = get_client_ip(request)
    log_service = LogService(db)
    request_path = f"/api/3rd/configs/{vm_ip}/destroy"
    
    try:
        vpn_service = VpnConfigService(db)
        config = vpn_service.get_config_by_ip(vm_ip)
        
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Configuration for {vm_ip} not found",
            )
        
        archive = vpn_service.archive_config(config)
        
        response_time_ms = int((time.time() - start_time) * 1000)
        log_service.create_log(
            source_ip=source_ip,
            request_path=request_path,
            request_method="POST",
            response_status=200,
            response_time_ms=response_time_ms,
        )
        
        return {
            "success": True,
            "message": f"Configuration for {vm_ip} has been destroyed",
            "data": {
                "vm_ip": archive.vm_ip,
                "deleted_at": archive.deleted_at.isoformat(),
            },
        }
    
    except HTTPException as e:
        response_time_ms = int((time.time() - start_time) * 1000)
        log_service.create_log(
            source_ip=source_ip,
            request_path=request_path,
            request_method="POST",
            response_status=e.status_code,
            response_time_ms=response_time_ms,
            error_message=e.detail,
        )
        raise
