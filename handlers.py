import json
import textwrap
from typing import Any, Dict, List, Optional
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from loguru import logger

from controler import Controller
from tools.table_renderer import render_html_table


# Функция для перевода уровня логирования на русский
def russian_level(record):
    levels = {
        "TRACE": "ТРЕЙС",
        "DEBUG": "ОТЛАДКА",
        "INFO": "ИНФО",
        "SUCCESS": "УСПЕХ",
        "WARNING": "ПРЕДУПРЕЖДЕНИЕ",
        "ERROR": "ОШИБКА",
        "CRITICAL": "КРИТИЧНО",
    }
    record["level"].name = levels.get(record["level"].name, record["level"].name)
    return record


# Настройка loguru
logger.remove()
logger.add(
    sink=lambda msg: print(msg, end=""),
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <12}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="DEBUG",
    colorize=True,
    filter=russian_level,
)
logger.add(
    "bot.log",
    rotation="10 MB",
    retention="10 days",
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
)

bot_router = Router()
controller = Controller()


class Form(StatesGroup):
    waiting_for_pavilion = State()
    waiting_for_password = State()


def _truncate(value: Optional[Any], length: int) -> str:
    if value is None:
        return ""
    s = str(value)
    return s if len(s) <= length else s[: max(0, length - 1)] + "…"


def get_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Таблица", callback_data="action:show_table"),
            InlineKeyboardButton(text="➕ Новое заполнение", callback_data="action:new_entry"),
        ],
        [
            InlineKeyboardButton(text="📖 Инструкция", callback_data="action:instructions"),
        ]
    ])


def _format_records_table(records: List[Dict[str, Any]]) -> str:
    if not records:
        return "BSSID | SSID | RSSI | FREQ | TIMESTAMP\n00:11:22:33:44:55 | MyWiFi | -50 | 2412 | 1698115200"

    lines = ["BSSID | SSID | RSSI | FREQ | TIMESTAMP"]
    for r in records:
        lines.append(
            f"{_truncate(r.get('bssid'),17)} | {_truncate(r.get('ssid'),20)} | {_truncate(r.get('rssi'),4)} | {_truncate(r.get('frequency'),5)} | {_truncate(r.get('timestamp'),10)}"
        )
    return "\n".join(lines)


def _validate_wifi_data(data: Dict[str, Any]) -> tuple[bool, str]:
    required_fields = ['bssid', 'frequency', 'rssi', 'ssid', 'timestamp']
    for field in required_fields:
        if field not in data:
            return False, f"Отсутствует обязательное поле: {field}"

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
    prepared_data = data.copy()
    for key in prepared_data:
        if prepared_data[key] is None:
            if key in ['frequency', 'rssi', 'timestamp']:
                prepared_data[key] = 0
            elif key in ['ssid', 'bssid', 'channel_bandwidth', 'capabilities']:
                prepared_data[key] = ""
        elif prepared_data[key] == "":
            if key in ['bssid']:
                prepared_data[key] = "00:00:00:00:00:00"

    required_fields = ['bssid', 'frequency', 'rssi', 'ssid', 'timestamp', 'channel_bandwidth', 'capabilities']
    for field in required_fields:
        if field not in prepared_data:
            if field in ['frequency', 'rssi', 'timestamp']:
                prepared_data[field] = 0
            else:
                prepared_data[field] = ""

    return prepared_data


def _is_example_payload(obj) -> bool:
    """Detect the example payload shown in the bot instructions."""
    if not isinstance(obj, dict):
        return False
    bssid = obj.get('bssid', '')
    if isinstance(bssid, str) and bssid.strip() == '00:11:22:33:44:55':
        return True
    if obj.get('ssid') == 'MyWiFi':
        return True
    return False


async def _process_single_wifi_record(data: Dict[str, Any], message: types.Message, state: FSMContext) -> Optional[str]:
    prepared_data = _prepare_wifi_data(data)
    is_valid, error_msg = _validate_wifi_data(prepared_data)
    if not is_valid:
        await message.answer(f"❌ Ошибка валидации данных: {error_msg}", reply_markup=get_main_keyboard())
        return None

    try:
        network = controller.build_network(prepared_data)
        bssid = controller.save_network(network)
        if bssid:
            return bssid
        else:
            await message.answer("❌ Не удалось сохранить данные в БД.", reply_markup=get_main_keyboard())
            return None
    except Exception as e:
        logger.exception("Error processing WiFi record")
        await message.answer(f"❌ Ошибка при обработке данных: {e}", reply_markup=get_main_keyboard())
        return None


async def _process_multiple_wifi_records(records: List[Dict[str, Any]], message: types.Message) -> None:
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
            bssid = await _process_single_wifi_record(record, message, FSMContext(state=None))
            if bssid:
                success_count += 1
            else:
                error_count += 1
        except Exception:
            error_count += 1
            logger.exception(f"Ошибка при обработке записи #{i}")

    result_message = (
        f"Обработка завершена!\n\n"
        f"• Успешно: {success_count}/{total_count}\n"
        f"• Ошибки: {error_count}/{total_count}"
    )
    await message.answer(result_message, reply_markup=get_main_keyboard())


async def _process_json_content(parsed_data: Any, message: types.Message, state: FSMContext) -> None:
    # Проверка на пример
    if isinstance(parsed_data, list):
        if any(_is_example_payload(item) for item in parsed_data if isinstance(item, dict)):
            await message.answer(
                "⚠️ Похоже, вы прислали пример из инструкции, а не реальные данные. Пожалуйста, пришлите реальные записи.",
                reply_markup=get_main_keyboard(),
            )
            return
        await _process_multiple_wifi_records(parsed_data, message)
    elif isinstance(parsed_data, dict):
        if _is_example_payload(parsed_data):
            await message.answer(
                "⚠️ Похоже, вы прислали пример из инструкции, а не реальные данные. Пожалуйста, пришлите реальные записи.",
                reply_markup=get_main_keyboard(),
            )
            return

        bssid = await _process_single_wifi_record(parsed_data, message, state)
        if bssid:
            await state.update_data(bssid=bssid)
            await message.answer("🏢 Введите номер павильона:")
            await state.set_state(Form.waiting_for_pavilion)
        else:
            await message.answer("❌ Не удалось обработать запись.", reply_markup=get_main_keyboard())
    else:
        await message.answer("❌ Неподдерживаемый формат JSON. Ожидается объект или массив.", reply_markup=get_main_keyboard())


@bot_router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
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


@bot_router.callback_query(F.data == "action:show_table")
async def show_table(callback: types.CallbackQuery) -> None:
    try:
        records = controller.get_all_networks()
        logger.info(f"Получено {len(records)} записей из базы данных")
    except Exception as exc:
        logger.exception("Failed to read records from DB")
        await callback.message.answer(f"❌ Ошибка при получении таблицы: {exc}")
        await callback.answer()
        return

    if not records:
        await callback.message.answer("Таблица пуста. Добавьте данные через '➕ Новое заполнение'.")
        await callback.answer()
        return

    table_text = _format_records_table(records)
    if len(table_text) > 4000:
        parts = [table_text[i:i+4000] for i in range(0, len(table_text), 4000)]
        for part in parts:
            await callback.message.answer(f"```\n{part}\n```", parse_mode="Markdown")
        # after sending parts, provide an inline export button
        export_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🖼 Скачать HTML", callback_data="action:show_table_pretty")]])
        await callback.message.answer("Полная таблица слишком большая для одного сообщения. Вы можете скачать её целиком:", reply_markup=export_kb)
        await callback.message.answer("", reply_markup=get_main_keyboard())
    else:
        # attach an inline button to allow exporting the full table as a styled HTML
        export_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🖼 Скачать HTML", callback_data="action:show_table_pretty")]])
        await callback.message.answer(f"```\n{table_text}\n```", parse_mode="Markdown", reply_markup=export_kb)
    await callback.answer()


@bot_router.callback_query(F.data == "action:show_table_pretty")
async def show_table_pretty(callback: types.CallbackQuery) -> None:
    """Generate a pretty HTML table and send it as a file to the user."""
    try:
        records = controller.get_all_networks()
    except Exception as exc:
        logger.exception("Failed to read records from DB")
        await callback.message.answer(f"❌ Ошибка при получении таблицы: {exc}")
        await callback.answer()
        return

    if not records:
        await callback.message.answer("Таблица пуста. Добавьте данные через '➕ Новое заполнение'.")
        await callback.answer()
        return

    html = render_html_table(records, title="Таблица WiFi-сетей")
    # send as in-memory file
    from io import BytesIO

    bio = BytesIO()
    bio.write(html.encode('utf-8'))
    bio.seek(0)
    filename = "wifi_table.html"
    try:
        # prefer bot.send_document with explicit chat_id to avoid context issues
        await callback.message.bot.send_document(chat_id=callback.message.chat.id, document=types.InputFile(bio, filename=filename))
        # also send main keyboard afterwards
        await callback.message.answer("Готово — файл отправлен.", reply_markup=get_main_keyboard())
    except Exception as e:
        logger.exception("Failed to send HTML document to user")
        # fallback: send as text (may be large)
        await callback.message.answer("❌ Не удалось отправить файл. Отправляю таблицу как текст:")
        await callback.message.answer(f"```\n{_format_records_table(records)}\n```", parse_mode="Markdown")

    await callback.answer()


@bot_router.callback_query(F.data == "action:new_entry")
async def new_entry_prompt(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    example_single = textwrap.dedent('''
        📋 *Одиночная запись:*
        ```json
        {
            "bssid": "00:11:22:33:44:55",
            "frequency": 2412,
            "rssi": -50,
            "ssid": "MyWiFi",
            "timestamp": 1698115200,
            "channel_bandwidth": "20",
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


@bot_router.message(F.document)
async def handle_json_file(message: types.Message, state: FSMContext) -> None:
    if not message.document or not message.document.file_name.lower().endswith('.json'):
        await message.answer("❌ Пожалуйста, отправьте файл в формате JSON.", reply_markup=get_main_keyboard())
        return

    try:
        file = await message.bot.get_file(message.document.file_id)
        file_content = await message.bot.download_file(file.file_path)
        content_text = file_content.read().decode('utf-8')
        await message.answer("📥 Файл получен, начинаю обработку...")
        try:
            parsed_data = json.loads(content_text)
        except json.JSONDecodeError as e:
            await message.answer(f"❌ Ошибка парсинга JSON: {e}", reply_markup=get_main_keyboard())
            return
        await _process_json_content(parsed_data, message, state)
    except Exception as e:
        logger.exception("Error processing JSON file")
        await message.answer(f"❌ Ошибка при обработке файла: {e}", reply_markup=get_main_keyboard())


@bot_router.message()
async def handle_text_or_file(message: types.Message, state: FSMContext) -> None:
    payload_text = message.text or ""
    try:
        parsed_data = json.loads(payload_text)
    except json.JSONDecodeError as e:
        await message.answer(f"❌ Некорректный JSON: {e}", reply_markup=get_main_keyboard())
        return

    await _process_json_content(parsed_data, message, state)


@bot_router.message(Form.waiting_for_pavilion)
async def process_pavilion(message: types.Message, state: FSMContext):
    try:
        pavilion_input = message.text.strip()
        if pavilion_input.lower() in ("0", "none"):
            pavilion = None
        else:
            pavilion = int(pavilion_input)
            if pavilion <= 0:
                raise ValueError
        await state.update_data(pavilion=pavilion)
        await message.answer("🔑 Введите пароль от Wi-Fi сети (или '0' / 'none', если пароля нет):")
        await state.set_state(Form.waiting_for_password)
    except ValueError:
        await message.answer("❌ Номер павильона должен быть положительным целым числом, либо '0'/'none'. Попробуйте снова:")
        return


@bot_router.message(Form.waiting_for_password)
async def process_password(message: types.Message, state: FSMContext):
    password_input = message.text.strip()
    if password_input.lower() in ("0", "none", ""):
        password = None
    else:
        password = password_input

    data = await state.get_data()
    bssid = data.get("bssid")
    pavilion = data.get("pavilion")

    if not bssid:
        await message.answer("❌ Внутренняя ошибка: BSSID не найден.", reply_markup=get_main_keyboard())
        await state.clear()
        return

    success = controller.update_network(bssid, password=password, pavilion_number=pavilion)
    if success:
        await message.answer("✅ Данные успешно обновлены!", reply_markup=get_main_keyboard())
    else:
        await message.answer("❌ Не удалось обновить данные.", reply_markup=get_main_keyboard())

    await state.clear()


@bot_router.callback_query(F.data == "action:instructions")
async def show_instructions(callback: types.CallbackQuery) -> None:
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

        После добавления базовых данных бот запросит:
        - Номер павильона (целое число) или '0'/'none'
        - Пароль от Wi-Fi или '0'/'none'

        Эти данные будут сохранены в таблицу.
        """
    ).strip()

    await callback.message.answer(instructions, parse_mode="Markdown", reply_markup=get_main_keyboard())
    await callback.answer()