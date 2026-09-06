"""Rate limiting middleware and abuse detection."""
import time
from collections import defaultdict

from app.core.config import settings
from app.core.exceptions import RateLimitExceededError


class RateLimiter:
    """In-memory rate limiter with per-user tracking and abuse detection."""
    
    def __init__(
        self,
        requests_per_period: int = settings.rate_limit_requests,
        period_seconds: int = settings.rate_limit_period_seconds,
    ):
        self.requests_per_period = requests_per_period
        self.period_seconds = period_seconds
        
        # Track request timestamps per user: {user_id: [timestamp, timestamp, ...]}
        self.request_history: dict[str, list[float]] = defaultdict(list)
        
        # Track blocked reasons for abuse detection: {user_id: (reason, count, last_time)}
        self.blocked_attempts: dict[str, tuple[str, int, float]] = {}
    
    def is_allowed(self, user_id: str) -> bool:
        """Check if a user is allowed to make a request."""
        now = time.time()
        cutoff = now - self.period_seconds
        
        # Clean old request history
        if user_id in self.request_history:
            self.request_history[user_id] = [
                ts for ts in self.request_history[user_id]
                if ts > cutoff
            ]
        
        # Count requests in current period
        request_count = len(self.request_history[user_id])
        
        # If under limit, allow and record
        if request_count < self.requests_per_period:
            self.request_history[user_id].append(now)
            return True
        
        # Rate limit exceeded
        return False
    
    def check_limit(self, user_id: str) -> None:
        """Check rate limit and raise RateLimitExceededError if exceeded."""
        if not self.is_allowed(user_id):
            raise RateLimitExceededError(
                f"Rate limit exceeded: {self.requests_per_period} requests "
                f"per {self.period_seconds} seconds"
            )
    
    def record_blocked_attempt(self, user_id: str, reason: str) -> None:
        """Record a blocked attempt for abuse detection.
        
        Can be used to detect repeated malicious attempts from the same user.
        """
        now = time.time()
        
        if user_id in self.blocked_attempts:
            prev_reason, count, last_time = self.blocked_attempts[user_id]
            
            # If same reason within a short window, increment counter
            if reason == prev_reason and (now - last_time) < 300:  # 5 minute window
                self.blocked_attempts[user_id] = (reason, count + 1, now)
            else:
                # Different reason or old attempt, reset
                self.blocked_attempts[user_id] = (reason, 1, now)
        else:
            self.blocked_attempts[user_id] = (reason, 1, now)
    
    def get_blocked_attempt_count(self, user_id: str, reason: str) -> int:
        """Get count of blocked attempts for a specific reason."""
        if user_id not in self.blocked_attempts:
            return 0
        
        recorded_reason, count, _ = self.blocked_attempts[user_id]
        if recorded_reason == reason:
            return count
        return 0


# Global instance
rate_limiter = RateLimiter()
