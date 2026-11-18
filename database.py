import aiosqlite
import os
from datetime import datetime, timedelta
from config import config

class Database:
    def __init__(self):
        pass

    async def init(self):
        os.makedirs(config.DATA_DIR, exist_ok=True)
        async with aiosqlite.connect(config.DB_PATH) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    tariff TEXT DEFAULT 'free',
                    tokens_text INTEGER DEFAULT 0,
                    tokens_file INTEGER DEFAULT 0,
                    images_count INTEGER DEFAULT 0,
                    last_reset TEXT,
                    last_image_reset TEXT,
                    registered_at TEXT,
                    is_blocked INTEGER DEFAULT 0,
                    bot_mode TEXT DEFAULT 'normal'
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS applications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    status TEXT DEFAULT 'pending',
                    created_at TEXT
                )
            """)
            await db.commit()

        async with aiosqlite.connect(config.LOG_DB_PATH) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    action_type TEXT,
                    request TEXT,
                    response TEXT,
                    tokens_used INTEGER DEFAULT 0,
                    created_at TEXT
                )
            """)
            await db.commit()

    async def get_user(self, user_id: int):
        async with aiosqlite.connect(config.DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cur:
                return await cur.fetchone()

    async def create_user(self, user_id: int, username: str):
        async with aiosqlite.connect(config.DB_PATH) as db:
            now = datetime.now().isoformat()
            await db.execute(
                "INSERT OR IGNORE INTO users (user_id, username, last_reset, last_image_reset, registered_at) VALUES (?, ?, ?, ?, ?)",
                (user_id, username, now, now, now)
            )
            await db.commit()

    async def update_field(self, user_id: int, field: str, value):
        allowed = {"tariff", "tokens_text", "tokens_file", "images_count",
                   "last_reset", "last_image_reset", "is_blocked", "bot_mode", "username"}
        if field not in allowed:
            raise ValueError(f"Field {field} not allowed")
        async with aiosqlite.connect(config.DB_PATH) as db:
            await db.execute(f"UPDATE users SET {field} = ? WHERE user_id = ?", (value, user_id))
            await db.commit()

    async def add_tokens(self, user_id: int, field: str, amount: int):
        if field not in {"tokens_text", "tokens_file"}:
            raise ValueError("Only token fields allowed")
        async with aiosqlite.connect(config.DB_PATH) as db:
            await db.execute(f"UPDATE users SET {field} = {field} + ? WHERE user_id = ?", (amount, user_id))
            await db.commit()

    async def get_all_users(self):
        async with aiosqlite.connect(config.DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM users ORDER BY registered_at DESC") as cur:
                return await cur.fetchall()

    async def log_action(self, user_id: int, action_type: str, request: str, response: str, tokens: int = 0):
        async with aiosqlite.connect(config.LOG_DB_PATH) as db:
            await db.execute(
                "INSERT INTO actions (user_id, action_type, request, response, tokens_used, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, action_type, request[:800], response[:800], tokens, datetime.now().isoformat())
            )
            await db.commit()

    async def get_user_logs(self, user_id: int, limit: int = 50):
        async with aiosqlite.connect(config.LOG_DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM actions WHERE user_id = ? ORDER BY id DESC LIMIT ?", (user_id, limit)
            ) as cur:
                return await cur.fetchall()

    async def get_stats(self, user_id: int = None, period: str = "all"):
        async with aiosqlite.connect(config.LOG_DB_PATH) as db:
            if period == "hour":
                since = (datetime.now() - timedelta(hours=1)).isoformat()
            elif period == "day":
                since = (datetime.now() - timedelta(days=1)).isoformat()
            elif period == "week":
                since = (datetime.now() - timedelta(weeks=1)).isoformat()
            else:
                since = "1970-01-01"
            query = "SELECT COALESCE(SUM(tokens_used),0) as total, COUNT(*) as count FROM actions WHERE created_at > ?"
            params = [since]
            if user_id:
                query += " AND user_id = ?"
                params.append(user_id)
            db.row_factory = aiosqlite.Row
            async with db.execute(query, params) as cur:
                return await cur.fetchone()

    async def create_application(self, user_id: int):
        async with aiosqlite.connect(config.DB_PATH) as db:
            await db.execute(
                "INSERT INTO applications (user_id, created_at) VALUES (?, ?)",
                (user_id, datetime.now().isoformat())
            )
            await db.commit()

    async def get_pending_applications(self):
        async with aiosqlite.connect(config.DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM applications WHERE status = 'pending' ORDER BY id DESC") as cur:
                return await cur.fetchall()

    async def close_application(self, app_id: int, status: str = "closed"):
        async with aiosqlite.connect(config.DB_PATH) as db:
            await db.execute("UPDATE applications SET status = ? WHERE id = ?", (status, app_id))
            await db.commit()

db = Database()