import os
import logging

from bot import build_application

logging.basicConfig(level=logging.INFO)


def main() -> None:
	token = os.environ.get("BOT_TOKEN") or "REPLACE_WITH_YOUR_BOT_TOKEN"
	if not token or token.startswith("REPLACE"):
		print("Установите переменную окружения BOT_TOKEN и перезапустите бота.")
		return

	app = build_application(token)
	logging.info("Запуск бота...")
	app.run_polling()


if __name__ == "__main__":
	main()

