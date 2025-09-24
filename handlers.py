import logging
import json
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
            InlineKeyboardButton(text="📊 Таблица", callback_data="show_table"),
            InlineKeyboardButton(text="➕ Новое заполнение", callback_data="new_entry"),
        ],
        [InlineKeyboardButton(text="📚 Инструкция", callback_data="instructions")]
    ])
    return keyboard


def _format_records_table(records: List[Dict[str, Any]]) -> str:
    """Форматирует список записей в текстовую таблицу."""
    if not records:
        return "📊 Таблица WiFi-сетей:\n\nТаблица пуста."

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


def _validate_wifi_data(data: Dict[str, Any]) -> tuple[bool, str]:
    """Проверяет валидность данных WiFi-сети."""
    required_fields = ['bssid', 'frequency', 'rssi', 'ssid', 'timestamp']

    for field in required_fields:
        if field not in data:
            return False, f"Отсутствует обязательное поле: {field}"

    # Проверка типов данных
    if not isinstance(data['bssid'], str) or len(data['bssid']) == 0:
        return False, "BSSID должен быть непустой строкой"

    if not isinstance(data['ssid'], str):
        return False, "SSID должен быть строкой"

    if not isinstance(data['frequency'], (int, float)) or data['frequency'] <= 0:
        return False, "Frequency должен быть положительным числом"

    if not isinstance(data['rssi'], int) or data['rssi'] > 0:
        return False, "RSSI должен быть целым отрицательным числом"

    if not isinstance(data['timestamp'], (int, float)) or data['timestamp'] <= 0:
        return False, "Timestamp должен быть положительным числом"

    return True, ""


def _prepare_wifi_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Подготавливает данные WiFi-сети, обрабатывая пустые значения."""
    prepared_data = data.copy()
    
    # Обработка пустых или None значений
    for key in prepared_data:
        if prepared_data[key] is None:
            if key in ['frequency', 'rssi', 'timestamp']:
                prepared_data[key] = 0
            elif key in ['ssid', 'bssid', 'channel_bandwidth', 'capabilities']:
                prepared_data[key] = ""
        elif prepared_data[key] == "":
            if key in ['bssid']:
                prepared_data[key] = "00:00:00:00:00:00"
    
    # Гарантируем наличие всех обязательных полей
    required_fields = ['bssid', 'frequency', 'rssi', 'ssid', 'timestamp', 'channel_bandwidth', 'capabilities']
    for field in required_fields:
        if field not in prepared_data:
            if field in ['frequency', 'rssi', 'timestamp']:
                prepared_data[field] = 0
            else:
                prepared_data[field] = ""
    
    return prepared_data


async def _process_single_wifi_record(data: Dict[str, Any], message: types.Message) -> bool:
    """Обрабатывает одну запись WiFi-данных."""
    # Подготавливаем данные
    prepared_data = _prepare_wifi_data(data)
    
    # Проверяем валидность данных
    is_valid, error_msg = _validate_wifi_data(prepared_data)
    if not is_valid:
        await message.answer(f"❌ Ошибка валидации данных: {error_msg}", reply_markup=get_main_keyboard())
        return False

    try:
        # Пробуем сохранить через контроллер
        network = controller.build_network(prepared_data)
        saved = controller.save_network(network)

        if saved:
            return True
        else:
            await message.answer("❌ Не удалось сохранить данные в БД.", reply_markup=get_main_keyboard())
            return False

    except Exception as e:
        logger.exception("Error processing WiFi record")
        await message.answer(f"❌ Ошибка при обработке данных: {e}", reply_markup=get_main_keyboard())
        return False


async def _process_multiple_wifi_records(records: List[Dict[str, Any]], message: types.Message) -> None:
    """Обрабатывает множественные записи WiFi-данных."""
    if not records:
        await message.answer("❌ Нет записей для обработки.", reply_markup=get_main_keyboard())
        return

    total_count = len(records)
    success_count = 0
    error_count = 0

    await message.answer(f"🔄 Начинаю обработку {total_count} записей...")

    for i, record in enumerate(records, 1):
        if not isinstance(record, dict):
            error_count += 1
            logger.warning(f"Запись #{i} имеет неверный формат: {type(record)}")
            continue

        try:
            if await _process_single_wifi_record(record, message):
                success_count += 1
            else:
                error_count += 1
        except Exception:
            error_count += 1
            logger.exception(f"Ошибка при обработке записи #{i}")

    # Формируем итоговое сообщение
    result_message = (
        f"✅ Обработка завершена!\n\n"
        f"• Успешно: {success_count}/{total_count}\n"
        f"• Ошибки: {error_count}/{total_count}"
    )

    await message.answer(result_message, reply_markup=get_main_keyboard())


async def _process_json_file_content(content: str, message: types.Message) -> None:
    """Обрабатывает содержимое JSON-файла."""
    try:
        parsed_data = json.loads(content)
    except json.JSONDecodeError as e:
        await message.answer(f"❌ Ошибка парсинга JSON: {e}", reply_markup=get_main_keyboard())
        return

    # Определяем тип данных: одиночная запись или массив записей
    if isinstance(parsed_data, list):
        # Множественные записи
        await _process_multiple_wifi_records(parsed_data, message)
    elif isinstance(parsed_data, dict):
        # Одиночная запись
        success = await _process_single_wifi_record(parsed_data, message)
        if success:
            await message.answer("✅ Данные из файла успешно сохранены в таблицу!", reply_markup=get_main_keyboard())
    else:
        await message.answer("❌ Неподдерживаемый формат JSON. Ожидается объект или массив.", reply_markup=get_main_keyboard())


# Обработчик команды /start
@bot_router.message(Command("start"))
async def cmd_start(message: types.Message):
    welcome_text = (
        "Добро пожаловать в WiFi Data Bot! 🌐\n"
        "Я помогаю собирать и хранить данные о WiFi-сетях.\n"
        "Вы можете присылать данные как текстом в JSON формате, так и JSON-файлами.\n\n"
        "📋 Поддерживаемые форматы:\n"
        "• Одиночная запись: JSON-объект\n"
        "• Множественные записи: JSON-массив объектов\n\n"
        "Используйте кнопки ниже для работы с ботом:"
    )
    await message.answer(welcome_text, reply_markup=get_main_keyboard())


# Обработчик кнопки "Таблица"
@bot_router.callback_query(F.data == "show_table")
async def show_table(callback: types.CallbackQuery) -> None:
    """Отправляет пользователю текстовую таблицу со всеми записями."""
    try:
        records = controller.db.read_all()
    except Exception as exc:
        logger.exception("Failed to read records from DB")
        await callback.message.answer(f"Ошибка при получении таблицы: {exc}")
        await callback.answer()
        return

    if not records:
        await callback.message.answer("Таблица пуста. Добавьте данные через '➕ Новое заполнение'.")
        await callback.answer()
        return

    table_text = _format_records_table(records)
    
    # Разбиваем длинные сообщения на части
    if len(table_text) > 4000:
        parts = [table_text[i:i+4000] for i in range(0, len(table_text), 4000)]
        for part in parts:
            await callback.message.answer(f"```\n{part}\n```", parse_mode="Markdown")
    else:
        await callback.message.answer(f"```\n{table_text}\n```", parse_mode="Markdown", reply_markup=get_main_keyboard())
    
    await callback.answer()


# Обработчик кнопки "Начать новое заполнение"
@bot_router.callback_query(F.data == "new_entry")
async def start_new_entry(callback: types.CallbackQuery) -> None:
    """Просит пользователя прислать JSON с данными о WiFi-сети."""
    example_single = textwrap.dedent('''
        📋 *Одиночная запись:*
        ```json
        {
            "bssid": "00:11:22:33:44:55",
            "frequency": 2412,
            "rssi": -50,
            "ssid": "MyWiFi",
            "timestamp": 1698115200,
            "channel_bandwidth": "20MHz",
            "capabilities": "WPA2-PSK"
        }
        ```
    ''')
    
    example_multiple = textwrap.dedent('''
        📋 *Множественные записи (массив):*
        ```json
        [
            {
                "bssid": "00:11:22:33:44:55",
                "frequency": 2412,
                "rssi": -50,
                "ssid": "MyWiFi",
                "timestamp": 1698115200
            },
            {
                "bssid": "AA:BB:CC:DD:EE:FF",
                "frequency": 5180,
                "rssi": -65,
                "ssid": "OfficeNet",
                "timestamp": 1698115300
            }
        ]
        ```
    ''')

    instruction_text = (
        "📝 Введите данные WiFi-сети в формате JSON или отправьте JSON-файл.\n\n"
        "Вы можете отправить:\n"
        "• **Одиночную запись** - один JSON-объект\n"
        "• **Множественные записи** - JSON-массив объектов\n\n"
    )

    await callback.message.answer(instruction_text, parse_mode="Markdown")
    await callback.message.answer(example_single, parse_mode="Markdown")
    await callback.message.answer("... или ...", parse_mode="Markdown")
    await callback.message.answer(example_multiple, parse_mode="Markdown")

    await callback.answer()


# Обработчик JSON-файлов
@bot_router.message(F.document)
async def handle_json_file(message: types.Message) -> None:
    """Обрабатывает загруженные JSON-файлы."""
    if not message.document:
        return

    # Проверяем, что это JSON файл
    if not message.document.file_name.endswith('.json'):
        await message.answer("❌ Пожалуйста, отправьте файл в формате JSON.", reply_markup=get_main_keyboard())
        return

    try:
        # Скачиваем файл
        file = await message.bot.get_file(message.document.file_id)
        file_content = await message.bot.download_file(file.file_path)
        content_text = file_content.read().decode('utf-8')

        await message.answer("📥 Файл получен, начинаю обработку...")

        # Обрабатываем содержимое файла
        await _process_json_file_content(content_text, message)

    except Exception as e:
        logger.exception("Error processing JSON file")
        await message.answer(f"❌ Ошибка при обработке файла: {e}", reply_markup=get_main_keyboard())


# Обработчик текстового ввода для новой записи
@bot_router.message()
async def process_new_entry(message: types.Message) -> None:
    """Обрабатывает текстовое сообщение как JSON-пэйлоад."""
    payload_text = message.text or ""

    try:
        parsed_data = json.loads(payload_text)
    except json.JSONDecodeError as e:
        await message.answer(f"❌ Некорректный JSON: {e}", reply_markup=get_main_keyboard())
        return

    # Определяем тип данных: одиночная запись или массив записей
    if isinstance(parsed_data, list):
        # Множественные записи
        await _process_multiple_wifi_records(parsed_data, message)
    elif isinstance(parsed_data, dict):
        # Одиночная запись
        success = await _process_single_wifi_record(parsed_data, message)
        if success:
            await message.answer("✅ Данные успешно сохранены в таблицу!", reply_markup=get_main_keyboard())
        else:
            await message.answer("❌ Не удалось сохранить данные. Проверьте формат.", reply_markup=get_main_keyboard())
    else:
        await message.answer("❌ Неподдерживаемый формат JSON. Ожидается объект или массив.", reply_markup=get_main_keyboard())


# Обработчик кнопки "Инструкция"
@bot_router.callback_query(F.data == "instructions")
async def show_instructions(callback: types.CallbackQuery) -> None:
    """Отправляет подробную инструкцию пользователю."""
    instructions = textwrap.dedent(
        """
        📚 *Инструкция по использованию WiFi Data Bot*

        Этот бот предназначен для сбора и хранения данных о WiFi-сетях.

        *Функционал бота:*
        - *Таблица*: Показывает все сохранённые данные о WiFi-сетях
        - *Начать новое заполнение*: Добавить новые WiFi-сети
        - *Инструкция*: Это сообщение

        *Способы добавления данных:*
        1. *Текстовый JSON*: Отправьте JSON-строку как текстовое сообщение
        2. *JSON-файл*: Отправьте файл с расширением .json

        *Форматы данных:*
        - *Одиночная запись*: JSON-объект с данными одной сети
        - *Множественные записи*: JSON-массив объектов

        *Пример одиночной записи:*
        ```json
        {
            "bssid": "00:11:22:33:44:55",
            "frequency": 2412,
            "rssi": -50,
            "ssid": "MyWiFi",
            "timestamp": 1698115200
        }
        ```
<<<<<<< HEAD

        *Обязательные поля:* bssid, frequency, rssi, ssid, timestamp

        Если возникли ошибки, проверьте формат JSON.
=======
>>>>>>> 8df2a6ae81cbbba7dc5ea44c92959a8d7ddbd142
        """
    )
