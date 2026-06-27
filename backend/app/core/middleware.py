import time
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = logging.getLogger("app.middleware")

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log request details and execution latencies.
    """
    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.time()
        
        # Log request receipt
        logger.info(f"---> {request.method} {request.url.path}")
        
        try:
            response = await call_next(request)
            process_time = (time.time() - start_time) * 1000
            
            # Log successful or client-error responses
            logger.info(
                f"<--- {request.method} {request.url.path} | Status: {response.status_code} | Latency: {process_time:.2f}ms"
            )
            return response
            
        except Exception as e:
            process_time = (time.time() - start_time) * 1000
            logger.error(
                f"<--- FAIL {request.method} {request.url.path} | Latency: {process_time:.2f}ms | Error: {str(e)}"
            )
            raise e
