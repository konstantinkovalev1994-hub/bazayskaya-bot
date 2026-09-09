import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from flask import Flask
import threading

from config import TOKEN, ADMIN_ID, URL, CHECK_INTERVAL, PRICE, WALLET
from parser import parse_table
from database import add_user, has_subscription, is_admin, activate_subscription, get_active_users

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask для Render
web_app = Flask(__name__)

@web_app.route('/')
def health():
    return "✅ Bot is running!", 200

def run_web():
    web_app.run(host='0.0.0.0', port=10000)

# ============== КОМАНДЫ ==============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user(user.id, user.username or user.first_name)
    
    keyboard = [
        [InlineKeyboardButton("🔍 Проверить отключения", callback_data='check')],
        [InlineKeyboardButton("💰 Оплатить подписку", callback_data='pay')],
        [InlineKeyboardButton("📊 Статус подписки", callback_data='status')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text("👋 Привет! Бот работает!", reply_markup=reply_markup)

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if has_subscription(user_id):
        await update.message.reply_text("✅ Подписка активна!")
    else:
        await update.message.reply_text("❌ Подписка неактивна. Используйте /pay")

async def pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    import urllib.parse
    params = {
        'receiver': WALLET,
        'quickpay-form': 'shop',
        'targets': 'Подписка',
        'sum': str(PRICE),
        'label': str(user_id)
    }
    link = f"https://yoomoney.ru/quickpay/confirm.xml?{urllib.parse.urlencode(params)}"
    await update.message.reply_text(f"💳 Оплатите по ссылке:\n{link}")

async def check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("🔍 /check вызвана")
    user_id = update.effective_user.id
    
    if not has_subscription(user_id):
        await update.message.reply_text("❌ Нет подписки. Используйте /pay")
        return
    
    items = parse_table()
    if items:
        msg = "🔍 Найдены отключения:\n\n"
        for item in items:
            msg += f"📌 {item['address']}\n"
            msg += f"⏰ {item['period']}\n\n"
        await update.message.reply_text(msg)
    else:
        await update.message.reply_text("📭 Отключений не найдено.")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопок"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'check':
        await check(update, context)
    elif query.data == 'pay':
        await pay(update, context)
    elif query.data == 'status':
        await status(update, context)

# ============== ЗАПУСК ==============

def main():
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("pay", pay))
    app.add_handler(CommandHandler("check", check))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    # Запускаем Flask для Render
    threading.Thread(target=run_web, daemon=True).start()
    
    print("🚀 Бот запущен!")
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
