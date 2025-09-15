from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from config.settings import settings
from app.models import Base
import logging

logger = logging.getLogger(__name__)


class DatabaseService:
    def __init__(self):
        self.engine = create_async_engine(
            settings.database_url,
            poolclass=NullPool,
            echo=settings.debug
        )
        self.async_session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
    
    async def create_tables(self):
        """Создание всех таблиц"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created successfully")
    
    async def drop_tables(self):
        """Удаление всех таблиц"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            logger.info("Database tables dropped successfully")
    
    async def get_session(self) -> AsyncSession:
        """Получение сессии базы данных"""
        async with self.async_session() as session:
            try:
                yield session
            finally:
                await session.close()
    
    async def close(self):
        """Закрытие соединения с базой данных"""
        await self.engine.dispose()
        logger.info("Database connection closed")


# Глобальный экземпляр сервиса базы данных
db_service = DatabaseService()