from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import (
    is_admin, get_all_users, get_active_users, 
    activate_subscription, get_expiring_soon
)
from config import ADMIN_ID
from storage import clear_cache

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Доступ запрещен.")
        return
    
    keyboard = [
        [InlineKeyboardButton("📊 Статистика", callback_data='admin_stats')],
        [InlineKeyboardButton("👥 Все пользователи", callback_data='admin_users')],
        [InlineKeyboardButton("➕ Выдать подписку", callback_data='admin_give')],
        [InlineKeyboardButton("📢 Рассылка", callback_data='admin_broadcast')],
        [InlineKeyboardButton("⏰ Скоро истекают", callback_data='admin_expiring')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🔐 Админ-панель\n\nВыберите действие:",
        reply_markup=reply_markup
    )

async def give_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Доступ запрещен.")
        return
    
    args = context.args
    if len(args) < 2:
        await update.message.reply_text(
            "❌ Использование: /give ID_пользователя Дней\n"
            "Пример: /give 123456789 30"
        )
        return
    
    try:
        user_id = int(args[0])
        days = int(args[1])
    except ValueError:
        await update.message.reply_text("❌ ID и дни должны быть числами")
        return
    
    activate_subscription(user_id, days)
    clear_cache(user_id)
    
    await update.message.reply_text(
        f"✅ Пользователю {user_id} выдана подписка на {days} дней."
    )
    
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=(
                f"✅ <b>Подписка активирована!</b>\n\n"
                f"📅 Срок действия: {days} дней\n"
                f"🔔 Теперь вы будете получать уведомления об отключениях на Базайской.\n\n"
                f"📱 Статус обновлён! Используйте /status для проверки."
            ),
            parse_mode='HTML'
        )
    except Exception as e:
        print(f"Ошибка отправки пользователю: {e}")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    
    users = get_all_users()
    active = get_active_users()
    
    await update.message.reply_text(
        f"📊 Статистика:\n\n"
        f"👥 Всего пользователей: {len(users)}\n"
        f"✅ Активных подписок: {len(active)}"
    )

async def expiring(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    
    expiring_users = get_expiring_soon(3)
    
    if not expiring_users:
        await update.message.reply_text("✅ Нет пользователей с истекающей подпиской.")
        return
    
    msg = "⏰ Скоро истекает подписка (3 дня):\n\n"
    for user in expiring_users:
        msg += f"👤 {user[1] or user[0]} (ID: {user[0]})\n"
        msg += f"📅 До: {user[2]}\n\n"
    
    await update.message.reply_text(msg)

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    
    message_text = ' '.join(context.args)
    if not message_text:
        await update.message.reply_text(
            "❌ Использование: /broadcast Текст сообщения"
        )
        return
    
    users = get_all_users()
    sent = 0
    failed = 0
    
    for user in users:
        try:
            await context.bot.send_message(
                chat_id=user[0],
                text=f"📢 Уведомление:\n\n{message_text}"
            )
            sent += 1
        except Exception:
            failed += 1
    
    await update.message.reply_text(
        f"✅ Рассылка завершена:\n"
        f"📤 Отправлено: {sent}\n"
        f"❌ Ошибок: {failed}"
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'admin_stats':
        users = get_all_users()
        active = get_active_users()
        await query.edit_message_text(
            f"📊 Статистика:\n\n"
            f"👥 Всего пользователей: {len(users)}\n"
            f"✅ Активных подписок: {len(active)}"
        )
    elif query.data == 'admin_users':
        users = get_all_users()
        if not users:
            await query.edit_message_text("👥 Пользователей пока нет")
            return
        msg = "👥 Все пользователи:\n\n"
        for user in users:
            msg += f"👤 {user[1] or user[0]}\n"
            msg += f"📅 Подписка до: {user[2] or 'Нет'}\n\n"
        await query.edit_message_text(msg[:4000])
    elif query.data == 'admin_give':
        await query.edit_message_text(
            "➕ Используй команду:\n"
            "/give ID_пользователя Дней\n\n"
            "Пример: /give 123456789 30"
        )
    elif query.data == 'admin_broadcast':
        await query.edit_message_text(
            "📢 Используй команду:\n"
            "/broadcast Текст сообщения"
        )
    elif query.data == 'admin_expiring':
        expiring_users = get_expiring_soon(3)
        if not expiring_users:
            await query.edit_message_text("✅ Нет пользователей с истекающей подпиской.")
            return
        msg = "⏰ Скоро истекает подписка (3 дня):\n\n"
        for user in expiring_users:
            msg += f"👤 {user[1] or user[0]} (ID: {user[0]})\n"
            msg += f"📅 До: {user[2]}\n\n"
        await query.edit_message_text(msg)