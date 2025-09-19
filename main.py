import os
from loguru import logger

from bot import build_application

# Настройка loguru
logger.add(
    "bot.log",
    rotation="10 MB",
    retention="10 days",
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
)
logger.add(
    sys.stderr,
    level="INFO",
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | <level>{message}</level>"
)


def main() -> None:
    token = os.environ.get("BOT_TOKEN") or "REPLACE_WITH_YOUR_BOT_TOKEN"
    if not token or token.startswith("REPLACE"):
        logger.error("Установите переменную окружения BOT_TOKEN и перезапустите бота.")
        return

    try:
        app = build_application(token)
        logger.info("Запуск бота...")
        app.run_polling()
    except Exception as e:
        logger.exception(f"Произошла ошибка при запуске бота: {e}")
        raise


if __name__ == "__main__":
    main()