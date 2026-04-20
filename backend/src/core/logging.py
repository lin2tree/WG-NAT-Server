"""Logging configuration and middleware"""
import logging
import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from .config import settings


def setup_logging() -> None:
    """Setup application logging"""
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging all HTTP requests"""
    
    async def dispatch(
        self, 
        request: Request, 
        call_next: Callable
    ) -> Response:
        start_time = time.time()
        
        response = await call_next(request)
        
        process_time = int((time.time() - start_time) * 1000)
        
        logging.info(
            f"{request.method} {request.url.path} - "
            f"Status: {response.status_code} - "
            f"Time: {process_time}ms - "
            f"IP: {request.client.host if request.client else 'unknown'}"
        )
        
        response.headers["X-Process-Time"] = str(process_time)
        
        return response
