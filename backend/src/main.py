"""FastAPI application entry point"""
import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import settings
from .core.logging import setup_logging, RequestLoggingMiddleware
from .api import vm, third_party, admin, auth
from .tasks import cleanup_soft_deleted_data, cleanup_logs

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def run_cleanup():
    """Run cleanup tasks"""
    try:
        result = cleanup_soft_deleted_data(days=90)
        logger.info(f"Cleanup completed: {result}")
        
        log_result = cleanup_logs(days=90)
        logger.info(f"Log cleanup completed: {log_result}")
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    
    scheduler.add_job(
        run_cleanup,
        CronTrigger(hour=3, minute=0),
        id="cleanup_job",
        name="Cleanup soft-deleted data and logs",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started - cleanup job scheduled at 03:00 daily")
    
    yield
    
    scheduler.shutdown()
    logger.info("Scheduler shutdown")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="WireGuard VPN Manager Service API",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RequestLoggingMiddleware)

app.include_router(vm.router, prefix="/api/vm", tags=["VM API"])
app.include_router(third_party.router, prefix="/api/3rd", tags=["3rd Party API"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin API"])
app.include_router(auth.router, prefix="/api/auth", tags=["Auth API"])


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": settings.APP_VERSION}


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
    }
