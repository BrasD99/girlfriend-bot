import google.generativeai as genai
from config.settings import settings
from app.models import GirlfriendProfile
from typing import Optional
import logging
import json
import re

logger = logging.getLogger(__name__)

# Настройка Gemini API
genai.configure(api_key=settings.gemini_api_key)


def extract_json_from_markdown(text: str) -> str:
    """Извлечение JSON из markdown блока кода"""
    # Поиск JSON в блоке кода ```json...```
    json_match = re.search(r'```(?:json)?\s*\n?({[^`]+})\s*\n?```', text, re.DOTALL)
    if json_match:
        return json_match.group(1).strip()
    
    # Поиск JSON в обычном блоке кода ```...```
    code_match = re.search(r'```\s*\n?({[^`]+})\s*\n?```', text, re.DOTALL)
    if code_match:
        return code_match.group(1).strip()
    
    # Поиск JSON объекта в тексте
    json_object_match = re.search(r'({\s*"[^}]+})', text, re.DOTALL)
    if json_object_match:
        return json_object_match.group(1).strip()
    
    # Если ничего не найдено, возвращаем исходный текст
    return text.strip()


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
            - name: русское женское имя
            - age: возраст (18-30)
            - personality: описание характера (2-3 предложения)
            - appearance: описание внешности (2-3 предложения)
            - interests: интересы и хобби (через запятую)
            - background: краткая предыстория (2-3 предложения)
            - communication_style: стиль общения (1-2 предложения)
            
            Отвечай в формате:
            ```json
            {{
              "name": "Имя",
              "age": 25,
              "personality": "Описание характера...",
              "appearance": "Описание внешности...",
              "interests": "Интересы, хобби",
              "background": "Предыстория...",
              "communication_style": "Стиль общения..."
            }}
            ```
            """
            
            response = await self.model.generate_content_async(
                prompt,
                safety_settings=self.safety_settings
            )
            
            if response.text:
                # Извлекаем JSON из markdown и парсим
                try:
                    json_text = extract_json_from_markdown(response.text)
                    logger.info(f"Extracted JSON from Gemini response: {json_text[:200]}...")
                    
                    profile_data = json.loads(json_text)
                    
                    # Проверяем, что все обязательные поля присутствуют
                    required_fields = ["name", "age", "personality", "appearance", "interests", "background", "communication_style"]
                    for field in required_fields:
                        if field not in profile_data:
                            logger.warning(f"Missing required field: {field}")
                            profile_data[field] = self._get_default_profile()[field]
                    
                    # Проверяем возраст
                    if not isinstance(profile_data.get("age"), int) or not (18 <= profile_data["age"] <= 50):
                        profile_data["age"] = 23
                    
                    logger.info(f"Successfully parsed profile for: {profile_data.get('name', 'Unknown')}")
                    return profile_data
                    
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse JSON from Gemini response: {e}")
                    logger.warning(f"Raw response: {response.text[:500]}...")
                    return self._get_default_profile()
                except Exception as e:
                    logger.error(f"Error processing Gemini response: {e}")
                    return self._get_default_profile()
            else:
                logger.warning("Empty response from Gemini")
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