from loguru import logger
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
import sqlite3


class BotController:
    def init(self, conn: sqlite3.Connection):
        self.conn = conn

    async def start(self, msg: Message, state: FSMContext):
        try:
            text = "Привет! Отправляй текст, я сохраню и отсортирую.\n" \
                   "Используй /sort_time для сортировки."
            await msg.answer(text, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Ошибка команды /start: {e}")
            await msg.answer("Ошибка. Попробуйте снова.")

    async def handle_message(self, msg: Message, state: FSMContext):
        try:
            if not msg.text.strip():
                await msg.answer("Отправьте непустое сообщение.")
                return
            data = {'user_id': msg.from_user.id, 'message': msg.text,
                    'timestamp': msg.date.isoformat()}
            c = self.conn.cursor()
            c.execute("INSERT INTO messages VALUES (?, ?, ?)",
                      (data['user_id'], data['message'], data['timestamp']))
            self.conn.commit()
            c.execute("SELECT user_id, message, timestamp FROM messages "
                      "ORDER BY LOWER(message)")
            sorted_data = [{'user_id': row[0], 'message': row[1],
                            'timestamp': row[2]} for row in c.fetchall()]
            response = "Данные (по тексту):\n"
            for item in sorted_data:
                response += f"User {item['user_id']}: {item['message']} " \
                           f"(время: {item['timestamp']})\n"
            await msg.answer(response, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Ошибка обработки сообщения: {e}")
            await msg.answer("Ошибка обработки. Попробуйте снова.")

    async def sort_by_time(self, msg: Message, state: FSMContext):
        try:
            c = self.conn.cursor()
            c.execute("SELECT user_id, message, timestamp FROM messages")
            sorted_data = [{'user_id': row[0], 'message': row[1],
                            'timestamp': row[2]} for row in c.fetchall()]
            if not sorted_data:
                await msg.answer("Нет данных!")
                return
            sorted_data = sorted(sorted_data, key=lambda x: x['timestamp'])
            response = "Данные (по времени):\n"
            for item in sorted_data:
                response += f"User {item['user_id']}: {item['message']} " \
                           f"(время: {item['timestamp']})\n"
            await msg.answer(response, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Ошибка команды /sort_time: {e}")
            await msg.answer("Ошибка сортировки. Попробуйте снова.")
