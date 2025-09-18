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
        "<b>Привет! Я — маленький помощник сети.</b>\n\n"
        "Я могу показать текущий IP, имя Wi‑Fi сети, шлюз и помочь посмотреть сохранённые Wi‑Fi пароли.\n"
        "Используйте команды: <code>/network</code>, <code>/wifiprofiles</code>, <code>/wifipass</code>."
    )
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
