import os
import html
from loguru import logger
from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import Message
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ParseMode

from . import network
from . import storage

handlers_router = Router()
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


# States для FSM
class FillStates(StatesGroup):
    name = State()
    address = State()
    password = State()
    note = State()


async def start_command(message: Message) -> None:
    user = message.from_user
    logger.info(f"Команда /start от пользователя {user.id} ({user.username})")

    text = (
        "<b>Привет! Я — бот-помощник.</b>\n\n"
        "Я умею несколько команд. Ниже кратное описание и форматы данных, которые я принимаю.\n\n"
        "🔹 <b>/start</b> — это сообщение помощи (вы уже здесь).\n\n"
        "🔹 <b>/find_net номер_павильона</b> — найти информацию по номеру павильона.\n"
        "   Пример: <code>/find_net 122</code> или просто отправьте номер павильона как текст после команды.\n\n"
        "🔹 <b>/add_data</b> — добавить запись в базу данных. Отправьте JSON в одном сообщении в следующем формате:\n"
        "   <code>{\"pavilion\": \"122\", \"name\": \"Продавец\", \"note\": \"Комментарий\"}</code>\n"
        "   Поля нестрого обязательны — главное, чтобы сообщение было корректным JSON-объектом.\n\n"
        "Если у вас вопросы, используйте <code>/help</code> или просто напишите сообщение — я постараюсь помочь."
    )
    await message.answer(text, parse_mode=ParseMode.HTML)
    logger.debug("Ответ на /start отправлен")


async def network_command(message: Message) -> None:
    user = message.from_user
    logger.info(f"Команда /network от пользователя {user.id}")

    text = format_network_info()
    await message.answer(text, parse_mode=ParseMode.HTML)
    logger.debug("Сетевой отчет отправлен")


async def wifiprofiles_command(message: Message) -> None:
    user = message.from_user
    logger.info(f"Команда /wifiprofiles от пользователя {user.id}")

    profiles = network.list_wifi_profiles()
    if not profiles:
        logger.warning("WiFi профили не найдены")
        await message.answer("<i>Сохранённых Wi‑Fi профилей не найдено.</i>", parse_mode=ParseMode.HTML)
        return

    logger.info(f"Найдено {len(profiles)} WiFi профилей")
    lines = ["<b>Сохранённые Wi‑Fi профили:</b>"]
    for p in profiles:
        lines.append(f"• <code>{html.escape(p)}</code>")
    lines.append("\nИспользуйте: <code>/wifipass имя_профиля</code>")
    
    await message.answer("\n".join(lines), parse_mode=ParseMode.HTML)
    logger.debug("Список WiFi профилей отправлен")


async def wifipass_command(message: Message, command: CommandObject) -> None:
    user = message.from_user
    args = command.args
    
    logger.info(f"Команда /wifipass от пользователя {user.id} с аргументами: {args}")
    
    if not args:
        logger.warning("Не указано имя профиля для /wifipass")
        await message.answer("Использование: <code>/wifipass имя_профиля</code>", parse_mode=ParseMode.HTML)
        return
    
    profile = args.strip()
    logger.debug(f"Поиск пароля для профиля: {profile}")
    
    pwd = network.get_wifi_password(profile)
    if pwd:
        logger.info(f"Пароль для профиля '{profile}' найден")
        await message.answer(f"<b>Пароль для</b> <code>{html.escape(profile)}</code>:\n<code>{html.escape(pwd)}</code>", parse_mode=ParseMode.HTML)
    else:
        logger.warning(f"Пароль для профиля '{profile}' не найден или недоступен")
        await message.answer(f"Не удалось найти пароль для <code>{html.escape(profile)}</code> (или отсутствуют права).", parse_mode=ParseMode.HTML)


async def wifipass_all_command(message: Message) -> None:
    user = message.from_user
    logger.info(f"Команда /wifipass_all от пользователя {user.id}")
    
    profiles = network.list_wifi_profiles()
    if not profiles:
        logger.warning("WiFi профили не найдены для /wifipass_all")
        await message.answer("<i>Сохранённых Wi‑Fi профилей не найдено.</i>", parse_mode=ParseMode.HTML)
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
    
    await message.answer("\n".join(lines), parse_mode=ParseMode.HTML)
    logger.info("Все пароли WiFi отправлены")


async def fill_start(message: Message, state: FSMContext):
    user = message.from_user
    logger.info(f"Начало заполнения таблицы пользователем {user.id}")
    
    await message.answer("<b>Заполнение записи.</b> Введите имя сети (SSID) или отправьте /skip, чтобы пропустить.", parse_mode=ParseMode.HTML)
    await state.set_state(FillStates.name)
    await state.update_data({})


async def fill_name(message: Message, state: FSMContext):
    user = message.from_user
    text = message.text.strip() if message.text else ""
    
    await state.update_data({'name': text or "Отсутствует"})
    logger.info(f"Пользователь {user.id} ввел имя: {text}")
    
    await message.answer("Введите адрес (IP) или отправьте /skip, чтобы пропустить.", parse_mode=ParseMode.HTML)
    await state.set_state(FillStates.address)


async def fill_address(message: Message, state: FSMContext):
    user = message.from_user
    text = message.text.strip() if message.text else ""
    
    await state.update_data({'address': text or "Отсутствует"})
    logger.info(f"Пользователь {user.id} ввел адрес: {text}")
    
    await message.answer("Введите пароль (если есть) или отправьте /skip.", parse_mode=ParseMode.HTML)
    await state.set_state(FillStates.password)


async def fill_password(message: Message, state: FSMContext):
    user = message.from_user
    text = message.text.strip() if message.text else ""
    
    await state.update_data({'password': text or "Отсутствует"})
    logger.info(f"Пользователь {user.id} ввел пароль: {'*' * len(text) if text else 'Отсутствует'}")
    
    await message.answer("Введите примечание или отправьте /skip.", parse_mode=ParseMode.HTML)
    await state.set_state(FillStates.note)


async def fill_note(message: Message, state: FSMContext):
    user = message.from_user
    text = message.text.strip() if message.text else ""
    
    data = await state.get_data()
    data['note'] = text or "Отсутствует"
    
    logger.info(f"Пользователь {user.id} ввел примечание: {text}")
    storage.save_row(os.path.dirname(__file__), data)
    logger.info(f"Запись сохранена в таблицу для пользователя {user.id}")
    
    await message.answer("Запись сохранена в таблицу.", parse_mode=ParseMode.HTML)
    await state.clear()


async def skip_field(message: Message, state: FSMContext):
    user = message.from_user
    current_state = await state.get_state()
    data = await state.get_data()
    
    if current_state == FillStates.name.state:
        data['name'] = "Отсутствует"
        logger.info(f"Пользователь {user.id} пропустил ввод имени")
        await message.answer("Пропущено. Введите адрес (IP) или /skip.", parse_mode=ParseMode.HTML)
        await state.set_state(FillStates.address)
        
    elif current_state == FillStates.address.state:
        data['address'] = "Отсутствует"
        logger.info(f"Пользователь {user.id} пропустил ввод адреса")
        await message.answer("Пропущено. Введите пароль или /skip.", parse_mode=ParseMode.HTML)
        await state.set_state(FillStates.password)
        
    elif current_state == FillStates.password.state:
        data['password'] = "Отсутствует"
        logger.info(f"Пользователь {user.id} пропустил ввод пароля")
        await message.answer("Пропущено. Введите примечание или /skip.", parse_mode=ParseMode.HTML)
        await state.set_state(FillStates.note)
        
    elif current_state == FillStates.note.state:
        data['note'] = "Отсутствует"
        storage.save_row(os.path.dirname(__file__), data)
        logger.info(f"Запись сохранена с пропущенными полями для пользователя {user.id}")
        await message.answer("Запись сохранена в таблицу.", parse_mode=ParseMode.HTML)
        await state.clear()
    
    await state.update_data(data)


async def cancel_fill(message: Message, state: FSMContext):
    user = message.from_user
    logger.info(f"Пользователь {user.id} отменил заполнение таблицы")
    
    await message.answer("Заполнение отменено.", parse_mode=ParseMode.HTML)
    await state.clear()


async def showtable_command(message: Message):
    user = message.from_user
    logger.info(f"Команда /showtable от пользователя {user.id}")
    
    rows = storage.load_table(os.path.dirname(__file__))
    if not rows:
        logger.warning("Таблица пуста")
        await message.answer("<i>Таблица пуста.</i>", parse_mode=ParseMode.HTML)
        return
    
    logger.info(f"Загружено {len(rows)} записей из таблицы")
    lines = ["<b>Таблица записей:</b>"]
    for i, r in enumerate(rows, 1):
        lines.append(f"{i}. SSID: <code>{html.escape(r.get('name','Отсутствует'))}</code> | IP: <code>{html.escape(r.get('address','Отсутствует'))}</code> | Пароль: <code>{html.escape(r.get('password','Отсутствует'))}</code> | Прим: <code>{html.escape(r.get('note','Отсутствует'))}</code>")
    
    await message.answer("\n".join(lines), parse_mode=ParseMode.HTML)
    logger.debug("Таблица отправлена пользователю")


def setup_handlers(dp: Dispatcher) -> None:
    logger.info("Настройка обработчиков aiogram")
    
    # Basic commands
    dp.message.register(start_command, Command("start"))
    dp.message.register(network_command, Command("network"))
    dp.message.register(wifiprofiles_command, Command("wifiprofiles"))
    dp.message.register(wifipass_command, Command("wifipass"))
    dp.message.register(wifipass_all_command, Command("wifipass_all"))
    dp.message.register(showtable_command, Command("showtable"))
    
    # FSM handlers
    dp.message.register(fill_start, Command("fill"))
    dp.message.register(cancel_fill, Command("cancel"))
    dp.message.register(skip_field, Command("skip"))
    
    dp.message.register(fill_name, FillStates.name, F.text)
    dp.message.register(fill_address, FillStates.address, F.text)
    dp.message.register(fill_password, FillStates.password, F.text)
    dp.message.register(fill_note, FillStates.note, F.text)
    
    logger.success("Обработчики aiogram настроены успешно")


def build_application(token: str) -> tuple[Bot, Dispatcher]:
    logger.info("Создание aiogram бота и диспетчера")
    
    bot = Bot(token=token)
    dp = Dispatcher()
    
    setup_handlers(dp)
    
    logger.success("Aiogram бот и диспетчер созданы успешно")
    return bot, dp