import redis.asyncio as redis
from datetime import datetime, timezone
from typing import Dict, Optional
from config.settings import settings
import logging

logger = logging.getLogger(__name__)

class RedisRateLimiter:
    """
    Redis-based rate limiter для ограничения количества сообщений от пользователей
    
    Простая логика:
    1. Каждый пользователь имеет счетчик сообщений с TTL = 60 секунд
    2. При превышении лимита пользователь банится на N секунд
    3. После истечения бана счетчик сбрасывается
    """
    
    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or settings.redis_url
        self._redis: Optional[redis.Redis] = None
        
        # Префиксы для ключей Redis
        self.MESSAGE_COUNT_KEY_PREFIX = "rate_limit:count:"
        self.BAN_KEY_PREFIX = "rate_limit:ban:"
        self.WARNING_KEY_PREFIX = "rate_limit:warning:"
    
    async def _get_redis(self) -> redis.Redis:
        """Получение подключения к Redis"""
        if self._redis is None:
            try:
                self._redis = redis.from_url(
                    self.redis_url,
                    encoding="utf-8",
                    decode_responses=True
                )
                # Проверяем подключение
                await self._redis.ping()
                logger.info("Connected to Redis for rate limiting")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                raise
        return self._redis
    
    async def close(self):
        """Закрытие подключения к Redis"""
        if self._redis:
            await self._redis.aclose()
            self._redis = None
    
    def _get_current_timestamp(self) -> int:
        """Получение текущего timestamp в секундах"""
        return int(datetime.now(timezone.utc).timestamp())
    
    async def is_user_banned(self, user_id: int) -> bool:
        """Проверка, забанен ли пользователь"""
        if not settings.enable_rate_limiting:
            return False
        
        try:
            redis_client = await self._get_redis()
            ban_key = f"{self.BAN_KEY_PREFIX}{user_id}"
            
            # Проверяем TTL ключа бана
            ttl = await redis_client.ttl(ban_key)
            return ttl > 0
            
        except Exception as e:
            logger.error(f"Error checking ban status for user {user_id}: {e}")
            return False
    
    async def get_ban_remaining_time(self, user_id: int) -> Optional[int]:
        """Получение оставшегося времени бана в секундах"""
        try:
            redis_client = await self._get_redis()
            ban_key = f"{self.BAN_KEY_PREFIX}{user_id}"
            
            ttl = await redis_client.ttl(ban_key)
            return ttl if ttl > 0 else None
            
        except Exception as e:
            logger.error(f"Error getting ban remaining time for user {user_id}: {e}")
            return None
    
    async def check_rate_limit(self, user_id: int) -> Dict[str, any]:
        """
        Проверка rate limit для пользователя
        
        Returns:
            dict: {
                'allowed': bool,  # Разрешено ли сообщение
                'remaining': int,  # Сколько сообщений осталось
                'reset_in': int,  # Через сколько секунд сбросится лимит
                'banned': bool,  # Забанен ли пользователь
                'ban_remaining': int,  # Сколько секунд осталось до разбана
                'warning': bool  # Нужно ли показать предупреждение
            }
        """
        if not settings.enable_rate_limiting:
            return {
                'allowed': True,
                'remaining': settings.rate_limit_messages_per_minute,
                'reset_in': 0,
                'banned': False,
                'ban_remaining': 0,
                'warning': False
            }
        
        try:
            redis_client = await self._get_redis()
            ban_key = f"{self.BAN_KEY_PREFIX}{user_id}"
            count_key = f"{self.MESSAGE_COUNT_KEY_PREFIX}{user_id}"
            warning_key = f"{self.WARNING_KEY_PREFIX}{user_id}"
            
            # 1. Проверяем, забанен ли пользователь
            ban_remaining = await redis_client.ttl(ban_key)
            if ban_remaining > 0:
                return {
                    'allowed': False,
                    'remaining': 0,
                    'reset_in': 0,
                    'banned': True,
                    'ban_remaining': ban_remaining,
                    'warning': False
                }
            
            # 2. Получаем текущий счетчик сообщений
            current_count = await redis_client.get(count_key)
            current_count = int(current_count) if current_count else 0
            
            # 3. Проверяем, превышен ли лимит
            if current_count >= settings.rate_limit_messages_per_minute:
                # Создаем бан и сбрасываем счетчик
                await redis_client.setex(ban_key, settings.rate_limit_ban_duration_seconds, "banned")
                await redis_client.delete(count_key)  # Сбрасываем счетчик
                
                logger.warning(f"User {user_id} rate limited: {current_count} messages, banned for {settings.rate_limit_ban_duration_seconds}s")
                
                return {
                    'allowed': False,
                    'remaining': 0,
                    'reset_in': 0,
                    'banned': True,
                    'ban_remaining': settings.rate_limit_ban_duration_seconds,
                    'warning': False
                }
            
            # 4. Лимит не превышен - вычисляем оставшиеся сообщения
            remaining = settings.rate_limit_messages_per_minute - current_count - 1  # -1 для текущего сообщения
            
            # 5. Получаем время до сброса счетчика
            reset_in = await redis_client.ttl(count_key)
            reset_in = reset_in if reset_in > 0 else 60
            
            # 6. Проверяем предупреждение
            warning = False
            if current_count >= settings.rate_limit_warning_threshold:
                warning_exists = await redis_client.exists(warning_key)
                if not warning_exists:
                    warning = True
                    await redis_client.setex(warning_key, 60, "warned")
            
            return {
                'allowed': True,
                'remaining': max(0, remaining),
                'reset_in': reset_in,
                'banned': False,
                'ban_remaining': 0,
                'warning': warning
            }
            
        except Exception as e:
            logger.error(f"Error checking rate limit for user {user_id}: {e}")
            # В случае ошибки разрешаем сообщение
            return {
                'allowed': True,
                'remaining': settings.rate_limit_messages_per_minute,
                'reset_in': 0,
                'banned': False,
                'ban_remaining': 0,
                'warning': False
            }
    
    async def record_message(self, user_id: int) -> None:
        """Записать сообщение пользователя"""
        if not settings.enable_rate_limiting:
            return
        
        try:
            redis_client = await self._get_redis()
            count_key = f"{self.MESSAGE_COUNT_KEY_PREFIX}{user_id}"
            
            # Увеличиваем счетчик на 1
            current_count = await redis_client.incr(count_key)
            
            # Если это первое сообщение, устанавливаем TTL на 60 секунд
            if current_count == 1:
                await redis_client.expire(count_key, 60)
            
            logger.debug(f"User {user_id} message recorded, count: {current_count}")
            
        except Exception as e:
            logger.error(f"Error recording message for user {user_id}: {e}")
    
    async def reset_user_limit(self, user_id: int) -> None:
        """Сброс лимита для пользователя (для админских команд)"""
        try:
            redis_client = await self._get_redis()
            
            count_key = f"{self.MESSAGE_COUNT_KEY_PREFIX}{user_id}"
            ban_key = f"{self.BAN_KEY_PREFIX}{user_id}"
            warning_key = f"{self.WARNING_KEY_PREFIX}{user_id}"
            
            # Удаляем все ключи пользователя
            await redis_client.delete(count_key, ban_key, warning_key)
            
            logger.info(f"Rate limit reset for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error resetting rate limit for user {user_id}: {e}")
    
    async def get_stats(self) -> Dict[str, any]:
        """Получение статистики rate limiter"""
        try:
            redis_client = await self._get_redis()
            
            # Получаем все ключи для подсчета статистики
            count_keys = await redis_client.keys(f"{self.MESSAGE_COUNT_KEY_PREFIX}*")
            ban_keys = await redis_client.keys(f"{self.BAN_KEY_PREFIX}*")
            warning_keys = await redis_client.keys(f"{self.WARNING_KEY_PREFIX}*")
            
            return {
                'active_users': len(count_keys),
                'banned_users': len(ban_keys),
                'warnings_sent': len(warning_keys),
                'settings': {
                    'enabled': settings.enable_rate_limiting,
                    'messages_per_minute': settings.rate_limit_messages_per_minute,
                    'ban_duration_seconds': settings.rate_limit_ban_duration_seconds,
                    'warning_threshold': settings.rate_limit_warning_threshold
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting rate limiter stats: {e}")
            return {
                'active_users': 0,
                'banned_users': 0,
                'warnings_sent': 0,
                'settings': {
                    'enabled': settings.enable_rate_limiting,
                    'messages_per_minute': settings.rate_limit_messages_per_minute,
                    'ban_duration_seconds': settings.rate_limit_ban_duration_seconds,
                    'warning_threshold': settings.rate_limit_warning_threshold
                },
                'error': str(e)
            }

# Глобальный экземпляр Redis rate limiter
redis_rate_limiter = RedisRateLimiter()