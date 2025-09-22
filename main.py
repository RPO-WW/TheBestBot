import asyncio
import os

from loguru import logger
from dotenv import load_dotenv, find_dotenv
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties

from controler import Controller


load_dotenv(find_dotenv())
TOKEN = os.getenv("TOKEN")

dp = Dispatcher()
dp.include_router(handlers_router)


async def main():
    logger.add("file.log",
               format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}",
               rotation="3 days",
               backtrace=True,
               diagnose=True)

    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))

    logger.info("Бот запущен")

    # TODO
    # controller = Controller()
    # controller.logic()

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        logger.info("Бот остановлен")


if __name__ == '__main__':
    asyncio.run(main())
