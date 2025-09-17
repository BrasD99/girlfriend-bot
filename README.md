# Girlfriend Bot - Telegram Bot с ИИ-компаньоном

Полноценный Telegram-бот с виртуальной девушкой-компаньоном, использующий Gemini AI для генерации ответов.

## Возможности

- 💬 **Интеллектуальное общение** с виртуальной девушкой через Gemini AI
- 👤 **Настраиваемые профили** - создание уникальных персонажей
- 💎 **Система подписок** с интеграцией YooKassa
- 🎁 **Бесплатный пробный период** для новых пользователей
- 📊 **База данных PostgreSQL** для хранения данных
- 🔄 **Redis** для кэширования и состояний FSM
- 🐳 **Docker** для простого развертывания

## Технологии

- **Python 3.11+**
- **aiogram 3.x** - Telegram Bot API
- **SQLAlchemy 2.x** - ORM для работы с БД
- **PostgreSQL** - основная база данных
- **Redis** - кэширование и FSM
- **Google Gemini AI** - генерация ответов
- **YooKassa** - платежная система
- **Alembic** - миграции БД
- **Docker & Docker Compose** - контейнеризация

## Быстрый старт

### 1. Клонирование репозитория

```bash
git clone <repository-url>
cd girlfriend-bot
```

### 2. Настройка окружения

Скопируйте файл с переменными окружения:

```bash
cp .env.example .env
```

Отредактируйте `.env` файл, указав ваши токены и настройки:

```env
# Telegram Bot
BOT_TOKEN=your_telegram_bot_token_here

# Database
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/girlfriend_bot

# Gemini AI
GEMINI_API_KEY=your_gemini_api_key_here

# YooKassa
YOOKASSA_SHOP_ID=your_yookassa_shop_id
YOOKASSA_SECRET_KEY=your_yookassa_secret_key

# Redis
REDIS_URL=redis://localhost:6379/0

# App Settings
DEBUG=True
TRIAL_DAYS=7
SUBSCRIPTION_PRICE=299
WEBHOOK_URL=https://your-domain.com/webhook
WEBHOOK_PATH=/webhook
```

### 3. Запуск с Docker Compose (рекомендуется)

```bash
# Запуск всех сервисов
docker-compose up -d

# Просмотр логов
docker-compose logs -f bot
```

### 4. Ручная установка

#### Установка зависимостей

```bash
# Создание виртуального окружения
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows

# Установка зависимостей
pip install -r requirements.txt
```

#### Настройка базы данных

```bash
# Запуск PostgreSQL и Redis (если не используете Docker)
# Создание миграций
alembic revision --autogenerate -m "Initial migration"

# Применение миграций
alembic upgrade head
```

#### Запуск бота

```bash
python main.py
```

## Получение токенов

### Telegram Bot Token

1. Найдите [@BotFather](https://t.me/BotFather) в Telegram
2. Отправьте `/newbot`
3. Следуйте инструкциям для создания бота
4. Скопируйте полученный токен

### Gemini API Key

1. Перейдите на [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Создайте новый API ключ
3. Скопируйте ключ в настройки

### Настройка модели Gemini

Доступные модели:
- `gemini-pro` - базовая модель (по умолчанию)
- `gemini-1.5-pro` - продвинутая модель (рекомендуется для продакшена)
- `gemini-1.5-flash` - быстрая модель
- `gemini-2.0-flash-lite` - новая легкая модель (рекомендуется для разработки)

Укажите модель в переменной `GEMINI_MODEL` в файле `.env`

### YooKassa

1. Зарегистрируйтесь в [YooKassa](https://yookassa.ru/)
2. Получите Shop ID и Secret Key в личном кабинете
3. Настройте webhook URL для уведомлений о платежах

## Структура проекта

```
girlfriend-bot/
├── app/
│   ├── handlers/          # Обработчики команд и сообщений
│   ├── models/           # Модели базы данных
│   ├── services/         # Бизнес-логика
│   └── utils/            # Утилиты и хелперы
├── config/               # Конфигурация
├── migrations/           # Миграции базы данных
├── main.py              # Точка входа
├── requirements.txt     # Зависимости Python
├── docker-compose.yml   # Docker Compose конфигурация
└── README.md           # Документация
```

## Основные команды бота

- `/start` - Запуск бота и главное меню
- `/help` - Справка по использованию
- `/subscription` - Управление подпиской
- `/profile` - Управление профилем девушки
- `/chat` - Начать общение
- `/stop` - Выйти из режима общения

## Функциональность

### Создание профиля девушки

Пользователи могут создавать профили тремя способами:

1. **Вручную** - пошаговое заполнение всех характеристик
2. **С помощью ИИ** - описание предпочтений, ИИ создает профиль
3. **Случайный профиль** - ИИ генерирует случайный профиль

### Система подписок

- 🎁 **Пробный период**: 7 дней бесплатно для новых пользователей
- 📅 **Месячная подписка**: 299₽/месяц
- 📈 **Квартальная подписка**: 799₽/3 месяца (экономия 11%)
- 🏆 **Годовая подписка**: 2399₽/год (экономия 33%)
- 💳 **Оплата**: через YooKassa (карты, электронные кошельки)

### Общение с ИИ

- Персонализированные ответы на основе профиля девушки
- Сохранение контекста разговора
- Эмоциональные и живые ответы
- Отсутствие ограничений на темы общения

## Развертывание в продакшене

### Настройка webhook

Для продакшена рекомендуется использовать webhook вместо polling:

1. Получите SSL сертификат для вашего домена
2. Настройте веб-сервер (nginx) для проксирования запросов
3. Укажите `WEBHOOK_URL` в переменных окружения
4. Перезапустите бота

### Мониторинг и логи

```bash
# Просмотр логов в Docker
docker-compose logs -f bot

# Мониторинг ресурсов
docker stats
```

### Резервное копирование

Регулярно создавайте резервные копии базы данных:

```bash
# Создание бэкапа
docker-compose exec postgres pg_dump -U postgres girlfriend_bot > backup.sql

# Восстановление из бэкапа
docker-compose exec -T postgres psql -U postgres girlfriend_bot < backup.sql
```

## Безопасность

- Все секретные ключи хранятся в переменных окружения
- Используется HTTPS для webhook
- Валидация и санитизация пользовательского ввода
- Ограничения на размер сообщений

## Поддержка

При возникновении проблем:

1. Проверьте логи: `docker-compose logs bot`
2. Убедитесь, что все переменные окружения настроены
3. Проверьте доступность внешних сервисов (Gemini AI, YooKassa)
4. Создайте issue в репозитории

## Лицензия

MIT License - см. файл LICENSE для деталей.

## Разработка

### Добавление новых функций

1. Создайте новый обработчик в `app/handlers/`
2. Добавьте необходимые модели в `app/models/`
3. Реализуйте бизнес-логику в `app/services/`
4. Создайте миграцию: `alembic revision --autogenerate -m "Description"`
5. Примените миграцию: `alembic upgrade head`

### Тестирование

```bash
# Запуск в режиме разработки
DEBUG=True python main.py

# Проверка кода
flake8 app/
black app/
```

---

**Примечание**: Этот бот предназначен для развлекательных целей. Убедитесь, что использование соответствует правилам Telegram и местному законодательству.