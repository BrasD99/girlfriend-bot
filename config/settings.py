from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    # Telegram Bot
    bot_token: str = Field(..., env="BOT_TOKEN")
    
    # Database
    database_url: str = Field(..., env="DATABASE_URL")
    
    # Gemini AI
    gemini_api_key: str = Field(..., env="GEMINI_API_KEY")
    gemini_model: str = Field("gemini-pro", env="GEMINI_MODEL")
    
    # YooKassa
    yookassa_shop_id: str = Field(..., env="YOOKASSA_SHOP_ID")
    yookassa_secret_key: str = Field(..., env="YOOKASSA_SECRET_KEY")
    
    # Redis
    redis_url: str = Field("redis://localhost:6379/0", env="REDIS_URL")
    
    # App Settings
    debug: bool = Field(False, env="DEBUG")
    trial_days: int = Field(7, env="TRIAL_DAYS")
    webhook_url: Optional[str] = Field(None, env="WEBHOOK_URL")
    webhook_path: str = Field("/webhook", env="WEBHOOK_PATH")
    bot_username: Optional[str] = Field(None, env="BOT_USERNAME")
    payment_return_url: Optional[str] = Field(None, env="PAYMENT_RETURN_URL")
    admin_username: Optional[str] = Field(None, env="ADMIN_USERNAME")
    
    # Subscription Notifications
    subscription_expiry_notification_days: int = Field(1, env="SUBSCRIPTION_EXPIRY_NOTIFICATION_DAYS")
    notification_check_interval_hours: int = Field(6, env="NOTIFICATION_CHECK_INTERVAL_HOURS")
    enable_subscription_notifications: bool = Field(True, env="ENABLE_SUBSCRIPTION_NOTIFICATIONS")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
    
    def get_payment_return_url(self) -> str:
        """Получение URL для возврата после оплаты"""
        if self.payment_return_url:
            return self.payment_return_url
        elif self.bot_username:
            return f"https://t.me/{self.bot_username}"
        else:
            return "https://t.me/"  # Fallback на главную страницу Telegram


settings = Settings()