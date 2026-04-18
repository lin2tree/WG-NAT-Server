"""Log service for operation logging"""
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from ..models.operation_log import OperationLog


class LogService:
    """Service for managing operation logs"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_log(
        self,
        source_ip: str,
        request_path: str,
        request_method: str,
        response_status: int,
        response_time_ms: int,
        request_params: dict[str, Any] | None = None,
    ) -> OperationLog:
        """Create a new operation log entry"""
        log = OperationLog.create(
            source_ip=source_ip,
            request_path=request_path,
            request_method=request_method,
            response_status=response_status,
            response_time_ms=response_time_ms,
            request_params=request_params,
        )
        self.db.add(log)
        self.db.commit()
        return log
    
    def list_logs(
        self,
        page: int = 1,
        page_size: int = 50,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        source_ip: str | None = None,
        request_path: str | None = None,
    ) -> dict[str, Any]:
        """List operation logs with filters"""
        query = self.db.query(OperationLog)
        
        if start_time:
            query = query.filter(OperationLog.request_time >= start_time)
        if end_time:
            query = query.filter(OperationLog.request_time <= end_time)
        if source_ip:
            query = query.filter(OperationLog.source_ip == source_ip)
        if request_path:
            query = query.filter(OperationLog.request_path.ilike(f"%{request_path}%"))
        
        total = query.count()
        items = query.order_by(
            OperationLog.request_time.desc()
        ).offset((page - 1) * page_size).limit(page_size).all()
        
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": items,
        }
    
    def cleanup_old_logs(self, retention_days: int = 90) -> int:
        """Delete logs older than retention period"""
        cutoff = datetime.utcnow() - timedelta(days=retention_days)
        deleted = self.db.query(OperationLog).filter(
            OperationLog.request_time < cutoff,
        ).delete()
        self.db.commit()
        return deleted
