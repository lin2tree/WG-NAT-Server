"""VM API routes"""
import time
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from ..core.config import settings
from ..core.database import get_db
from ..api.deps import verify_vm_request
from ..models.vpn_config import VpnStatus
from ..services.vpn_config_service import VpnConfigService
from ..services.log_service import LogService

router = APIRouter()


@router.get("/config")
async def get_vm_config(
    request: Request,
    source_ip: str = Depends(verify_vm_request),
    db: Session = Depends(get_db),
):
    """Get VPN configuration for VM
    
    Returns WireGuard server configuration for the VM to set up VPN.
    Idempotent - returns same config if already requested in init state.
    """
    start_time = time.time()
    vpn_service = VpnConfigService(db)
    log_service = LogService(db)
    
    try:
        config = vpn_service.get_or_create_config(
            vm_ip=source_ip,
            public_ip=settings.PUBLIC_IP,
        )
        
        server_config = vpn_service.get_server_config_for_vm(config)
        
        response_time_ms = int((time.time() - start_time) * 1000)
        log_service.create_log(
            source_ip=source_ip,
            request_path="/api/vm/config",
            request_method="GET",
            response_status=200,
            response_time_ms=response_time_ms,
        )
        
        return {
            "success": True,
            "data": {
                "vm_ip": config.vm_ip,
                "status": config.status,
                "server": server_config,
            },
        }
    
    except ValueError as e:
        response_time_ms = int((time.time() - start_time) * 1000)
        log_service.create_log(
            source_ip=source_ip,
            request_path="/api/vm/config",
            request_method="GET",
            response_status=400,
            response_time_ms=response_time_ms,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/ready")
async def report_vm_ready(
    request: Request,
    source_ip: str = Depends(verify_vm_request),
    db: Session = Depends(get_db),
):
    """Report VM is ready with WireGuard running
    
    VM calls this after successfully setting up WireGuard.
    Updates status from init to started.
    Idempotent - no error if already started.
    """
    start_time = time.time()
    vpn_service = VpnConfigService(db)
    log_service = LogService(db)
    
    try:
        config = vpn_service.report_ready(source_ip)
        
        response_time_ms = int((time.time() - start_time) * 1000)
        log_service.create_log(
            source_ip=source_ip,
            request_path="/api/vm/ready",
            request_method="POST",
            response_status=200,
            response_time_ms=response_time_ms,
        )
        
        return {
            "success": True,
            "message": f"VM {source_ip} marked as started",
            "data": {
                "vm_ip": config.vm_ip,
                "status": config.status,
                "started_at": config.started_at.isoformat() if config.started_at else None,
            },
        }
    
    except ValueError as e:
        response_time_ms = int((time.time() - start_time) * 1000)
        log_service.create_log(
            source_ip=source_ip,
            request_path="/api/vm/ready",
            request_method="POST",
            response_status=400,
            response_time_ms=response_time_ms,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
