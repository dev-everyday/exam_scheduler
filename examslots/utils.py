from django.conf import settings
from django_redis import get_redis_connection
import redis_lock
from functools import wraps
from contextlib import contextmanager

@contextmanager
def distributed_lock(key, blocking_timeout=None, timeout=None):
    if blocking_timeout is None:
        blocking_timeout = getattr(settings, 'REDIS_LOCK_BLOCKING_TIMEOUT', 10)
    if timeout is None:
        timeout = getattr(settings, 'REDIS_LOCK_TIMEOUT', 30)

    redis_client = get_redis_connection()
    lock = redis_lock.Lock(redis_client, key, expire=timeout)
    
    try:
        acquired = lock.acquire(blocking=blocking_timeout > 0, timeout=blocking_timeout)
        yield acquired
    finally:
        if acquired:
            try:
                lock.release()
            except redis_lock.NotAcquired:
                pass

def with_distributed_lock(key_prefix, blocking_timeout=None, timeout=None):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = f"{key_prefix}:{func.__name__}:{':'.join(str(arg) for arg in args)}"
            
            with distributed_lock(key, blocking_timeout, timeout) as acquired:
                if not acquired:
                    raise redis_lock.NotAcquired("락을 획득할 수 없습니다.")
                return func(*args, **kwargs)
        return wrapper
    return decorator 