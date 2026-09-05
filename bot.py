"""
Демо-бот для записи клиентов + FAQ.
Подходит для: кафе, стоматологий, репетиторских центров, автосервисов и т.п.

Что умеет:
  /start   — приветствие и главное меню
  Кнопка "Записаться" — пошаговая запись (имя, услуга, дата/время, телефон)
  Кнопка "Вопросы (FAQ)" — быстрые ответы на частые вопросы
  Кнопка "Мои записи" — показать последнюю запись пользователя
  Уведомление владельцу бизнеса о новой записи (через OWNER_CHAT_ID)

Как запустить:
  1. Создать бота через @BotFather в Telegram, получить токен.
  2. Установить библиотеку:  pip install python-telegram-bot --break-system-packages
  3. Вписать токен в переменную BOT_TOKEN ниже (или через переменную окружения BOT_TOKEN).
  4. Вписать свой OWNER_CHAT_ID (узнать свой chat_id можно у бота @userinfobot).
  5. Запустить:  python bot.py

Хранение данных — в памяти (для демо). Для реального использования
подключить базу данных (SQLite/Postgres) — легко расширяется.
"""

import os
import logging
from datetime import datetime

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    ConversationHandler,
    filters,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ------------------------- НАСТРОЙКИ (измени под свой бизнес) -------------------------

BOT_TOKEN = os.environ.get("BOT_TOKEN", "ВСТАВЬ_СЮДА_ТОКЕН_ОТ_BOTFATHER")
OWNER_CHAT_ID = os.environ.get("OWNER_CHAT_ID", "")  # твой chat_id для уведомлений о новых записях

BUSINESS_NAME = "Демо-бизнес"

SERVICES = [
    "Консультация",
    "Услуга 1",
    "Услуга 2",
    "Услуга 3",
]

FAQ = {
    "Часы работы": "Мы работаем ежедневно с 9:00 до 20:00, без выходных.",
    "Адрес": "г. Ташкент, ул. Примерная, 1 (вставь реальный адрес).",
    "Способы оплаты": "Наличные, карта, перевод.",
    "Как отменить запись": "Напишите нам в этот же чат минимум за 2 часа до визита.",
}

# ------------------------- Состояния диалога записи -------------------------

CHOOSING_SERVICE, ENTERING_DATE, ENTERING_PHONE = range(3)

# Простое "хранилище" записей в памяти (для демо)
bookings = {}


# ------------------------- Главное меню -------------------------

def main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("📅 Записаться", callback_data="book_start")],
        [InlineKeyboardButton("❓ Вопросы (FAQ)", callback_data="faq_menu")],
        [InlineKeyboardButton("📋 Мои записи", callback_data="my_bookings")],
    ]
    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        f"Здравствуйте! Это бот записи «{BUSINESS_NAME}».\n\n"
        "Выберите действие:"
    )
    if update.message:
        await update.message.reply_text(text, reply_markup=main_menu_keyboard())
    else:
        await update.callback_query.edit_message_text(text, reply_markup=main_menu_keyboard())


async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await start(update, context)
    return ConversationHandler.END


# ------------------------- FAQ -------------------------

async def faq_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [[InlineKeyboardButton(q, callback_data=f"faq_{q}")] for q in FAQ]
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="menu_back")])
    await query.edit_message_text("Часто задаваемые вопросы:", reply_markup=InlineKeyboardMarkup(keyboard))


async def faq_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    question = query.data.replace("faq_", "")
    answer = FAQ.get(question, "Ответ не найден.")
    keyboard = [[InlineKeyboardButton("⬅️ Назад к вопросам", callback_data="faq_menu")]]
    await query.edit_message_text(f"❓ {question}\n\n{answer}", reply_markup=InlineKeyboardMarkup(keyboard))


# ------------------------- Мои записи -------------------------

async def my_bookings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    booking = bookings.get(user_id)
    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="menu_back")]]
    if booking:
        text = (
            "Ваша последняя запись:\n\n"
            f"Услуга: {booking['service']}\n"
            f"Дата/время: {booking['date']}\n"
            f"Телефон: {booking['phone']}"
        )
    else:
        text = "У вас пока нет активных записей."
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


# ------------------------- Процесс записи (ConversationHandler) -------------------------

async def book_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [[InlineKeyboardButton(s, callback_data=f"svc_{s}")] for s in SERVICES]
    keyboard.append([InlineKeyboardButton("⬅️ Отмена", callback_data="menu_back")])
    await query.edit_message_text("Выберите услугу:", reply_markup=InlineKeyboardMarkup(keyboard))
    return CHOOSING_SERVICE


async def service_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    service = query.data.replace("svc_", "")
    context.user_data["service"] = service
    await query.edit_message_text(
        f"Услуга: {service}\n\nВведите желаемую дату и время (например: 12.09 в 15:00):"
    )
    return ENTERING_DATE


async def date_entered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["date"] = update.message.text
    await update.message.reply_text("Отлично! Теперь введите номер телефона для связи:")
    return ENTERING_PHONE


async def phone_entered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.text
    user = update.message.from_user
    service = context.user_data.get("service")
    date = context.user_data.get("date")

    bookings[user.id] = {"service": service, "date": date, "phone": phone}

    await update.message.reply_text(
        "✅ Запись создана!\n\n"
        f"Услуга: {service}\n"
        f"Дата/время: {date}\n"
        f"Телефон: {phone}\n\n"
        "Мы свяжемся с вами для подтверждения.",
        reply_markup=main_menu_keyboard(),
    )

    # Уведомление владельцу бизнеса
    if OWNER_CHAT_ID:
        try:
            await context.bot.send_message(
                chat_id=OWNER_CHAT_ID,
                text=(
                    "🔔 Новая запись!\n\n"
                    f"Клиент: {user.first_name} (@{user.username})\n"
                    f"Услуга: {service}\n"
                    f"Дата/время: {date}\n"
                    f"Телефон: {phone}\n"
                    f"Время создания: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
                ),
            )
        except Exception as e:
            logger.warning(f"Не удалось отправить уведомление владельцу: {e}")

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Запись отменена.", reply_markup=main_menu_keyboard())
    return ConversationHandler.END


# ------------------------- Сборка приложения -------------------------

def main():
    if BOT_TOKEN == "ВСТАВЬ_СЮДА_ТОКЕН_ОТ_BOTFATHER":
        print("⚠️  Сначала вставь токен бота в BOT_TOKEN (или переменную окружения BOT_TOKEN).")
        return

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    booking_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(book_start, pattern="^book_start$")],
        states={
            CHOOSING_SERVICE: [CallbackQueryHandler(service_chosen, pattern="^svc_")],
            ENTERING_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, date_entered)],
            ENTERING_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, phone_entered)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(booking_conv)
    app.add_handler(CallbackQueryHandler(faq_menu, pattern="^faq_menu$"))
    app.add_handler(CallbackQueryHandler(my_bookings, pattern="^my_bookings$"))
    app.add_handler(CallbackQueryHandler(back_to_menu, pattern="^menu_back$"))
    app.add_handler(CallbackQueryHandler(faq_answer, pattern="^faq_"))

    print("Бот запущен. Нажми Ctrl+C для остановки.")
    app.run_polling()


if __name__ == "__main__":
    main()
