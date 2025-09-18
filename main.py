import os
import logging

from bot import build_application
from logconfig import setup_logging



def main() -> None:
	setup_logging()
	LOG = logging.getLogger(__name__)

	token = os.environ.get("BOT_TOKEN") or "REPLACE_WITH_YOUR_BOT_TOKEN"
	if not token or token.startswith("REPLACE"):
		LOG.error("Установите переменную окружения BOT_TOKEN и перезапустите бота.")
		return

	app = build_application(token)
	LOG.info("Запуск бота...")
	app.run_polling()


if __name__ == "__main__":
	main()

