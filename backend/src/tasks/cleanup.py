"""Scheduled tasks for cleanup"""
from datetime import datetime, timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..core.database import SessionLocal
from ..models.resource_pool import ResourcePool


def cleanup_soft_deleted_data(days: int = 90) -> dict:
    """Clean up soft-deleted data older than specified days
    
    Args:
        days: Number of days to keep soft-deleted data (default: 90)
    
    Returns:
        Dictionary with cleanup statistics
    """
    db: Session = SessionLocal()
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        result = db.query(ResourcePool).filter(
            ResourcePool.deleted_at < cutoff_date,
            ResourcePool.deleted_at.isnot(None),
        ).delete(synchronize_session=False)
        
        db.commit()
        
        return {
            "deleted_count": result,
            "cutoff_date": cutoff_date.isoformat(),
            "message": f"Cleaned up {result} records deleted before {cutoff_date.isoformat()}",
        }
    except Exception as e:
        db.rollback()
        return {
            "error": str(e),
            "deleted_count": 0,
        }
    finally:
        db.close()


def cleanup_logs(days: int = 90) -> dict:
    """Clean up logs older than specified days
    
    Args:
        days: Number of days to keep logs (default: 90)
    
    Returns:
        Dictionary with cleanup statistics
    """
    db: Session = SessionLocal()
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        result = db.execute(
            text("DELETE FROM logs WHERE created_at < :cutoff"),
            {"cutoff": cutoff_date},
        )
        
        db.commit()
        
        return {
            "deleted_count": result.rowcount,
            "cutoff_date": cutoff_date.isoformat(),
            "message": f"Cleaned up {result.rowcount} log records before {cutoff_date.isoformat()}",
        }
    except Exception as e:
        db.rollback()
        return {
            "error": str(e),
            "deleted_count": 0,
        }
    finally:
        db.close()
