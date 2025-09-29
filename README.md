# TheBestBot

## Распределение обязанностей

**Саша** - дата процессор

**Ксюша** - База данных

**Гера** - контролер

**Тимур** - собрать проект

**Кирилл** - собрать проект

**Линда** - контролер

**Влад** - 3 хендлера 

**Виталина** - курьер(2 сырном пожалуйста)

**Илюха** - FSM

## Функционал

Кнопка таблица: позволяет увидеть заполненную, на данный момент, таблицу. По мере добавления данных, таблица будет обновляться

Кнопка начать новое заполнение: позволяет заполнить новую строку таблицы

Кнопка Инструкция: выводит функционал бота , что он делает, чем дышит, обозначения в таблице, что нужно, чтобы заполнить таблицу и так далее

Telegram network helper bot.

Setup
1. Create a bot via BotFather and get the token.
2. Install dependencies (recommended in virtualenv):

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt
```

3. Set the `BOT_TOKEN` environment variable in PowerShell and run:

```powershell
$env:BOT_TOKEN = 'your_token_here'; python main.py
```

Commands
- `/start` — приветствие и инструкции
- `/network` — краткий сетевой отчёт (SSID, IP, шлюз)
- `/wifiprofiles` — список сохранённых Wi‑Fi профилей
- `/wifipass <profile>` — показать пароль для профиля (только локально и при наличии прав)

Security
- Отображение паролей Wi‑Fi возможно только при запуске на машине с сохранёнными профилями и правами администратора. Будьте осторожны с распространением этих данных.

Notes
- Скрипт рассчитан на Windows (использует `netsh` и `ipconfig`).
- Для Linux/macOS нужно адаптировать команды.

Pretty table export
-------------------

The bot now supports exporting a nicely styled HTML table of all records.
There is a reusable helper in `tools/table_renderer.py` which you can use
from other scripts as well. Example usage:

```python
from tools.table_renderer import render_html_table

# records is a list of dicts returned by controller.get_all_networks()
html = render_html_table(records, title="Таблица WiFi-сетей")
with open('wifi_table.html', 'w', encoding='utf-8') as f:
	f.write(html)

# open wifi_table.html in browser to view the styled, scrollable table
```

In the Telegram bot UI there is a button "🖼 Красиво" which generates the
HTML and sends it as a .html file to the user.
