import re
import time
import logging
from collections import defaultdict
from fastapi import Request, status
from app.core.exceptions import AppException

logger = logging.getLogger("app.core.guards")

# --- 1. PROMPT INJECTION PROTECTION ---
INJECTION_PATTERNS = [
    r"ignore\s+previous\s+instructions",
    r"ignore\s+above\s+instructions",
    r"system\s+override",
    r"you\s+are\s+now",
    r"new\s+system\s+prompt",
    r"disregard\s+all\s+prior",
    r"bypass\s+restrictions",
    r"developer\s+mode",
    r"ignore\s+rules"
]

def sanitize_and_guard_prompt(text: str) -> str:
    """
    Validates input strings for potential LLM prompt injection attempts.
    Raises an AppException if matches are identified.
    """
    if not text:
        return text
        
    normalized = text.lower()
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, normalized):
            logger.warning(f"Malicious prompt injection attempt flagged: pattern '{pattern}' matched.")
            raise AppException(
                code="SECURITY_VIOLATION",
                message="Input text contains blocked phrases. Request rejected for system safety.",
                status_code=status.HTTP_400_BAD_REQUEST
            )
    return text


# --- 2. IN-MEMORY RATE LIMITING ---
class TokenBucketLimiter:
    def __init__(self, limit: int = 120, window: int = 60):
        """
        Token bucket IP-based rate limiter.
        Default: 120 requests per 60 seconds (window) per IP.
        """
        self.limit = limit
        self.window = window
        self.history = defaultdict(list)

    def check_rate_limit(self, ip: str):
        now = time.time()
        # Prune older requests outside the time window
        self.history[ip] = [t for t in self.history[ip] if now - t < self.window]
        
        if len(self.history[ip]) >= self.limit:
            logger.warning(f"Rate limit triggered for IP: {ip}")
            raise AppException(
                code="RATE_LIMIT_EXCEEDED",
                message="Too many requests. Please slow down and try again later.",
                status_code=status.HTTP_429_TOO_MANY_REQUESTS
            )
        self.history[ip].append(now)

# Global rate limiter instance
global_limiter = TokenBucketLimiter(limit=120, window=60)

def rate_limit_guard(request: Request):
    """
    Dependency injection handler to enforce rate limits per request client IP.
    """
    ip = request.client.host if request.client else "unknown"
    global_limiter.check_rate_limit(ip)
