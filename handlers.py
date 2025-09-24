from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from controler import Controller  # Импорт вашего Controller

# Создаём маршрутизатор
bot_router = Router()

# Инициализация Controller
controller = Controller()


# Функция для создания клавиатуры с тремя кнопками
def get_main_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Таблица", callback_data="show_table"),
            InlineKeyboardButton(text="Начать новое заполнение", callback_data="new_entry"),
        ],
        [InlineKeyboardButton(text="Инструкция", callback_data="instructions")]
    ])
    return keyboard


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
async def show_table(callback: types.CallbackQuery):
    try:
        # Предполагаем, что WiFiDB имеет метод read_all() для получения всех записей
        records = controller.db.read_all()  # TODO: Реализуйте read_all() в WiFiDB, если его нет
        if not records:
            await callback.message.answer("Таблица пуста. Добавьте данные через 'Начать новое заполнение'.")
            return

        # Формируем таблицу в текстовом виде
        table = "📊 Таблица WiFi-сетей:\n\n"
        table += f"{'SSID':<20} {'BSSID':<18} {'Частота':<10} {'RSSI':<8} {'Канал':<10} {'Время':<15} {'Капабилити':<20}\n"
        table += "-" * 100 + "\n"
        for record in records:
            table += (
                f"{record['ssid'][:19]:<20} "
                f"{record['bssid']:<18} "
                f"{record['frequency']:<10} "
                f"{record['rssi']:<8} "
                f"{record['channel_bandwidth']:<10} "
                f"{record['timestamp']:<15} "
                f"{record['capabilities'][:19]:<20}\n"
            )
        await callback.message.answer(table, reply_markup=get_main_keyboard())
    except Exception as e:
        await callback.message.answer(f"Ошибка при получении таблицы: {e}")
    await callback.answer()


# Обработчик кнопки "Начать новое заполнение"
@bot_router.callback_query(F.data == "new_entry")
async def start_new_entry(callback: types.CallbackQuery):
    await callback.message.answer(
        "📝 Введите данные WiFi-сети в формате JSON, например:\n"
        '{"bssid": "00:11:22:33:44:55", "frequency": 2412, "rssi": -50, '
        '"ssid": "MyWiFi", "timestamp": 1698115200, "channel_bandwidth": "20MHz", '
        '"capabilities": "WPA2-PSK"}'
    )
    # Устанавливаем состояние ожидания ввода JSON
    await callback.message.bot.set_chat_menu_button(
        chat_id=callback.message.chat.id,
        menu_button=types.MenuButtonCommands()
    )
    await callback.answer()


# Обработчик текстового ввода для новой записи
@bot_router.message()
async def process_new_entry(message: types.Message):
    try:
        success = controller.process_payload_and_save(message.text)
        if success:
            await message.answer(
                "✅ Данные успешно сохранены в таблицу!",
                reply_markup=get_main_keyboard()
            )
        else:
            await message.answer(
                "❌ Не удалось сохранить данные. Проверьте формат JSON.",
                reply_markup=get_main_keyboard()
            )
    except ValueError as e:
        await message.answer(f"❌ Ошибка в JSON: {e}", reply_markup=get_main_keyboard())
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}", reply_markup=get_main_keyboard())


# Обработчик кнопки "Инструкция"
@bot_router.callback_query(F.data == "instructions")
async def show_instructions(callback: types.CallbackQuery):
    instructions = (
        "📚 **Инструкция по использованию WiFi Data Bot**\n\n"
        "Этот бот предназначен для сбора и хранения данных о WiFi-сетях. "
        "Вы можете добавлять данные о сетях, просматривать их в таблице и получать информацию о функционале.\n\n"
        "**Функционал бота:**\n"
        "- **Таблица**: Показывает все сохранённые данные о WiFi-сетях в формате таблицы.\n"
        "- **Начать новое заполнение**: Позволяет добавить новую WiFi-сеть, отправив данные в формате JSON.\n"
        "- **Инструкция**: Выводит это сообщение.\n\n"
        "**Как заполнить таблицу:**\n"
        "1. Нажмите 'Начать новое заполнение'.\n"
        "2. Отправьте данные в формате JSON, например:\n"
        "   ```json\n"
        '   {"bssid": "00:11:22:33:44:55", "frequency": 2412, "rssi": -50, '
        '   "ssid": "MyWiFi", "timestamp": 1698115200, "channel_bandwidth": "20MHz", '
        '   "capabilities": "WPA2-PSK"}\n'
        "   ```\n"
        "3. Данные будут сохранены в базу и добавлены в таблицу.\n\n"
        "**Обозначения в таблице:**\n"
        "- **SSID**: Имя WiFi-сети.\n"
        "- **BSSID**: MAC-адрес точки доступа.\n"
        "- **Частота**: Частота в МГц (например, 2412 для 2.4 ГГц).\n"
        "- **RSSI**: Уровень сигнала в дБм (например, -50).\n"
        "- **Канал**: Ширина канала (например, 20MHz).\n"
        "- **Время**: Время обнаружения (Unix timestamp).\n"
        "- **Капабилити**: Поддерживаемые протоколы (например, WPA2-PSK).\n\n"
        "Если возникли ошибки, проверьте формат JSON или свяжитесь с разработчиком."
    )
    await callback.message.answer(instructions, parse_mode="Markdown", reply_markup=get_main_keyboard())
    await callback.answer()
