import asyncio
import os
from loguru import logger
from dotenv import load_dotenv, find_dotenv
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties

load_dotenv(find_dotenv())
TOKEN = os.getenv("TOKEN")

async def main():
    logger.add("file.log",
               format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}",
               rotation="3 days",
               backtrace=True,
               diagnose=True)

    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher()


    logger.info("Бот запущен")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        logger.info("Бот остановлен")

if __name__ == '__main__':
    asyncio.run(main())
