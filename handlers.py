import json
import textwrap
from typing import Any, Dict, List, Optional
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from loguru import logger

from controler import Controller


# Настройка loguru для вывода в терминал
logger.add(
    sink=lambda msg: print(msg, end=""),  # Вывод в терминал
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="DEBUG",
    colorize=True,
)

# Также можно добавить вывод в файл (опционально)
logger.add(
    "bot.log",
    rotation="10 MB",
    retention="10 days",
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
)

bot_router = Router()
controller = Controller()


def _truncate(value: Optional[Any], length: int) -> str:
    if value is None:
        return ""
    s = str(value)
    return s if len(s) <= length else s[: max(0, length - 1)] + "…"


def get_main_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Таблица", callback_data="action:show_table"),
            InlineKeyboardButton(text="➕ Новое заполнение", callback_data="action:new_entry"),
        ],
        [InlineKeyboardButton(text="📚 Инструкция", callback_data="action:instructions")]
    ])
    return keyboard


def _format_records_table(records: List[Dict[str, Any]]) -> str:
    if not records:
        return "(нет записей)"
    lines = ["BSSID | SSID | RSSI | FREQ | TIMESTAMP"]
    for r in records:
        lines.append(
            f"{_truncate(r.get('bssid'),17)} | {_truncate(r.get('ssid'),20)} | {_truncate(r.get('rssi'),4)} | {_truncate(r.get('frequency'),5)} | {_truncate(r.get('timestamp'),10)}"
        )
    return "\n".join(lines)


@bot_router.message(Command(commands=["start"]))
async def cmd_start(message: types.Message) -> None:
    logger.info(f"User {message.from_user.id} started the bot")
    await message.answer(
        "Привет! Я бот для сбора WiFi-данных. Выберите действие ниже:",
        reply_markup=get_main_keyboard(),
    )


@bot_router.callback_query(F.data == "action:show_table")
async def show_table(callback: types.CallbackQuery) -> None:
    logger.debug("Callback show_table received: {}", callback.data)
    try:
        records = controller.get_all_networks()
        logger.info(f"Retrieved {len(records)} records from database")
        text = _format_records_table(records)
        await callback.message.answer(f"📊 Таблица записей:\n{text}")
    except Exception as e:
        logger.error("Error showing table: {}", e)
        await callback.message.answer("❌ Ошибка при получении таблицы")
    await callback.answer()


@bot_router.callback_query(F.data == "action:instructions")
async def show_instructions(callback: types.CallbackQuery) -> None:
    logger.debug("Callback instructions received: {}", callback.data)
    instructions = textwrap.dedent(
        """
        📚 *Инструкция по использованию WiFi Data Bot*

        Этот бот принимает данные о WiFi сетях в формате JSON.

        Функционал:
        - Таблица: показывает все записи
        - Новое заполнение: отправьте JSON как текст или файлом .json

        Пример записи (JSON):
        {
            "bssid": "00:11:22:33:44:55",
            "frequency": 2412,
            "rssi": -50,
            "ssid": "MyWiFi",
            "timestamp": 1698115200,
            "channel_bandwidth": "20",
            "capabilities": "WPA2-PSK"
        }
        """
    ).strip()

    await callback.message.answer(
        instructions,
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )
<<<<<<< HEAD
    await callback.message.answer(instructions, parse_mode="Markdown")
    await callback.answer()


@bot_router.callback_query(F.data == "action:new_entry")
async def new_entry_prompt(callback: types.CallbackQuery) -> None:
    logger.debug("Callback new_entry received: {}", callback.data)
    await callback.message.answer("Отправьте JSON (как текст или файл .json) с данными сети.")
    await callback.answer()


@bot_router.message()
async def handle_text_or_file(message: types.Message) -> None:
    logger.info(f"Processing message from user {message.from_user.id}")
    
    # Handle json text messages or json files attached
    # If there is a document with .json extension – try to read
    payload: Optional[bytes] = None
    if message.document and message.document.file_name.lower().endswith('.json'):
        logger.debug("JSON file received: {}", message.document.file_name)
        file = await message.document.download()
        payload = await file.read()
    elif message.text:
        logger.debug("Text message received")
        payload = message.text.encode('utf-8')
    else:
        logger.warning("Unsupported message type received")
        await message.answer("Отправьте JSON текстом или прикрепите .json файл.")
        return

    try:
        data = controller.parse_json(payload)
        logger.debug("JSON parsed successfully")
    except ValueError as e:
        logger.error("JSON parsing error: {}", e)
        await message.answer(f"Ошибка парсинга JSON: {e}")
        return

    # If it's a list, process items one by one
    if isinstance(data, list):
        logger.info(f"Processing list with {len(data)} items")
        ok_count = 0
        for i, item in enumerate(data):
            try:
                nw = controller.build_network(item)
                if controller.save_network(nw):
                    ok_count += 1
                    logger.debug(f"Item {i+1} saved successfully")
                else:
                    logger.warning(f"Failed to save item {i+1}")
            except Exception as e:
                logger.error("Error saving item {} from list: {}", i+1, e)
        
        logger.info(f"Saved {ok_count}/{len(data)} records successfully")
        await message.answer(f"Сохранено {ok_count}/{len(data)} записей.")
        await message.answer("Готово!", reply_markup=get_main_keyboard())
        return

    # single record
    logger.debug("Processing single record")
    try:
        nw = controller.build_network(data)
        if controller.save_network(nw):
            logger.info("Single record saved successfully")
            await message.answer("✅ Данные успешно сохранены.", reply_markup=get_main_keyboard())
        else:
            logger.warning("Failed to save single record")
            await message.answer("❌ Не удалось сохранить запись (возможно дубликат BSSID или ошибочные поля).")
    except Exception as e:
        logger.error("Error processing single record: {}", e)
        await message.answer(f"Ошибка при обработке записи: {e}")
=======
    await callback.answer()  # Подтверждаем нажатие кнопки
>>>>>>> dc915c2f680653ea37a87ea047816d5b4fab2de7
