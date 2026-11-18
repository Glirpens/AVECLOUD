import os
from dataclasses import dataclass, field
from typing import List

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def _parse_ids(raw: str) -> List[int]:
    """'123, 456' -> [123, 456]"""
    return [int(x) for x in raw.replace(" ", "").split(",") if x]


ADMIN_ID_VALUE = int(os.getenv("ADMIN_ID", "0") or 0)


@dataclass
class Config:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")

    # Telegram ID администратора (узнать можно у @userinfobot)
    ADMIN_ID: int = ADMIN_ID_VALUE
    # Кому разрешён доступ, через запятую. Админ добавляется автоматически.
    ALLOWED_USERS: List[int] = field(
        default_factory=lambda: sorted(set(_parse_ids(os.getenv("ALLOWED_USERS", ""))) | ({ADMIN_ID_VALUE} - {0}))
    )

    # Платный OpenAI-совместимый API (используется для анализа файлов)
    API_BASE_URL: str = os.getenv("API_BASE_URL", "https://api.openai.com/v1")
    API_KEY: str = os.getenv("API_KEY", "")
    API_MODEL: str = os.getenv("API_MODEL", "gpt-4o-mini")
    API_IMAGE_MODEL: str = os.getenv("API_IMAGE_MODEL", "gpt-image-1")

    # Бесплатные API без ключа (Pollinations): текст и картинки.
    FREE_CHAT_BASE_URL: str = os.getenv("FREE_CHAT_BASE_URL", "https://text.pollinations.ai/openai")
    FREE_CHAT_MODEL: str = os.getenv("FREE_CHAT_MODEL", "openai")
    FREE_IMAGE_BASE_URL: str = os.getenv("FREE_IMAGE_BASE_URL", "https://image.pollinations.ai/prompt")
    FREE_IMAGE_MODEL: str = os.getenv("FREE_IMAGE_MODEL", "flux")

    PREMIUM_LIMITS: dict = field(default_factory=lambda: {
        "images_per_day": 1,
        "file_tokens": 10000,
        "text_tokens": 1000,
    })
    FREE_LIMITS: dict = field(default_factory=lambda: {
        "images_per_day": 14,
        "file_tokens": 500,
        "file_tokens_days": 3,
        "text_tokens": 500,
        "text_tokens_days": 3,
    })

    MODES: dict = field(default_factory=lambda: {
        "econom": {"daily_tokens": 4000, "max_tokens": 512},
        "normal": {"daily_tokens": 10000, "max_tokens": 2048},
        "max":    {"daily_tokens": 30000, "max_tokens": 8192},
    })

    DATA_DIR: str = os.getenv("DATA_DIR", "./data")
    DB_PATH: str = os.getenv("DB_PATH", os.path.join(os.getenv("DATA_DIR", "./data"), "bot.db"))
    LOG_DB_PATH: str = os.getenv("LOG_DB_PATH", os.path.join(os.getenv("DATA_DIR", "./data"), "logs.db"))


config = Config()
