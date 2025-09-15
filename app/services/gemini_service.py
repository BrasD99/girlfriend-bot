import google.generativeai as genai
from config.settings import settings
from app.models import GirlfriendProfile
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Настройка Gemini API
genai.configure(api_key=settings.gemini_api_key)


class GeminiService:
    # Доступные модели Gemini
    AVAILABLE_MODELS = {
        "gemini-pro": {
            "name": "Gemini Pro",
            "description": "Базовая модель с хорошим качеством",
            "recommended_for": "general"
        },
        "gemini-1.5-pro": {
            "name": "Gemini 1.5 Pro",
            "description": "Продвинутая модель с высоким качеством",
            "recommended_for": "production"
        },
        "gemini-1.5-flash": {
            "name": "Gemini 1.5 Flash",
            "description": "Быстрая модель с хорошим качеством",
            "recommended_for": "development"
        },
        "gemini-2.0-flash-lite": {
            "name": "Gemini 2.0 Flash Lite",
            "description": "Новая легкая и быстрая модель",
            "recommended_for": "development"
        }
    }
    
    def __init__(self):
        # Проверяем, что модель поддерживается
        if settings.gemini_model not in self.AVAILABLE_MODELS:
            logger.warning(
                f"Model {settings.gemini_model} not in supported list. "
                f"Supported models: {list(self.AVAILABLE_MODELS.keys())}"
            )
        
        self.model = genai.GenerativeModel(settings.gemini_model)
        model_info = self.AVAILABLE_MODELS.get(settings.gemini_model, {})
        logger.info(
            f"Initialized Gemini service with model: {settings.gemini_model} "
            f"({model_info.get('name', 'Unknown')})"
        )
        self.safety_settings = [
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_NONE"
            },
            {
                "category": "HARM_CATEGORY_HATE_SPEECH", 
                "threshold": "BLOCK_NONE"
            },
            {
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": "BLOCK_NONE"
            },
            {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_NONE"
            }
        ]
    
    async def generate_response(
        self,
        girlfriend_profile: GirlfriendProfile,
        user_message: str,
        conversation_context: Optional[str] = None
    ) -> str:
        """Генерация ответа от девушки"""
        try:
            # Создаем системный промпт
            system_prompt = girlfriend_profile.get_full_prompt()
            
            # Добавляем контекст разговора если есть
            if conversation_context:
                system_prompt += f"\n\nКонтекст предыдущих сообщений:\n{conversation_context}"
            
            # Формируем полный промпт
            full_prompt = f"{system_prompt}\n\nПользователь написал: {user_message}\n\nОтветь как {girlfriend_profile.name}:"
            
            # Генерируем ответ
            response = await self.model.generate_content_async(
                full_prompt,
                safety_settings=self.safety_settings
            )
            
            if response.text:
                logger.info(f"Generated response for profile {girlfriend_profile.name}")
                return response.text.strip()
            else:
                logger.warning("Empty response from Gemini")
                return "Извини, я не знаю что ответить... 😔"
                
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return "Прости, у меня сейчас проблемы с интернетом... Попробуй написать еще раз 😊"
    
    async def generate_profile_suggestions(self, user_preferences: str) -> dict:
        """Генерация предложений для профиля девушки на основе предпочтений пользователя"""
        try:
            prompt = f"""
            На основе предпочтений пользователя создай характеристики для виртуальной девушки.
            
            Предпочтения пользователя: {user_preferences}
            
            Создай JSON с полями:
            - name: имя девушки
            - age: возраст (18-30)
            - personality: описание характера (2-3 предложения)
            - appearance: описание внешности (2-3 предложения)
            - interests: интересы и хобби (через запятую)
            - background: краткая предыстория (2-3 предложения)
            - communication_style: стиль общения (1-2 предложения)
            
            Отвечай только JSON без дополнительного текста.
            """
            
            response = await self.model.generate_content_async(
                prompt,
                safety_settings=self.safety_settings
            )
            
            if response.text:
                # Попытка парсинга JSON
                import json
                try:
                    return json.loads(response.text.strip())
                except json.JSONDecodeError:
                    logger.warning("Failed to parse JSON from Gemini response")
                    return self._get_default_profile()
            else:
                return self._get_default_profile()
                
        except Exception as e:
            logger.error(f"Error generating profile suggestions: {e}")
            return self._get_default_profile()
    
    def _get_default_profile(self) -> dict:
        """Профиль по умолчанию"""
        return {
            "name": "Анна",
            "age": 23,
            "personality": "Добрая и отзывчивая девушка с хорошим чувством юмора. Любит общаться и поддерживать близких людей.",
            "appearance": "Привлекательная девушка среднего роста с длинными темными волосами и карими глазами.",
            "interests": "чтение, фильмы, музыка, прогулки, кулинария",
            "background": "Студентка университета, изучает психологию. Живет в большом городе, любит путешествовать.",
            "communication_style": "Общается тепло и дружелюбно, часто использует эмодзи. Любит задавать вопросы и проявлять интерес к собеседнику."
        }
    
    async def moderate_content(self, text: str) -> bool:
        """Модерация контента (базовая проверка)"""
        try:
            # Простая проверка на запрещенные слова
            forbidden_words = ["убить", "смерть", "суицид", "наркотики"]
            text_lower = text.lower()
            
            for word in forbidden_words:
                if word in text_lower:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error in content moderation: {e}")
            return True  # В случае ошибки разрешаем контент
    
    def get_model_info(self) -> dict:
        """Получение информации о текущей модели"""
        model_info = self.AVAILABLE_MODELS.get(settings.gemini_model, {})
        return {
            "model_id": settings.gemini_model,
            "name": model_info.get("name", "Unknown Model"),
            "description": model_info.get("description", "No description available"),
            "recommended_for": model_info.get("recommended_for", "general")
        }
    
    @classmethod
    def get_available_models(cls) -> dict:
        """Получение списка доступных моделей"""
        return cls.AVAILABLE_MODELS