"""Simple in-memory rate limiter with configurable limits via environment variables.

Rate limit keys:
- Login/Withdraw: IP + user/email
- Webhook: provider + IP
"""

import os
import time
from collections import defaultdict
from typing import Dict, Tuple, Optional
import threading


class RateLimitExceeded(Exception):
    """Rate limit exceeded exception."""
    def __init__(self, limit: int, window_seconds: int, retry_after: int):
        self.limit = limit
        self.window_seconds = window_seconds
        self.retry_after = retry_after
        super().__init__(
            f"Rate limit exceeded: {limit} requests per {window_seconds}s. "
            f"Retry after {retry_after}s"
        )


class RateLimiter:
    """Thread-safe in-memory rate limiter using sliding window."""
    
    def __init__(self):
        # {key: [(timestamp, count), ...]}
        self._buckets: Dict[str, list] = defaultdict(list)
        self._lock = threading.Lock()
        
        # Load limits from environment
        self.limits = {
            "login": int(os.environ.get("RATE_LIMIT_LOGIN_PER_MIN", "10")),
            "withdraw": int(os.environ.get("RATE_LIMIT_WITHDRAW_PER_MIN", "5")),
            "webhook": int(os.environ.get("RATE_LIMIT_WEBHOOK_PER_MIN", "100")),
        }
        self.window_seconds = 60  # 1 minute window
    
    def _cleanup_old_entries(self, key: str, current_time: float):
        """Remove entries older than the window."""
        cutoff = current_time - self.window_seconds
        self._buckets[key] = [
            (ts, count) for ts, count in self._buckets[key]
            if ts > cutoff
        ]
    
    def _get_count(self, key: str) -> int:
        """Get current request count for key."""
        return sum(count for _, count in self._buckets[key])
    
    def check_rate_limit(
        self,
        limit_type: str,
        ip: str,
        identifier: Optional[str] = None,
    ) -> Tuple[bool, int]:
        """Check if request is within rate limit.
        
        Args:
            limit_type: Type of limit (login, withdraw, webhook)
            ip: Client IP address
            identifier: Additional identifier (email, provider, etc.)
        
        Returns:
            Tuple of (is_allowed, remaining_requests)
        
        Raises:
            RateLimitExceeded: If rate limit is exceeded
        """
        limit = self.limits.get(limit_type, 10)
        key = f"{limit_type}:{ip}"
        if identifier:
            key = f"{key}:{identifier}"
        
        current_time = time.time()
        
        with self._lock:
            self._cleanup_old_entries(key, current_time)
            current_count = self._get_count(key)
            
            if current_count >= limit:
                # Calculate retry-after
                oldest_entry = min(self._buckets[key], key=lambda x: x[0])
                retry_after = int(self.window_seconds - (current_time - oldest_entry[0])) + 1
                raise RateLimitExceeded(limit, self.window_seconds, max(1, retry_after))
            
            # Add new entry
            self._buckets[key].append((current_time, 1))
            remaining = limit - current_count - 1
            
            return True, remaining
    
    def get_client_ip(self, request) -> str:
        """Extract client IP from request, handling proxies."""
        # Check X-Forwarded-For header (common with reverse proxies)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # Take the first IP (client IP)
            return forwarded.split(",")[0].strip()
        
        # Check X-Real-IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fall back to direct client
        if request.client:
            return request.client.host
        
        return "unknown"


# Global rate limiter instance
rate_limiter = RateLimiter()
