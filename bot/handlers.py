"""Telegram bot handlers for TheBestBot.

This module exposes async handlers for the main bot commands and a
`build_application(token)` helper that registers them on a `telegram.ext.Application`.

Handlers provided:
- /start - greeting and help text
- /find_net <pavilion> - look up pavilion data (uses `database.Database` if available)
- /add_data - accept a single JSON object message and store it (deduplicated)
- plus the existing network and wifi helpers which are preserved.

The implementation keeps dependencies minimal and uses HTML-formatted replies.
"""

from __future__ import annotations

import os
import html
import json
import logging
from typing import Any, Dict, List, Optional

from telegram import Update, Message
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from . import network, storage

try:
    from database import Database
except Exception:
    Database = None  # type: ignore

LOG = logging.getLogger(__name__)


def _safe_reply_html(msg: Message, text: str) -> None:
    """Send an HTML-formatted reply; catch and log exceptions."""
    try:
        # reply_html is a coroutine so callers should await. This helper is
        # intended to be used within async handlers where `await` is used.
        return msg.reply_html(text)
    except Exception:
        LOG.exception("Ошибка при отправке сообщения пользователю")


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    LOG.info("/start from %s", getattr(user, "id", "unknown"))

    text = (
        "<b>Привет! Я — бот-помощник TheBestBot.</b>\n\n"
        "Я могу помочь с поиском павильонов и сохранением данных.\n\n"
        "<b>Доступные команды</b>:\n"
        "• <code>/start</code> — показать это сообщение.\n"
        "• <code>/find_net &lt;номер_павильона&gt;</code> — найти записи по павильону.\n"
        "• <code>/add_data</code> — добавляет JSON-объект, отправьте один корректный JSON в сообщении.\n"
        "\nФормат JSON: <code>{\"pavilion\": \"A12\", \"name\": \"Продавец\", \"note\": \"Примечание\"}</code>\n"
        "Поля необязательны, главное — корректный JSON-объект.\n"
        "Если нужно — отправьте просто номер павильона и я попробую найти совпадения."
    )
    if update.message:
        await update.message.reply_html(text)


async def find_net_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Find records by pavilion. If a DB is available, query it; otherwise use CSV storage."""
    user = update.effective_user
    args = context.args
    LOG.info("/find_net from %s args=%s", getattr(user, "id", "?"), args)

    if not args and update.message and update.message.reply_to_message and update.message.reply_to_message.text:
        # allow replying to a message that contains the pavilion
        query = update.message.reply_to_message.text.strip()
    else:
        query = " ".join(args).strip()

    if not query:
        await update.message.reply_html("Использование: <code>/find_net номер_павильона</code>")
        return

    pavilion = query
    results: List[Dict[str, Any]] = []

    # Prefer Database if available
    if Database is not None:
        try:
            db = Database()
            db.connect()
            results = db.find_by_pavilion(pavilion)
            db.close()
        except Exception:
            LOG.exception("Ошибка при обращении к базе данных, попытаемся загрузить CSV")

    if not results:
        # Fallback to CSV table storage
        rows = storage.load_table(os.path.dirname(__file__))
        for r in rows:
            if r.get("name") == pavilion or r.get("pavilion") == pavilion or r.get("address") == pavilion:
                results.append(r)

    if not results:
        await update.message.reply_html(f"Ничего не найдено для: <code>{html.escape(pavilion)}</code>")
        return

    lines = [f"<b>Результаты поиска для</b> <code>{html.escape(pavilion)}</code>:"]
    for r in results:
        try:
            name = html.escape(str(r.get("name") or r.get("pavilion") or "-"))
            addr = html.escape(str(r.get("address") or "-"))
            note = html.escape(str(r.get("note") or "-"))
            lines.append(f"• {name} — IP: <code>{addr}</code> — Прим: <code>{note}</code>")
        except Exception:
            LOG.exception("Ошибка при форматировании строки результата")
    await update.message.reply_html("\n".join(lines))


async def add_data_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Accept a single JSON object (in the same message) and store it.

    Usage: send `/add_data` followed by a JSON object in the same message, or
    send `/add_data` and then the bot will prompt for the JSON in the next
    message (current implementation expects the JSON in the same message).
    """
    user = update.effective_user
    LOG.info("/add_data from %s", getattr(user, "id", "?"))

    text = "".join(context.args) if context.args else (update.message.text or "")

    # If user sent just '/add_data' without JSON, ask for it
    # For simplicity we expect JSON in the same message after the command.
    # Example: /add_data {"pavilion":"A1","name":"Seller"}
    try:
        # extract JSON substring after the command if present
        if text.strip().startswith("/add_data"):
            # remove the command itself
            payload = text.replace("/add_data", "", 1).strip()
        else:
            payload = text.strip()

        if not payload and update.message and update.message.caption:
            payload = update.message.caption.strip()

        if not payload:
            await update.message.reply_html("Отправьте JSON-объект в том же сообщении: <code>{\"pavilion\": \"A1\"}</code>")
            return

        obj = json.loads(payload)
        if not isinstance(obj, dict):
            await update.message.reply_html("Ожидается JSON-объект (словарь).")
            return

    except json.JSONDecodeError as e:
        LOG.warning("Неверный JSON: %s", e)
        await update.message.reply_html(f"Ошибка разбора JSON: {html.escape(str(e))}")
        return

    # Save to DB if available, otherwise to CSV via storage
    saved_id: Optional[int] = None
    if Database is not None:
        try:
            db = Database()
            db.connect()
            saved_id = db.add_record(obj)
            db.close()
        except Exception:
            LOG.exception("Ошибка при сохранении в базу; упадём back to CSV")

    if saved_id is None:
        try:
            storage.save_row(os.path.dirname(__file__), obj)
            await update.message.reply_html("Данные сохранены (CSV fallback).")
            return
        except Exception:
            LOG.exception("Не удалось сохранить данные ни в базу, ни в CSV")
            await update.message.reply_html("Не удалось сохранить данные: внутренняя ошибка.")
            return

    await update.message.reply_html(f"Данные сохранены с id={saved_id}.")


def build_application(token: str) -> Application:
    LOG.info("Создание Telegram Application (handlers)")

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("find_net", find_net_command))
    app.add_handler(CommandHandler("add_data", add_data_command))

    # Preserve legacy network/wifi helpers if present in network module
    if hasattr(network, "get_wifi_ssid"):
        async def network_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
            text = network.get_wifi_report() if hasattr(network, "get_wifi_report") else network.get_wifi_ssid()
            await update.message.reply_html(html.escape(str(text)))

        try:
            app.add_handler(CommandHandler("network", network_cmd))
        except Exception:
            LOG.debug("Не удалось добавить network handler")

    # Also add showtable using storage.load_table
    async def showtable(update: Update, context: ContextTypes.DEFAULT_TYPE):
        rows = storage.load_table(os.path.dirname(__file__))
        if not rows:
            await update.message.reply_html("<i>Таблица пуста.</i>")
            return
        lines = ["<b>Таблица записей:</b>"]
        for i, r in enumerate(rows, 1):
            name = html.escape(str(r.get("name", "Отсутствует")))
            addr = html.escape(str(r.get("address", "Отсутствует")))
            pwd = html.escape(str(r.get("password", "Отсутствует")))
            note = html.escape(str(r.get("note", "Отсутствует")))
            lines.append(f"{i}. SSID: <code>{name}</code> | IP: <code>{addr}</code> | Пароль: <code>{pwd}</code> | Прим: <code>{note}</code>")
        await update.message.reply_html("\n".join(lines))

    app.add_handler(CommandHandler("showtable", showtable))

    LOG.info("Handlers registered")
    return app
import os
import html
from loguru import logger
from telegram import Update
from telegram.ext import (
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
    Application,
)

from . import network
from . import storage

# Настройка логирования для этого модуля
logger = logger.bind(module="bot_handlers")


def format_network_info() -> str:
    logger.debug("Формирование сетевой информации")
    ssid = network.get_wifi_ssid()
    ip, gw = network.parse_ipconfig_for_gateway_and_ip()
    local_ip = network.get_local_ip()

    lines = ["<b>Сетевой отчёт</b>", ""]
    if ssid:
        lines.append(f"🔸 <b>Имя сети (SSID):</b> <code>{html.escape(ssid)}</code>")
        logger.debug(f"SSID найден: {ssid}")
    else:
        lines.append("🔸 <b>Имя сети (SSID):</b> <i>Не подключено / не найдено</i>")
        logger.warning("SSID не найден")

    if ip:
        lines.append(f"🔹 <b>Локальный IP (adapter):</b> <code>{html.escape(ip)}</code>")
        logger.debug(f"IP адаптера найден: {ip}")
    else:
        lines.append("🔹 <b>Локальный IP (adapter):</b> <i>Не найден</i>")
        logger.warning("IP адаптера не найден")

    lines.append(f"🔹 <b>Определённый IP (метод UDP):</b> <code>{html.escape(local_ip)}</code>")
    logger.debug(f"Локальный IP (UDP): {local_ip}")

    if gw:
        lines.append(f"🔸 <b>Шлюз (Default Gateway):</b> <code>{html.escape(gw)}</code>")
        logger.debug(f"Шлюз найден: {gw}")
    else:
        lines.append("🔸 <b>Шлюз (Default Gateway):</b> <i>Не найден</i>")
        logger.warning("Шлюз не найден")

    lines.append("")
    lines.append("Чтобы посмотреть сохранённые Wi‑Fi профили используйте: <code>/wifiprofiles</code>")
    lines.append("Чтобы увидеть пароль профиля: <code>/wifipass имя_профиля</code>")
    lines.append("Внимание: отображение паролей требует прав и доступно только на локальной машине.")
    
    logger.info("Сетевая информация сформирована")
    return "\n".join(lines)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    logger.info(f"Команда /start от пользователя {user.id} ({user.username})")
    
    text = (
        "<b>Привет! Я — бот-помощник.</b>\n\n"
        "Я умею несколько команд. Ниже краткое описание и форматы данных, которые я принимаю.\n\n"
        "🔹 <b>/start</b> — это сообщение помощи (вы уже здесь).\n\n"
        "🔹 <b>/find_net номер_павильона</b> — найти информацию по номеру павильона.\n"
        "   Пример: <code>/find_net A12</code> или просто отправьте номер павильона как текст после команды.\n\n"
        "🔹 <b>/add_data</b> — добавить запись в базу данных. Отправьте JSON в одном сообщении в следующем формате:\n"
        "   <code>{\"pavilion\": \"A12\", \"name\": \"Продавец\", \"note\": \"Комментарий\"}</code>\n"
        "   Поля нестрого обязательны — главное, чтобы сообщение было корректным JSON-объектом.\n\n"
        "Если у вас вопросы, используйте <code>/help</code> или просто напишите сообщение — я постараюсь помочь."
    )
    # Use reply_html to keep existing behaviour (HTML formatting)
    await update.message.reply_html(text)
    logger.debug("Ответ на /start отправлен")


async def network_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    logger.info(f"Команда /network от пользователя {user.id}")
    
    text = format_network_info()
    await update.message.reply_html(text)
    logger.debug("Сетевой отчет отправлен")


async def wifiprofiles_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    logger.info(f"Команда /wifiprofiles от пользователя {user.id}")
    
    profiles = network.list_wifi_profiles()
    if not profiles:
        logger.warning("WiFi профили не найдены")
        await update.message.reply_html("<i>Сохранённых Wi‑Fi профилей не найдено.</i>")
        return
    
    logger.info(f"Найдено {len(profiles)} WiFi профилей")
    lines = ["<b>Сохранённые Wi‑Fi профили:</b>"]
    for p in profiles:
        lines.append(f"• <code>{html.escape(p)}</code>")
    lines.append("\nИспользуйте: <code>/wifipass имя_профиля</code>")
    
    await update.message.reply_html("\n".join(lines))
    logger.debug("Список WiFi профилей отправлен")


async def wifipass_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    args = context.args
    
    logger.info(f"Команда /wifipass от пользователя {user.id} с аргументами: {args}")
    
    if not args:
        logger.warning("Не указано имя профиля для /wifipass")
        await update.message.reply_html("Использование: <code>/wifipass имя_профиля</code>")
        return
    
    profile = " ".join(args)
    logger.debug(f"Поиск пароля для профиля: {profile}")
    
    pwd = network.get_wifi_password(profile)
    if pwd:
        logger.info(f"Пароль для профиля '{profile}' найден")
        await update.message.reply_html(f"<b>Пароль для</b> <code>{html.escape(profile)}</code>:\n<code>{html.escape(pwd)}</code>")
    else:
        logger.warning(f"Пароль для профиля '{profile}' не найден или недоступен")
        await update.message.reply_html(f"Не удалось найти пароль для <code>{html.escape(profile)}</code> (или отсутствуют права).")


async def wifipass_all_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    logger.info(f"Команда /wifipass_all от пользователя {user.id}")
    
    profiles = network.list_wifi_profiles()
    if not profiles:
        logger.warning("WiFi профили не найдены для /wifipass_all")
        await update.message.reply_html("<i>Сохранённых Wi‑Fi профилей не найдено.</i>")
        return
    
    logger.info(f"Поиск паролей для {len(profiles)} профилей")
    lines = ["<b>Пароли Wi‑Fi (если доступны):</b>"]
    
    for p in profiles:
        pwd = network.get_wifi_password(p) or "<i>Не найден / закрыт</i>"
        lines.append(f"• <code>{html.escape(p)}</code>: <code>{html.escape(pwd)}</code>")
        if pwd and pwd != "<i>Не найден / закрыт</i>":
            logger.debug(f"Пароль для '{p}' найден")
        else:
            logger.debug(f"Пароль для '{p}' не найден")
    
    await update.message.reply_html("\n".join(lines))
    logger.info("Все пароли WiFi отправлены")


def build_application(token: str) -> Application:
    logger.info("Создание Telegram Application")
    
    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("network", network_command))
    app.add_handler(CommandHandler("wifiprofiles", wifiprofiles_command))
    app.add_handler(CommandHandler("wifipass", wifipass_command))
    app.add_handler(CommandHandler("wifipass_all", wifipass_all_command))

    # Table conversation
    NAME, ADDRESS, PASSWORD, NOTE = range(4)


    async def fill_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        logger.info(f"Начало заполнения таблицы пользователем {user.id}")
        
        await update.message.reply_html("<b>Заполнение записи.</b> Введите имя сети (SSID) или отправьте /skip, чтобы пропустить.")
        return NAME


    async def fill_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        text = update.message.text.strip() if update.message and update.message.text else ""
        context.user_data['name'] = text or "Отсутствует"
        
        logger.info(f"Пользователь {user.id} ввел имя: {text}")
        await update.message.reply_html("Введите адрес (IP) или отправьте /skip, чтобы пропустить.")
        return ADDRESS


    async def fill_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        text = update.message.text.strip() if update.message and update.message.text else ""
        context.user_data['address'] = text or "Отсутствует"
        
        logger.info(f"Пользователь {user.id} ввел адрес: {text}")
        await update.message.reply_html("Введите пароль (если есть) или отправьте /skip.")
        return PASSWORD


    async def fill_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        text = update.message.text.strip() if update.message and update.message.text else ""
        context.user_data['password'] = text or "Отсутствует"
        
        logger.info(f"Пользователь {user.id} ввел пароль: {'*' * len(text) if text else 'Отсутствует'}")
        await update.message.reply_html("Введите примечание или отправьте /skip.")
        return NOTE


    async def fill_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        text = update.message.text.strip() if update.message and update.message.text else ""
        context.user_data['note'] = text or "Отсутствует"
        
        logger.info(f"Пользователь {user.id} ввел примечание: {text}")
        storage.save_row(os.path.dirname(__file__), context.user_data)
        logger.info(f"Запись сохранена в таблицу для пользователя {user.id}")
        
        await update.message.reply_html("Запись сохранена в таблицу.")
        return ConversationHandler.END


    async def skip_field(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        current_state = await context.application.persistence.get_conversation(update.effective_chat.id, update.effective_user.id)
        
        if 'name' not in context.user_data:
            context.user_data['name'] = "Отсутствует"
            logger.info(f"Пользователь {user.id} пропустил ввод имени")
            await update.message.reply_html("Пропущено. Введите адрес (IP) или /skip.")
            return ADDRESS
        if 'address' not in context.user_data:
            context.user_data['address'] = "Отсутствует"
            logger.info(f"Пользователь {user.id} пропустил ввод адреса")
            await update.message.reply_html("Пропущено. Введите пароль или /skip.")
            return PASSWORD
        if 'password' not in context.user_data:
            context.user_data['password'] = "Отсутствует"
            logger.info(f"Пользователь {user.id} пропустил ввод пароля")
            await update.message.reply_html("Пропущено. Введите примечание или /skip.")
            return NOTE
        
        context.user_data['note'] = "Отсутствует"
        storage.save_row(os.path.dirname(__file__), context.user_data)
        logger.info(f"Запись сохранена с пропущенными полями для пользователя {user.id}")
        
        await update.message.reply_html("Запись сохранена в таблицу.")
        return ConversationHandler.END


    async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        logger.info(f"Пользователь {user.id} отменил заполнение таблицы")
        
        await update.message.reply_html("Заполнение отменено.")
        return ConversationHandler.END


    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('fill', fill_start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, fill_name), CommandHandler('skip', skip_field)],
            ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, fill_address), CommandHandler('skip', skip_field)],
            PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, fill_password), CommandHandler('skip', skip_field)],
            NOTE: [MessageHandler(filters.TEXT & ~filters.COMMAND, fill_note), CommandHandler('skip', skip_field)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    app.add_handler(conv_handler)


    async def showtable(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        logger.info(f"Команда /showtable от пользователя {user.id}")
        
        rows = storage.load_table(os.path.dirname(__file__))
        if not rows:
            logger.warning("Таблица пуста")
            await update.message.reply_html("<i>Таблица пуста.</i>")
            return
        
        logger.info(f"Загружено {len(rows)} записей из таблицы")
        lines = ["<b>Таблица записей:</b>"]
        for i, r in enumerate(rows, 1):
            lines.append(f"{i}. SSID: <code>{html.escape(r.get('name','Отсутствует'))}</code> | IP: <code>{html.escape(r.get('address','Отсутствует'))}</code> | Пароль: <code>{html.escape(r.get('password','Отсутствует'))}</code> | Прим: <code>{html.escape(r.get('note','Отсутствует'))}</code>")
        
        await update.message.reply_html("\n".join(lines))
        logger.debug("Таблица отправлена пользователю")

    app.add_handler(CommandHandler('showtable', showtable))

    logger.success("Telegram Application создано успешно")
    return app
