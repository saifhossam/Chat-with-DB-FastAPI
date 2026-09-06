"""Streaming response throttler to control chunk delivery rate."""
import asyncio

from app.core.config import settings


class StreamThrottler:
    """Controls the rate at which streaming chunks are sent to the client.
    
    Prevents overwhelming clients and helps manage resource usage.
    """
    
    def __init__(self, throttle_seconds: float | None = None):
        self.throttle_seconds = throttle_seconds or settings.stream_throttle_seconds
    
    async def throttle(self) -> None:
        """Sleep for the configured throttle duration."""
        if self.throttle_seconds > 0:
            await asyncio.sleep(self.throttle_seconds)


# Default instance
stream_throttler = StreamThrottler()
