import os
import socket
import subprocess
import shlex
import re
import html
import logging
from typing import List, Tuple, Optional

from telegram import Update
from telegram.ext import (
	ApplicationBuilder,
	CommandHandler,
	ContextTypes,
	ConversationHandler,
	MessageHandler,
	filters,
)

LOG = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def get_local_ip() -> str:
	"""Return the primary local IPv4 address by connecting a UDP socket."""
	s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	try:
		s.connect(("8.8.8.8", 80))
		ip = s.getsockname()[0]
	except Exception:
		ip = "127.0.0.1"
	finally:
		s.close()
	return ip


def run_cmd(cmd: List[str]) -> str:
	try:
		output = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, encoding="utf-8", errors="ignore")
		return output
	except subprocess.CalledProcessError:
		return ""
	except FileNotFoundError:
		return ""


def get_wifi_ssid() -> Optional[str]:
	out = run_cmd(["netsh", "wlan", "show", "interfaces"])
	if not out:
		return None
	m = re.search(r"^\s*SSID\s*:\s*(.+)$", out, re.MULTILINE)
	if m:
		ssid = m.group(1).strip()
		# Sometimes shows "SSID : <none>"
		if ssid.lower() in ("<none>", "none"):
			return None
		return ssid
	return None


def parse_ipconfig_for_gateway_and_ip() -> Tuple[Optional[str], Optional[str]]:
	out = run_cmd(["ipconfig"]) or ""
	blocks = re.split(r"\r?\n\r?\n", out)
	for blk in blocks:
		# Skip disconnected adapters
		if "Media State" in blk and "disconnected" in blk.lower():
			continue
		ip_match = re.search(r"IPv4 Address[\. ]*:\s*([0-9\.]+)", blk)
		gateway_match = re.search(r"Default Gateway[\. ]*:\s*([0-9\.]+)", blk)
		if ip_match:
			ip = ip_match.group(1)
			gw = gateway_match.group(1) if gateway_match else None
			return ip, gw
	# fallback: use UDP socket ip and no gateway
	return get_local_ip(), None


def list_wifi_profiles() -> List[str]:
	out = run_cmd(["netsh", "wlan", "show", "profiles"]) or ""
	profiles = re.findall(r"All User Profile\s*:\s*(.+)", out)
	return [p.strip().strip('"') for p in profiles]


def get_wifi_password(profile: str) -> Optional[str]:
	# profile may contain special chars; netsh accepts quoted names
	cmd = ["netsh", "wlan", "show", "profile", f"name={profile}", "key=clear"]
	out = run_cmd(cmd) or ""
	m = re.search(r"Key Content\s*:\s*(.+)", out)
	if m:
		return m.group(1).strip()
	return None


def format_network_info() -> str:
	ssid = get_wifi_ssid()
	ip, gw = parse_ipconfig_for_gateway_and_ip()
	local_ip = get_local_ip()

	lines = []
	lines.append("<b>Сетевой отчёт</b>")
	lines.append("")
	if ssid:
		lines.append(f"🔸 <b>Имя сети (SSID):</b> <code>{html.escape(ssid)}</code>")
	else:
		lines.append("🔸 <b>Имя сети (SSID):</b> <i>Не подключено / не найдено</i>")

	if ip:
		lines.append(f"🔹 <b>Локальный IP (adapter):</b> <code>{html.escape(ip)}</code>")
	else:
		lines.append(f"🔹 <b>Локальный IP (adapter):</b> <i>Не найден</i>")

	lines.append(f"🔹 <b>Определённый IP (метод UDP):</b> <code>{html.escape(local_ip)}</code>")

	if gw:
		lines.append(f"🔸 <b>Шлюз (Default Gateway):</b> <code>{html.escape(gw)}</code>")
	else:
		lines.append(f"🔸 <b>Шлюз (Default Gateway):</b> <i>Не найден</i>")

	lines.append("")
	lines.append("Чтобы посмотреть сохранённые Wi‑Fi профили используйте: <code>/wifiprofiles</code>")
	lines.append("Чтобы увидеть пароль профиля: <code>/wifipass имя_профиля</code>")
	lines.append("Внимание: отображение паролей требует прав и доступно только на локальной машине.")

	return "\n".join(lines)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	text = (
		"<b>Привет! Я — маленький помощник сети.</b>\n\n"
		"Я могу показать текущий IP, имя Wi‑Fi сети, шлюз и помочь посмотреть сохранённые Wi‑Fi пароли.\n"
		"Используйте команды: <code>/network</code>, <code>/wifiprofiles</code>, <code>/wifipass</code>."
	)
	await update.message.reply_html(text)


async def network_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	text = format_network_info()
	await update.message.reply_html(text)


async def wifiprofiles_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	profiles = list_wifi_profiles()
	if not profiles:
		await update.message.reply_html("<i>Сохранённых Wi‑Fi профилей не найдено.</i>")
		return
	lines = ["<b>Сохранённые Wi‑Fi профили:</b>"]
	for p in profiles:
		lines.append(f"• <code>{html.escape(p)}</code>")
	lines.append("\nИспользуйте: <code>/wifipass имя_профиля</code>")
	await update.message.reply_html("\n".join(lines))


async def wifipass_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	args = context.args
	if not args:
		await update.message.reply_html("Использование: <code>/wifipass имя_профиля</code>")
		return
	profile = " ".join(args)
	pwd = get_wifi_password(profile)
	if pwd:
		await update.message.reply_html(f"<b>Пароль для</b> <code>{html.escape(profile)}</code>:\n<code>{html.escape(pwd)}</code>")
	else:
		await update.message.reply_html(f"Не удалось найти пароль для <code>{html.escape(profile)}</code> (или отсутствуют права).")


async def wifipass_all_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	profiles = list_wifi_profiles()
	if not profiles:
		await update.message.reply_html("<i>Сохранённых Wi‑Fi профилей не найдено.</i>")
		return
	lines = ["<b>Пароли Wi‑Fi (если доступны):</b>"]
	for p in profiles:
		pwd = get_wifi_password(p) or "<i>Не найден / закрыт</i>"
		lines.append(f"• <code>{html.escape(p)}</code>: <code>{html.escape(pwd)}</code>")
	await update.message.reply_html("\n".join(lines))


def main() -> None:
	token = os.environ.get("BOT_TOKEN") or "REPLACE_WITH_YOUR_BOT_TOKEN"
	if not token or token.startswith("REPLACE"):
		LOG.error("Токен бота не задан. Установите переменную окружения BOT_TOKEN или укажите токен в main.py.")
		print("Установите переменную окружения BOT_TOKEN и перезапустите бота.")
		return

	app = ApplicationBuilder().token(token).build()

	app.add_handler(CommandHandler("start", start_command))
	app.add_handler(CommandHandler("network", network_command))
	app.add_handler(CommandHandler("wifiprofiles", wifiprofiles_command))
	app.add_handler(CommandHandler("wifipass", wifipass_command))
	app.add_handler(CommandHandler("wifipass_all", wifipass_all_command))

	# Таблица: пошаговое заполнение
	NAME, ADDRESS, PASSWORD, NOTE = range(4)


	async def fill_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
		await update.message.reply_html("<b>Заполнение записи.</b> Введите имя сети (SSID) или отправьте /skip, чтобы пропустить.")
		return NAME


	async def fill_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
		text = update.message.text.strip() if update.message and update.message.text else ""
		context.user_data['name'] = text or "Отсутствует"
		await update.message.reply_html("Введите адрес (IP) или отправьте /skip, чтобы пропустить.")
		return ADDRESS


	async def fill_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
		text = update.message.text.strip() if update.message and update.message.text else ""
		context.user_data['address'] = text or "Отсутствует"
		await update.message.reply_html("Введите пароль (если есть) или отправьте /skip.")
		return PASSWORD


	async def fill_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
		text = update.message.text.strip() if update.message and update.message.text else ""
		context.user_data['password'] = text or "Отсутствует"
		await update.message.reply_html("Введите примечание или отправьте /skip.")
		return NOTE


	async def fill_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
		text = update.message.text.strip() if update.message and update.message.text else ""
		context.user_data['note'] = text or "Отсутствует"
		# Сохранить запись
		save_row(context.user_data)
		await update.message.reply_html("Запись сохранена в таблицу.")
		return ConversationHandler.END


	async def skip_field(update: Update, context: ContextTypes.DEFAULT_TYPE):
		# Найти текущую стадию по обработчику — проще: если ключ не задан, ставим отсутствует
		if 'name' not in context.user_data:
			context.user_data['name'] = "Отсутствует"
			await update.message.reply_html("Пропущено. Введите адрес (IP) или /skip.")
			return ADDRESS
		if 'address' not in context.user_data:
			context.user_data['address'] = "Отсутствует"
			await update.message.reply_html("Пропущено. Введите пароль или /skip.")
			return PASSWORD
		if 'password' not in context.user_data:
			context.user_data['password'] = "Отсутствует"
			await update.message.reply_html("Пропущено. Введите примечание или /skip.")
			return NOTE
		# note
		context.user_data['note'] = "Отсутствует"
		save_row(context.user_data)
		await update.message.reply_html("Запись сохранена в таблицу.")
		return ConversationHandler.END


	async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
		await update.message.reply_html("Заполнение отменено.")
		return ConversationHandler.END


	conv_handler = ConversationHandler(
		entry_points=[CommandHandler('fill', fill_start)],
		states={
			NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, fill_name), CommandHandler('skip', skip_field)],
			ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, fill_address), CommandHandler('skip', skip_field)],
			PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, fill_password), CommandHandler('skip', skip_field)],
			NOTE: [MessageHandler(filters.TEXT & ~filters.COMMAND, fill_note), CommandHandler('skip', skip_field)],
		},
		fallbacks=[CommandHandler('cancel', cancel)],
	)

	app.add_handler(conv_handler)

	# Показать таблицу
	async def showtable(update: Update, context: ContextTypes.DEFAULT_TYPE):
		rows = load_table()
		if not rows:
			await update.message.reply_html("<i>Таблица пуста.</i>")
			return
		lines = ["<b>Таблица записей:</b>"]
		for i, r in enumerate(rows, 1):
			lines.append(f"{i}. SSID: <code>{html.escape(r.get('name','Отсутствует'))}</code> | IP: <code>{html.escape(r.get('address','Отсутствует'))}</code> | Пароль: <code>{html.escape(r.get('password','Отсутствует'))}</code> | Прим: <code>{html.escape(r.get('note','Отсутствует'))}</code>")
		# Telegram limits message size; send in chunks if necessary
		text = "\n".join(lines)
		await update.message.reply_html(text)

	app.add_handler(CommandHandler('showtable', showtable))


def ensure_data_dir() -> str:
	path = os.path.join(os.path.dirname(__file__), "data")
	os.makedirs(path, exist_ok=True)
	return path


def save_row(data: dict) -> None:
	"""Save a single row dict to data/table.csv with headers: name,address,password,note"""
	dirp = ensure_data_dir()
	p = os.path.join(dirp, "table.csv")
	headers = ["name", "address", "password", "note"]
	# Normalize values
	row = [data.get(k, "Отсутствует") or "Отсутствует" for k in headers]
	import csv

	exists = os.path.exists(p)
	with open(p, "a", newline='', encoding="utf-8") as f:
		writer = csv.writer(f)
		if not exists:
			writer.writerow(headers)
		writer.writerow(row)


def load_table() -> list:
	dirp = ensure_data_dir()
	p = os.path.join(dirp, "table.csv")
	if not os.path.exists(p):
		return []
	import csv
	rows = []
	with open(p, newline='', encoding="utf-8") as f:
		reader = csv.DictReader(f)
		for r in reader:
			rows.append(r)
	return rows

	LOG.info("Запуск бота...")
	app.run_polling()


if __name__ == "__main__":
	main()
