import redis.asyncio as redis
from datetime import datetime, timezone
from typing import Dict, Optional
from config.settings import settings
import logging

logger = logging.getLogger(__name__)

class RedisRateLimiter:
    """
    Redis-based rate limiter для ограничения количества сообщений от пользователей
    """
    
    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or settings.redis_url
        self._redis: Optional[redis.Redis] = None
        
        # Префиксы для ключей Redis
        self.MESSAGE_KEY_PREFIX = "rate_limit:messages:"
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
            await self._redis.close()
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
            
            # Проверяем, есть ли бан и не истек ли он
            ban_until = await redis_client.get(ban_key)
            if ban_until is None:
                return False
            
            current_time = self._get_current_timestamp()
            ban_until_timestamp = int(ban_until)
            
            if current_time >= ban_until_timestamp:
                # Бан истек, удаляем ключ
                await redis_client.delete(ban_key)
                return False
            
            return True
        except Exception as e:
            logger.error(f"Error checking ban status for user {user_id}: {e}")
            return False
    
    async def get_ban_remaining_time(self, user_id: int) -> Optional[int]:
        """Получение оставшегося времени бана в секундах"""
        try:
            redis_client = await self._get_redis()
            ban_key = f"{self.BAN_KEY_PREFIX}{user_id}"
            
            ban_until = await redis_client.get(ban_key)
            if ban_until is None:
                return None
            
            current_time = self._get_current_timestamp()
            ban_until_timestamp = int(ban_until)
            
            if current_time >= ban_until_timestamp:
                await redis_client.delete(ban_key)
                return None
            
            return ban_until_timestamp - current_time
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
            # Проверяем, не забанен ли пользователь
            if await self.is_user_banned(user_id):
                ban_remaining = await self.get_ban_remaining_time(user_id)
                return {
                    'allowed': False,
                    'remaining': 0,
                    'reset_in': 0,
                    'banned': True,
                    'ban_remaining': ban_remaining or 0,
                    'warning': False
                }
            
            redis_client = await self._get_redis()
            message_key = f"{self.MESSAGE_KEY_PREFIX}{user_id}"
            warning_key = f"{self.WARNING_KEY_PREFIX}{user_id}"
            
            current_time = self._get_current_timestamp()
            window_start = current_time - 60  # Окно в 60 секунд
            
            # Удаляем старые записи (старше 1 минуты)
            await redis_client.zremrangebyscore(message_key, 0, window_start)
            
            # Получаем количество сообщений за последнюю минуту
            current_messages = await redis_client.zcard(message_key)
            remaining = max(0, settings.rate_limit_messages_per_minute - current_messages)
            
            # Вычисляем время до сброса лимита
            oldest_messages = await redis_client.zrange(message_key, 0, 0, withscores=True)
            if oldest_messages:
                oldest_timestamp = int(oldest_messages[0][1])
                reset_in = max(0, oldest_timestamp + 60 - current_time)
            else:
                reset_in = 0
            
            # Проверяем, нужно ли показать предупреждение
            warning = False
            if (current_messages >= settings.rate_limit_warning_threshold):
                warning_sent = await redis_client.get(warning_key)
                if warning_sent is None:
                    warning = True
                    # Устанавливаем флаг предупреждения на 60 секунд
                    await redis_client.setex(warning_key, 60, "1")
            
            # Проверяем, превышен ли лимит
            if current_messages >= settings.rate_limit_messages_per_minute:
                # Баним пользователя
                ban_key = f"{self.BAN_KEY_PREFIX}{user_id}"
                ban_until = current_time + settings.rate_limit_ban_duration_seconds
                await redis_client.setex(ban_key, settings.rate_limit_ban_duration_seconds, str(ban_until))
                
                logger.warning(f"User {user_id} rate limited: {current_messages} messages in last minute")
                
                return {
                    'allowed': False,
                    'remaining': 0,
                    'reset_in': reset_in,
                    'banned': True,
                    'ban_remaining': settings.rate_limit_ban_duration_seconds,
                    'warning': False
                }
            
            return {
                'allowed': True,
                'remaining': remaining,
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
            message_key = f"{self.MESSAGE_KEY_PREFIX}{user_id}"
            
            current_time = self._get_current_timestamp()
            
            # Добавляем текущее сообщение в sorted set с timestamp как score
            await redis_client.zadd(message_key, {str(current_time): current_time})
            
            # Устанавливаем TTL для ключа (70 секунд, чтобы быть уверенными)
            await redis_client.expire(message_key, 70)
            
        except Exception as e:
            logger.error(f"Error recording message for user {user_id}: {e}")
    
    async def reset_user_limit(self, user_id: int) -> None:
        """Сброс лимита для пользователя (для админских команд)"""
        try:
            redis_client = await self._get_redis()
            
            message_key = f"{self.MESSAGE_KEY_PREFIX}{user_id}"
            ban_key = f"{self.BAN_KEY_PREFIX}{user_id}"
            warning_key = f"{self.WARNING_KEY_PREFIX}{user_id}"
            
            # Удаляем все ключи пользователя
            await redis_client.delete(message_key, ban_key, warning_key)
            
            logger.info(f"Rate limit reset for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error resetting rate limit for user {user_id}: {e}")
    
    async def get_stats(self) -> Dict[str, any]:
        """Получение статистики rate limiter"""
        try:
            redis_client = await self._get_redis()
            
            # Получаем все ключи для подсчета статистики
            message_keys = await redis_client.keys(f"{self.MESSAGE_KEY_PREFIX}*")
            ban_keys = await redis_client.keys(f"{self.BAN_KEY_PREFIX}*")
            warning_keys = await redis_client.keys(f"{self.WARNING_KEY_PREFIX}*")
            
            return {
                'active_users': len(message_keys),
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