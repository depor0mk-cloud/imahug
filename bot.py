import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from telegram import Update
import requests
from datetime import datetime
import asyncio

# Ключи API
TELEGRAM_TOKEN = '8665595835:AAHOuVKY2VFYoWm8t0KRt9Abl6Sk0d0X_f8'
OPENWEATHER_API_KEY = '07429fb452f7c75e79ded39101b5e6a4'
NEWS_API_KEY = '6ba268f9fe9d4d789aa0c47ce5c34658'

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Хранилище подписчиков и их настроек
subscribers = {}

# ========== ОБРАБОТЧИКИ КОМАНД ==========

async def start(update: Update, context):
    """Обработчик команды /start"""
    user_id = update.message.chat.id
    username = update.message.from_user.first_name
    
    subscribers[user_id] = {
        'city': 'Москва',
        'notifications': True,
        'username': username
    }
    
    welcome_message = (
        f"👋 Привет, {username}!\n\n"
        "Добро пожаловать в ErxTime Bot!\n\n"
        "📋 Доступные команды:\n"
        "/weather - Узнать погоду\n"
        "/news - Последние новости\n"
        "/setcity <город> - Установить город\n"
        "/stop - Отписаться от уведомлений\n"
        "/help - Справка"
    )
    
    await update.message.reply_text(welcome_message)

async def stop(update: Update, context):
    """Обработчик команды /stop"""
    user_id = update.message.chat.id
    
    if user_id in subscribers:
        del subscribers[user_id]
        await update.message.reply_text("😢 Вы отписались от уведомлений. Будем скучать!")
    else:
        await update.message.reply_text("❌ Вы не подписаны. Используйте /start для подписки.")

async def help_command(update: Update, context):
    """Обработчик команды /help"""
    help_text = (
        "📖 *Справка по командам:*\n\n"
        "/start - Подписаться на уведомления\n"
        "/weather - Получить информацию о погоде\n"
        "/news - Последние новости России\n"
        "/setcity <город> - Установить ваш город\n"
        "/stop - Отписаться от уведомлений\n"
        "/help - Показать эту справку\n\n"
        "⚙️ Бот автоматически отправляет уведомления каждые 12 часов."
    )
    
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def weather_command(update: Update, context):
    """Команда для получения погоды"""
    user_id = update.message.chat.id
    
    if user_id in subscribers:
        city = subscribers[user_id].get('city', 'Москва')
    else:
        city = 'Москва'
    
    weather = get_weather(city)
    await update.message.reply_text(f"🌤 {weather}")

async def news_command(update: Update, context):
    """Команда для получения новостей"""
    news = get_news()
    await update.message.reply_text(f"📰 {news}")

async def setcity_command(update: Update, context):
    """Команда для установки города"""
    user_id = update.message.chat.id
    
    if not context.args:
        await update.message.reply_text("❌ Укажите город! Например: /setcity Санкт-Петербург")
        return
    
    city = ' '.join(context.args)
    
    # Проверяем, существует ли город
    weather = get_weather(city)
    
    if "Не удалось получить погоду" in weather:
        await update.message.reply_text(f"❌ Город '{city}' не найден. Проверьте написание.")
        return
    
    if user_id not in subscribers:
        subscribers[user_id] = {'notifications': True}
    
    subscribers[user_id]['city'] = city
    await update.message.reply_text(f"✅ Город установлен: {city}\n\n{weather}")

# ========== ФУНКЦИИ ПОЛУЧЕНИЯ ДАННЫХ ==========

def get_weather(city='Москва'):
    """Получение данных о погоде"""
    try:
        url = (
            f"http://api.openweathermap.org/data/2.5/weather"
            f"?q={city}&appid={OPENWEATHER_API_KEY}&lang=ru&units=metric"
        )
        
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            
            if 'main' in data and 'weather' in data:
                temp = round(data['main']['temp'])
                feels_like = round(data['main']['feels_like'])
                description = data['weather'][0]['description'].capitalize()
                humidity = data['main']['humidity']
                wind_speed = round(data['wind']['speed'])
                
                weather_text = (
                    f"📍 {city}\n"
                    f"🌡 Температура: {temp}°C (ощущается как {feels_like}°C)\n"
                    f"☁️ {description}\n"
                    f"💧 Влажность: {humidity}%\n"
                    f"💨 Ветер: {wind_speed} м/с"
                )
                
                return weather_text
        
        return f"❌ Не удалось получить погоду для города {city}"
        
    except Exception as e:
        logger.error(f"Ошибка получения погоды: {e}")
        return "❌ Ошибка при получении данных о погоде"

def get_news(count=5):
    """Получение последних новостей"""
    try:
        url = f"https://newsapi.org/v2/top-headlines?country=ru&pageSize={count}&apiKey={NEWS_API_KEY}"
        
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            articles = data.get('articles', [])
            
            if articles:
                news_text = "📰 *Последние новости:*\n\n"
                
                for i, article in enumerate(articles[:5], 1):
                    title = article.get('title', 'Без заголовка')
                    news_text += f"{i}. {title}\n\n"
                
                return news_text
        
        return "❌ Не удалось загрузить новости"
        
    except Exception as e:
        logger.error(f"Ошибка получения новостей: {e}")
        return "❌ Ошибка при загрузке новостей"

# ========== ФУНКЦИЯ ОТПРАВКИ УВЕДОМЛЕНИЙ ==========

async def send_notifications(application):
    """Отправка уведомлений всем подписчикам"""
    logger.info("Начинаем рассылку уведомлений...")
    
    for user_id, user_data in list(subscribers.items()):
        if not user_data.get('notifications', True):
            continue
        
        try:
            city = user_data.get('city', 'Москва')
            weather = get_weather(city)
            news = get_news(3)
            
            message = (
                f"🔔 *Ежедневная сводка ErxTime*\n\n"
                f"{weather}\n\n"
                f"{news}\n"
                f"⏰ {datetime.now().strftime('%d.%m.%Y %H:%M')}"
            )
            
            await application.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode='Markdown'
            )
            
            logger.info(f"Уведомление отправлено пользователю {user_id}")
            
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления пользователю {user_id}: {e}")
            
        # Задержка между отправками
        await asyncio.sleep(0.5)

# ========== ПЛАНИРОВЩИК УВЕДОМЛЕНИЙ ==========

async def scheduled_notifications(application):
    """Периодическая отправка уведомлений каждые 12 часов"""
    while True:
        await asyncio.sleep(43200)  # 12 часов
        await send_notifications(application)

# ========== ОБРАБОТЧИК ОШИБОК ==========

async def error_handler(update: Update, context):
    """Обработчик ошибок"""
    logger.error(f"Ошибка при обработке обновления: {context.error}")

# ========== ГЛАВНАЯ ФУНКЦИЯ ==========

def main():
    """Запуск бота"""
    # Создание приложения
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Регистрация обработчиков команд
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('stop', stop))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('weather', weather_command))
    application.add_handler(CommandHandler('news', news_command))
    application.add_handler(CommandHandler('setcity', setcity_command))
    
    # Обработчик ошибок
    application.add_error_handler(error_handler)
    
    # Запуск фоновой задачи для рассылки
    application.job_queue.run_repeating(
        lambda context: send_notifications(context.application),
        interval=43200,  # 12 часов
        first=10  # Первая отправка через 10 секунд после запуска
    )
    
    # Запуск бота
    logger.info("Бот запущен!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
