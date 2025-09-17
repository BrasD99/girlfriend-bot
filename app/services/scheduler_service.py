from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from app.services.notification_service import NotificationService
from config.settings import settings
import logging

logger = logging.getLogger(__name__)

class SchedulerService:
    def __init__(self, bot):
        self.bot = bot
        self.scheduler = AsyncIOScheduler()
        self._setup_jobs()
    
    def _setup_jobs(self):
        """Настройка периодических задач"""
        if not settings.enable_subscription_notifications:
            logger.info("Subscription notifications disabled, skipping scheduler setup")
            return
        
        # Добавляем задачу проверки уведомлений
        self.scheduler.add_job(
            func=self._check_notifications,
            trigger=IntervalTrigger(hours=settings.notification_check_interval_hours),
            id='subscription_notifications',
            name='Check subscription notifications',
            replace_existing=True,
            max_instances=1  # Предотвращаем одновременное выполнение
        )
        
        logger.info(f"Scheduled subscription notifications check every {settings.notification_check_interval_hours} hours")
    
    async def _check_notifications(self):
        """Обертка для проверки уведомлений с обработкой ошибок"""
        try:
            logger.info("Starting scheduled notification check...")
            stats = await NotificationService.check_and_send_notifications(self.bot)
            logger.info(f"Notification check completed: {stats}")
        except Exception as e:
            logger.error(f"Error in scheduled notification check: {e}")
    
    def start(self):
        """Запуск планировщика"""
        if not settings.enable_subscription_notifications:
            logger.info("Subscription notifications disabled, scheduler not started")
            return
        
        try:
            self.scheduler.start()
            logger.info("Scheduler started successfully")
        except Exception as e:
            logger.error(f"Error starting scheduler: {e}")
    
    async def shutdown(self):
        """Остановка планировщика"""
        try:
            if self.scheduler.running:
                self.scheduler.shutdown(wait=True)
                logger.info("Scheduler shutdown completed")
        except Exception as e:
            logger.error(f"Error shutting down scheduler: {e}")
    
    def get_jobs_info(self) -> list:
        """Получение информации о запланированных задачах"""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                'id': job.id,
                'name': job.name,
                'next_run': job.next_run_time,
                'trigger': str(job.trigger)
            })
        return jobs
    
    async def run_notification_check_now(self) -> dict:
        """Принудительный запуск проверки уведомлений"""
        logger.info("Manual notification check triggered")
        return await NotificationService.check_and_send_notifications(self.bot)