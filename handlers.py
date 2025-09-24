import logging
import textwrap
from typing import Any, Dict, List

from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from controler import Controller  # Импорт вашего Controller


# Логгер для модуля
logger = logging.getLogger(__name__)

# Создаём маршрутизатор
bot_router = Router()

# Инициализация Controller
controller = Controller()


def _truncate(value: str, length: int) -> str:
    """Короткая обёртка для безопасного усечения строк."""
    if value is None:
        return ""
    s = str(value)
    return s if len(s) <= length else s[: max(0, length - 1)] + "…"


def get_main_keyboard() -> InlineKeyboardMarkup:
    """Создаёт основную inline-клавиатуру для бота."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Таблица", callback_data="show_table"),
            InlineKeyboardButton(text="Начать новое заполнение", callback_data="new_entry"),
        ],
        [InlineKeyboardButton(text="Инструкция", callback_data="instructions")]
    ])
    return keyboard


def _format_records_table(records: List[Dict[str, Any]]) -> str:
    """Форматирует список записей в текстовую таблицу.

    Ожидаемый формат записи - словарь с ключами: ssid, bssid, frequency, rssi,
    channel_bandwidth, timestamp, capabilities.
    """
    header = (
        "📊 Таблица WiFi-сетей:\n\n"
        f"{'SSID':<20} {'BSSID':<18} {'Частота':<10} {'RSSI':<8} {'Канал':<10} {'Время':<15} {'Капабилити':<20}\n"
    )
    lines = [header, "-" * 100 + "\n"]

    for rec in records:
        ssid = _truncate(rec.get("ssid", ""), 19)
        bssid = _truncate(rec.get("bssid", ""), 17)
        frequency = _truncate(rec.get("frequency", ""), 10)
        rssi = _truncate(rec.get("rssi", ""), 8)
        channel = _truncate(rec.get("channel_bandwidth", ""), 10)
        timestamp = _truncate(rec.get("timestamp", ""), 15)
        capabilities = _truncate(rec.get("capabilities", ""), 19)

        lines.append(
            f"{ssid:<20} {bssid:<18} {frequency:<10} {rssi:<8} {channel:<10} {timestamp:<15} {capabilities:<20}\n"
        )

    return "".join(lines)


# Обработчик команды /start
@bot_router.message(Command("start"))
async def cmd_start(message: types.Message):
    welcome_text = (
        "Добро пожаловать в WiFi Data Bot! 🌐\n"
        "Я помогаю собирать и хранить данные о WiFi-сетях.\n"
        "Используйте кнопки ниже для работы с ботом:"
    )
    await message.answer(welcome_text, reply_markup=get_main_keyboard())


# Обработчик кнопки "Таблица"
@bot_router.callback_query(F.data == "show_table")
async def show_table(callback: types.CallbackQuery) -> None:
    """Отправляет пользователю текстовую таблицу со всеми записями.

    NOTE: контроллер должен предоставлять метод `db.read_all()` возвращающий
    список словарей-записей. Если этого метода нет, оставлен TODO.
    """
    try:
        records = controller.db.read_all()  # TODO: Реализуйте read_all() в WiFiDB, если его нет
    except Exception as exc:
        logger.exception("Failed to read records from DB")
        await callback.message.answer(f"Ошибка при получении таблицы: {exc}")
        await callback.answer()
        return

    if not records:
        await callback.message.answer("Таблица пуста. Добавьте данные через 'Начать новое заполнение'.")
        await callback.answer()
        return

    table_text = _format_records_table(records)
    await callback.message.answer(table_text, reply_markup=get_main_keyboard())
    await callback.answer()


# Обработчик кнопки "Начать новое заполнение"
@bot_router.callback_query(F.data == "new_entry")
async def start_new_entry(callback: types.CallbackQuery) -> None:
    """Просит пользователя прислать JSON с данными о WiFi-сети."""
    example = (
        '{"bssid": "00:11:22:33:44:55", "frequency": 2412, "rssi": -50, '
        '"ssid": "MyWiFi", "timestamp": 1698115200, "channel_bandwidth": "20MHz", '
        '"capabilities": "WPA2-PSK"}'
    )
    await callback.message.answer(
        "📝 Введите данные WiFi-сети в формате JSON, например:\n" + example
    )

    # В оригинальном коде использовалась установка кнопки меню — это не обязательно,
    # но оставляем попытку установить её безопасно, чтобы не ломать UX у некоторых клиентов.
    try:
        await callback.message.bot.set_chat_menu_button(
            chat_id=callback.message.chat.id,
            menu_button=types.MenuButtonCommands(),
        )
    except Exception:
        # Не фатальная ошибка — просто логируем
        logger.debug("Не удалось установить chat menu button", exc_info=True)

    await callback.answer()


# Обработчик текстового ввода для новой записи
@bot_router.message()
async def process_new_entry(message: types.Message) -> None:
    """Обрабатывает текстовое сообщение как JSON-пэйлоад и сохраняет сеть через Controller.

    В этой реализации мы явно парсим JSON и вызываем методы контроллера
    `parse_json`, `build_network`, `save_network` чтобы иметь контроль над ошибками
    и возвращаемым кодом.
    """
    payload_text = message.text or ""

    try:
        data = controller.parse_json(payload_text)
    except ValueError as ve:
        logger.debug("Invalid JSON received from user", exc_info=True)
        await message.answer(f"❌ Некорректный JSON: {ve}", reply_markup=get_main_keyboard())
        return

    try:
        network = controller.build_network(data)
    except (KeyError, TypeError, ValueError) as e:
        logger.debug("Invalid network data", exc_info=True)
        await message.answer(f"❌ Неверные данные сети: {e}", reply_markup=get_main_keyboard())
        return

    try:
        saved = controller.save_network(network)
    except Exception as e:
        logger.exception("DB error when saving network")
        await message.answer(f"❌ Ошибка при сохранении в БД: {e}", reply_markup=get_main_keyboard())
        return

    if saved:
        await message.answer("✅ Данные успешно сохранены в таблицу!", reply_markup=get_main_keyboard())
    else:
        await message.answer("❌ Не удалось сохранить данные в БД.", reply_markup=get_main_keyboard())


# Обработчик кнопки "Инструкция"
@bot_router.callback_query(F.data == "instructions")
async def show_instructions(callback: types.CallbackQuery) -> None:
    """Отправляет подробную инструкцию пользователю."""
    instructions = textwrap.dedent(
        """
        📚 *Инструкция по использованию WiFi Data Bot*

        Этот бот предназначен для сбора и хранения данных о WiFi-сетях.
        Вы можете добавлять данные о сетях, просматривать их в таблице и получать информацию о функционале.

        *Функционал бота:*
        - *Таблица*: Показывает все сохранённые данные о WiFi-сетях в формате таблицы.
        - *Начать новое заполнение*: Позволяет добавить новую WiFi-сеть, отправив данные в формате JSON.
        - *Инструкция*: Выводит это сообщение.

        *Как заполнить таблицу:*
        1. Нажмите 'Начать новое заполнение'.
        2. Отправьте данные в формате JSON, например:

           ```json
           {"bssid": "00:11:22:33:44:55", "frequency": 2412, "rssi": -50,
            "ssid": "MyWiFi", "timestamp": 1698115200, "channel_bandwidth": "20MHz",
            "capabilities": "WPA2-PSK"}
           ```

        3. Данные будут сохранены в базу и добавлены в таблицу.

        *Обозначения в таблице:*
        - *SSID*: Имя WiFi-сети.
        - *BSSID*: MAC-адрес точки доступа.
        - *Частота*: Частота в МГц (например, 2412 для 2.4 ГГц).
        - *RSSI*: Уровень сигнала в дБм (например, -50).
        - *Канал*: Ширина канала (например, 20MHz).
        - *Время*: Время обнаружения (Unix timestamp).
        - *Капабилити*: Поддерживаемые протоколы (например, WPA2-PSK).

        Если возникли ошибки, проверьте формат JSON или свяжитесь с разработчиком.
        """
    )

    await callback.message.answer(instructions, parse_mode="Markdown", reply_markup=get_main_keyboard())
    await callback.answer()
