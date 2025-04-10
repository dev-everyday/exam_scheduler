import redis
import redis_lock
import functools
import logging
from django.conf import settings
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger(__name__)

redis_client = redis.Redis.from_url(settings.CACHES['default']['LOCATION'])

def acquire_lock(resource_key, timeout=None, blocking_timeout=None):
    lock_key = f"lock:{resource_key}"
    lock_timeout = timeout or getattr(settings, 'REDIS_LOCK_TIMEOUT', 30)
    lock_blocking_timeout = blocking_timeout or getattr(settings, 'REDIS_LOCK_BLOCKING_TIMEOUT', 10)
    
    lock = redis_lock.Lock(redis_client, lock_key, expire=lock_timeout, auto_renewal=False)
    
    try:
        acquired = lock.acquire(blocking=True, timeout=lock_blocking_timeout)
        if acquired:
            logger.debug(f"Lock acquired for {lock_key}")
            return lock
        else:
            logger.warning(f"Failed to acquire lock for {lock_key}")
            return None
    except Exception as e:
        logger.error(f"Error acquiring lock for {lock_key}: {str(e)}")
        return None

def release_lock(lock):
    if lock and hasattr(lock, 'acquired') and lock.acquired:
        try:
            lock.release()
            logger.debug(f"Lock released")
        except Exception as e:
            logger.error(f"Error releasing lock: {str(e)}")

def with_distributed_lock(resource_key_func=None, timeout=None, blocking_timeout=None):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if resource_key_func:
                resource_key = resource_key_func(*args, **kwargs)
            else:
                resource_key = func.__name__
            
            lock = acquire_lock(resource_key, timeout, blocking_timeout)
            
            if not lock:
                return Response(
                    {"error": "다른 관리자가 이 작업을 처리 중입니다. 잠시 후 다시 시도해주세요."},
                    status=status.HTTP_409_CONFLICT
                )
            
            try:
                return func(*args, **kwargs)
            finally:
                release_lock(lock)
                
        return wrapper
    return decorator 