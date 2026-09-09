import time
import asyncio
import threading
import logging
from datetime import datetime, timedelta
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.request import HTTPXRequest

from config import TOKEN, ADMIN_ID, URL, CHECK_INTERVAL, PRICE, WALLET
from parser import parse_table
from storage import check_updates, clear_cache
from database import (
    add_user, has_subscription, is_admin, 
    activate_subscription, get_active_users
)
from admin import admin_panel, give_subscription, stats, expiring, broadcast, button_handler as admin_button_handler

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

print("🚀 ВЕРСИЯ 3.0 - ПОЛНАЯ")

# ============== HTTP-СЕРВЕР ДЛЯ RENDER ==============
web_app = Flask(__name__)

@web_app.route('/')
def health_check():
    return "✅ Bot is running!", 200

@web_app.route('/webhook', methods=['POST'])
def webhook():
    """Обработчик вебхука от ЮMoney"""
    print("=" * 60)
    print("📩 ПОЛУЧЕН ЗАПРОС НА /webhook!")
    print(f"Метод: {request.method}")
    print(f"Данные (form): {dict(request.form)}")
    print("=" * 60)
    
    data = request.form
    notification_type = data.get('notification_type')
    amount = data.get('amount')
    label = data.get('label')
    sender = data.get('sender')
    
    print(f"Тип: {notification_type}")
    print(f"Сумма: {amount}")
    print(f"Label: {label}")
    print(f"От: {sender}")
    
    if notification_type == 'p2p-incoming':
        if not label:
            print("⚠️ Нет label!")
            return 'Missing label', 400
        
        try:
            user_id = int(label)
            if float(amount) >= 1:
                if activate_subscription(user_id, 30):
                    clear_cache(user_id)
                    send_message(user_id, "✅ Подписка активирована на 30 дней! Используйте /status для проверки.")
                    send_message(ADMIN_ID, f"💰 Платёж от {user_id} на сумму {amount} руб")
                    print("✅ ВСЁ ОК! Возвращаем 200")
                    return 'OK', 200
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return f'Error: {e}', 400
    
    return 'Invalid', 400

def send_message(user_id, text):
    """Отправляет сообщение в Telegram"""
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        import requests
        requests.post(url, json={'chat_id': user_id, 'text': text, 'parse_mode': 'HTML'}, timeout=10)
    except Exception as e:
        print(f"❌ Ошибка отправки: {e}")

def run_web_app():
    """Запускает Flask-сервер в отдельном потоке"""
    web_app.run(host='0.0.0.0', port=10000, debug=False, use_reloader=False)

# ============== УТРЕННЕЕ УВЕДОМЛЕНИЕ ==============

async def morning_notification(app):
    """Отправляет утреннее уведомление в 8:00"""
    logger.info("🌅 Утреннее уведомление запущено. Будет отправляться каждый день в 8:00")
    
    while True:
        try:
            now = datetime.now()
            target = datetime(now.year, now.month, now.day, 8, 0, 0)
            
            if now > target:
                target += timedelta(days=1)
            
            seconds_to_wait = (target - now).total_seconds()
            logger.info(f"⏳ Следующее утреннее уведомление в {target.strftime('%H:%M')} (через {int(seconds_to_wait/60)} мин)")
            
            await asyncio.sleep(seconds_to_wait)
            
            logger.info("🌅 Отправка утреннего уведомления...")
            
            items = parse_table()
            active_users = get_active_users()
            
            if not active_users:
                logger.info("📭 Нет активных пользователей для утреннего уведомления")
                continue
            
            if not items:
                msg = (
                    "🌅 <b>Доброе утро!</b>\n\n"
                    "📭 На данный момент отключений по адресу <b>Базайская</b> не найдено.\n\n"
                    "🔔 Бот продолжает мониторинг. При появлении новых отключений — вы получите уведомление."
                )
            else:
                msg = "🌅 <b>Доброе утро!</b>\n\n"
                msg += "🔍 <b>Актуальные отключения:</b>\n\n"
                for item in items:
                    day_label = "ЗАВТРА" if item.get('is_planned', False) else "СЕГОДНЯ"
                    msg += f"📅 <b>{day_label}</b>\n"
                    msg += f"📌 {item['resource']}\n"
                    msg += f"📍 {item['address'][:100]}\n"
                    msg += f"⏰ {item['period']}\n\n"
                msg += "📱 Используйте /check для обновления."
            
            keyboard = [[InlineKeyboardButton("🔍 Проверить сейчас", callback_data='check')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            sent_count = 0
            for user_id in active_users:
                try:
                    await app.bot.send_message(
                        chat_id=user_id,
                        text=msg,
                        parse_mode='HTML',
                        reply_markup=reply_markup
                    )
                    sent_count += 1
                except Exception as e:
                    logger.error(f"❌ Ошибка отправки {user_id}: {e}")
            
            logger.info(f"🌅 Утреннее уведомление отправлено {sent_count} пользователям")
            
        except Exception as e:
            logger.error(f"❌ Ошибка в утреннем уведомлении: {e}")
            await asyncio.sleep(300)

def run_morning(app):
    """Запуск утреннего уведомления в отдельном потоке"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(morning_notification(app))
    loop.close()

# ============== КОМАНДЫ ДЛЯ ПОЛЬЗОВАТЕЛЕЙ ==============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    add_user(user_id, user.username or user.first_name)
    clear_cache(user_id)
    
    keyboard = [
        [InlineKeyboardButton("🔍 Проверить отключения", callback_data='check')],
        [InlineKeyboardButton("💰 Оплатить подписку", callback_data='pay')],
        [InlineKeyboardButton("📊 Статус подписки", callback_data='status')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if has_subscription(user_id):
        msg = f"👋 Привет, {user.first_name}!\n\n✅ Ваша подписка активна.\n🔔 Бот будет присылать уведомления об отключениях."
    else:
        msg = f"👋 Привет, {user.first_name}!\n\n❌ У вас нет активной подписки.\n💳 Стоимость: {PRICE} руб/месяц.\n📱 Для оплаты используйте /pay"
    
    if is_admin(user_id):
        msg += "\n\n🔐 /admin - Панель управления"
    
    await update.message.reply_text(msg, reply_markup=reply_markup)

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
    else:
        query = None
    
    clear_cache(user_id)
    
    if has_subscription(user_id):
        msg = "✅ Ваша подписка активна!"
    else:
        msg = f"❌ Подписка неактивна.\n💳 Стоимость: {PRICE} руб/месяц\n📱 Для оплаты используйте /pay"
    
    if query:
        await query.edit_message_text(msg)
    else:
        await update.message.reply_text(msg)

async def pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
    else:
        query = None
    
    import urllib.parse
    params = {
        'receiver': WALLET,
        'quickpay-form': 'shop',
        'targets': 'Подписка на бот',
        'sum': str(PRICE),
        'label': str(user_id)
    }
    link = f"https://yoomoney.ru/quickpay/confirm.xml?{urllib.parse.urlencode(params)}"
    
    msg = f"💳 <b>Оформление подписки</b>\n\n📅 Стоимость: {PRICE} руб/месяц\n🔗 <a href='{link}'>Ссылка для оплаты</a>"
    
    if query:
        await query.edit_message_text(msg, parse_mode='HTML')
    else:
        await update.message.reply_text(msg, parse_mode='HTML')

async def check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("🔍 /check вызвана")
    user_id = update.effective_user.id
    
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
    else:
        query = None
    
    clear_cache(user_id)
    
    if not has_subscription(user_id):
        msg = "❌ У вас нет активной подписки.\nОформите подписку через /pay"
        if query:
            await query.edit_message_text(msg)
        else:
            await update.message.reply_text(msg)
        return
    
    items = parse_table()
    print(f"🔍 Парсер вернул {len(items)} элементов")
    
    if not items:
        msg = "📭 На данный момент отключений не найдено."
    else:
        msg = "🔍 <b>Актуальные отключения:</b>\n\n"
        for item in items:
            day_label = "ЗАВТРА" if item.get('is_planned', False) else "СЕГОДНЯ"
            msg += f"📅 <b>{day_label}</b>\n"
            msg += f"📌 {item['resource']}\n"
            msg += f"📍 {item['address'][:100]}\n"
            msg += f"⏰ {item['period']}\n\n"
    
    keyboard = [[InlineKeyboardButton("🔄 Обновить", callback_data='check')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if query:
        await query.edit_message_text(msg, parse_mode='HTML', reply_markup=reply_markup)
    else:
        await update.message.reply_text(msg, parse_mode='HTML', reply_markup=reply_markup)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 <b>Бот мониторит отключения</b>\n\n"
        "Команды:\n"
        "/start - Главное меню\n"
        "/check - Проверить отключения\n"
        "/status - Статус подписки\n"
        "/pay - Оплатить подписку\n"
        "/help - Помощь\n"
        "/refresh - Обновить статус\n"
        "/admin - Панель администратора",
        parse_mode='HTML'
    )

async def refresh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    clear_cache(user_id)
    if has_subscription(user_id):
        await update.message.reply_text("✅ Статус обновлён! Подписка активна.")
    else:
        await update.message.reply_text("❌ Статус обновлён. Подписка неактивна.")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'check':
        await check(update, context)
    elif query.data == 'pay':
        await pay(update, context)
    elif query.data == 'status':
        await status(update, context)
    elif query.data.startswith('admin_'):
        await admin_button_handler(update, context)

# ============== ФОНОВАЯ ЗАДАЧА ==============

async def check_site(app):
    logger.info("🔄 Фоновый парсинг запущен")
    while True:
        try:
            logger.info(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Проверка сайта...")
            items = parse_table()
            updates = check_updates(items)
            active_users = get_active_users()
            
            for update in updates:
                if update[0] == 'new':
                    day_label = "ЗАВТРА" if update[1].get('is_planned', False) else "СЕГОДНЯ"
                    msg = f"🔔 <b>НОВОЕ ОТКЛЮЧЕНИЕ!</b>\n📅 {day_label}\n📌 {update[1]['resource']}\n📍 {update[1]['address']}\n⏰ {update[1]['period']}"
                elif update[0] == 'changed':
                    msg = f"🔄 <b>ИЗМЕНИЛСЯ ПЕРИОД!</b>\nСтарый: {update[2]}\nНовый: {update[1]['period']}"
                else:
                    continue
                
                keyboard = [[InlineKeyboardButton("🔍 Проверить", callback_data='check')]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                for user_id in active_users:
                    try:
                        await app.bot.send_message(chat_id=user_id, text=msg, parse_mode='HTML', reply_markup=reply_markup)
                    except Exception as e:
                        logger.error(f"❌ Ошибка отправки {user_id}: {e}")
            
            if not updates:
                logger.info("Новых отключений или изменений нет")
            
        except Exception as e:
            logger.error(f"❌ Ошибка в фоновой задаче: {e}")
        
        await asyncio.sleep(CHECK_INTERVAL)

def run_async(app):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(check_site(app))
    loop.close()

# ============== ЗАПУСК ==============

def main():
    request = HTTPXRequest(
        connection_pool_size=8,
        read_timeout=60,
        write_timeout=60,
        connect_timeout=60,
        pool_timeout=60
    )
    
    app = Application.builder().token(TOKEN).request(request).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("refresh", refresh))
    app.add_handler(CommandHandler("pay", pay))
    app.add_handler(CommandHandler("check", check))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("give", give_subscription))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("expiring", expiring))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    threading.Thread(target=run_web_app, daemon=True).start()
    logger.info("🌐 HTTP-сервер запущен на порту 10000")
    
    threading.Thread(target=run_async, args=(app,), daemon=True).start()
    
    threading.Thread(target=run_morning, args=(app,), daemon=True).start()
    logger.info("🌅 Утреннее уведомление запланировано на 8:00")
    
    logger.info("🤖 Бот запущен!")
    app.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES, stop_signals=None)

if __name__ == '__main__':
    main()
