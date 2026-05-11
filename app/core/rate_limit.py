from collections import defaultdict
from datetime import datetime, timezone
from fastapi import HTTPException, Request

# { "endpoint:user_id": [(timestamp), ...] }
_request_log: dict = defaultdict(list)

def rate_limit(max_requests: int, window_seconds: int):
    """Decorator factory cho rate limiting"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Lấy current_user từ kwargs
            current_user = kwargs.get("current_user", {})
            user_id      = current_user.get("sub", "anonymous")
            key          = f"{func.__name__}:{user_id}"
            now          = datetime.now(timezone.utc).timestamp()

            # Xóa request cũ ngoài window
            _request_log[key] = [
                t for t in _request_log[key]
                if now - t < window_seconds
            ]

            if len(_request_log[key]) >= max_requests:
                raise HTTPException(
                    429,
                    f"Rate limit: max {max_requests} requests per {window_seconds}s"
                )

            _request_log[key].append(now)
            return await func(*args, **kwargs)
        wrapper.__name__ = func.__name__
        return wrapper
    return decorator