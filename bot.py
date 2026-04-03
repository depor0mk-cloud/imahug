import logging
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import requests
import asyncio

# Конфиг (для Render используем переменные окружения)
BOT_TOKEN = os.getenv('BOT_TOKEN', '8665595835:AAHOuVKY2VFYoWm8t0KRt9Abl6Sk0d0X_f8')
WEATHER_KEY = os.getenv('WEATHER_KEY', '07429fb452f7c75e79ded39101b5e6a4')
NEWS_KEY = os.getenv('NEWS_KEY', '6ba268f9fe9d4d789aa0c47ce5c34658')

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

subscribers = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat.id
    subscribers[user_id] = {'city': 'Москва'}
    await update.message.reply_text(
        "✅ Подписка активирована!\n\n"
        "/weather - погода\n"
        "/news - новости\n"
        "/city <название> - сменить город\n"
        "/stop - отписаться"
    )

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat.id
    if user_id in subscribers:
        del subscribers[user_id]
        await update.message.reply_text("Отписка выполнена")
    else:
        await update.message.reply_text("Вы не подписаны")

async def weather(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat.id
    city = subscribers.get(user_id, {}).get('city', 'Москва')
    
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_KEY}&lang=ru&units=metric"
        r = requests.get(url, timeout=10)
        
        if r.status_code == 200:
            d = r.json()
            temp = round(d['main']['temp'])
            desc = d['weather'][0]['description']
            await update.message.reply_text(f"🌤 {city}\n🌡 {temp}°C, {desc}")
        else:
            await update.message.reply_text("❌ Ошибка получения погоды")
    except Exception as e:
        logger.error(f"Weather error: {e}")
        await update.message.reply_text("❌ Ошибка получения погоды")

async def news(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        url = f"https://newsapi.org/v2/top-headlines?country=ru&pageSize=3&apiKey={NEWS_KEY}"
        r = requests.get(url, timeout=10)
        
        if r.status_code == 200:
            articles = r.json().get('articles', [])
            text = "📰 Новости:\n\n"
            for i, a in enumerate(articles, 1):
                text += f"{i}. {a['title']}\n\n"
            await update.message.reply_text(text)
        else:
            await update.message.reply_text("❌ Ошибка загрузки новостей")
    except Exception as e:
        logger.error(f"News error: {e}")
        await update.message.reply_text("❌ Ошибка загрузки новостей")

async def city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Укажите город: /city Москва")
        return
    
    user_id = update.message.chat.id
    new_city = ' '.join(context.args)
    
    if user_id not in subscribers:
        subscribers[user_id] = {}
    
    subscribers[user_id]['city'] = new_city
    await update.message.reply_text(f"✅ Город изменен на {new_city}")

async def send_notifications(context: ContextTypes.DEFAULT_TYPE):
    logger.info("Sending notifications...")
    for user_id, data in list(subscribers.items()):
        try:
            city_name = data.get('city', 'Москва')
            
            url = f"http://api.openweathermap.org/data/2.5/weather?q={city_name}&appid={WEATHER_KEY}&lang=ru&units=metric"
            r = requests.get(url, timeout=10)
            weather_text = "Погода недоступна"
            
            if r.status_code == 200:
                d = r.json()
                temp = round(d['main']['temp'])
                desc = d['weather'][0]['description']
                weather_text = f"🌤 {city_name}: {temp}°C, {desc}"
            
            url = f"https://newsapi.org/v2/top-headlines?country=ru&pageSize=1&apiKey={NEWS_KEY}"
            r = requests.get(url, timeout=10)
            news_text = "Новости недоступны"
            
            if r.status_code == 200:
                articles = r.json().get('articles', [])
                if articles:
                    news_text = f"📰 {articles[0]['title']}"
            
            msg = f"🔔 Сводка дня\n\n{weather_text}\n\n{news_text}"
            await context.bot.send_message(chat_id=user_id, text=msg)
            
        except Exception as e:
            logger.error(f"Notification error for {user_id}: {e}")
        
        await asyncio.sleep(0.5)

def main():
    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Добавляем обработчики
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('stop', stop))
    application.add_handler(CommandHandler('weather', weather))
    application.add_handler(CommandHandler('news', news))
    application.add_handler(CommandHandler('city', city))
    
    # Планировщик уведомлений (каждые 12 часов)
    if application.job_queue:
        application.job_queue.run_repeating(
            send_notifications,
            interval=43200,
            first=60
        )
    
    logger.info("Bot starting...")
    
    # Запуск с правильными параметрами для Render
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True
    )

if __name__ == '__main__':
    main()
