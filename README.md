# avecloud — Telegram-бот с ИИ

Закрытый Telegram-бот на **aiogram 3**: текстовые ответы, генерация картинок, анализ файлов (txt, md, py, json, csv, log, pdf, docx), тарифы Free/Premium с лимитами и админ-панель.

- 💬 Текст и 🖼 картинки — бесплатно через [Pollinations](https://pollinations.ai) (ключ не нужен)
- 📁 Файлы — через любой OpenAI-совместимый API (нужен ключ)
- 👑 Админ-панель: пользователи, блокировка, выдача Premium и токенов, логи, статистика, заявки на Premium
- Доступ только для пользователей из белого списка

## Быстрый старт

```bash
git clone <url-репозитория>
cd avecloud
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env     # и заполните значения
python bot.py
```

## Настройка (`.env`)

| Переменная | Описание |
|---|---|
| `BOT_TOKEN` | токен от [@BotFather](https://t.me/BotFather) |
| `ADMIN_ID` | ваш Telegram ID (узнать: [@userinfobot](https://t.me/userinfobot)) |
| `ALLOWED_USERS` | ID пользователей через запятую; админ добавляется автоматически |
| `API_BASE_URL`, `API_KEY`, `API_MODEL` | OpenAI-совместимый API для анализа файлов |
| `DATA_DIR` | папка для баз данных (по умолчанию `./data`) |

Лимиты тарифов и режимы (`econom` / `normal` / `max`) меняются в `config.py`.

## Деплой на Amvera

В репозитории есть `amvera.yml`. В настройках проекта Amvera задайте переменные окружения из таблицы выше и обязательно `DATA_DIR=/data`, чтобы базы лежали на постоянном диске. Бот поднимает health-сервер на порту 80.

## Структура

```
bot.py            точка входа
config.py         настройки и лимиты
database.py       SQLite (aiosqlite)
api_client.py     клиенты платного и бесплатного API
keyboards.py      клавиатуры
handlers/         user, admin, files
middlewares/      проверка доступа
```

## Лицензия

MIT, см. [LICENSE](LICENSE).
