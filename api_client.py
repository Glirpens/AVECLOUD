import asyncio
import aiohttp
import base64
import random
import urllib.parse
from config import config

class APIClient:
    def __init__(self):
        # Платный API — теперь ТОЛЬКО для файлов
        self.base_url = config.API_BASE_URL.rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {config.API_KEY}",
            "Content-Type": "application/json"
        }
        # Бесплатный чат (Pollinations, без ключа)
        self.free_base_url = config.FREE_CHAT_BASE_URL.rstrip("/")
        # Бесплатные картинки (Pollinations, без ключа)
        self.free_image_base = config.FREE_IMAGE_BASE_URL.rstrip("/")

    async def chat(self, messages: list, max_tokens: int = 2048):
        """Платный API. Используется только для анализа файлов."""
        payload = {
            "model": config.API_MODEL,
            "messages": messages,
            "max_tokens": max_tokens,
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=180),
            ) as resp:
                data = await resp.json()
                if resp.status != 200:
                    raise Exception(f"API {resp.status}: {data}")
                content = data["choices"][0]["message"]["content"]
                tokens = data.get("usage", {}).get("total_tokens", 0)
                return content, tokens

    async def chat_free(self, messages: list, max_tokens: int = 2048):
        """Бесплатный чат (без ключа, токены не тратятся). Возвращает (текст, 0)."""
        payload = {
            "model": config.FREE_CHAT_MODEL,
            "messages": messages,
            "max_tokens": max_tokens,
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.free_base_url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=120),
            ) as resp:
                data = await resp.json()
                if resp.status != 200:
                    raise Exception(f"Free API {resp.status}: {data}")
                content = data["choices"][0]["message"]["content"]
                return content, 0

    def _is_cyrillic(self, s: str) -> bool:
        return any("Ѐ" <= ch <= "ӿ" for ch in s)

    async def _translate_prompt(self, prompt: str) -> str:
        """Русский промпт сервис портит в ???, из-за чего картинки не по теме.
        Переводим на английский через тот же бесплатный текстовый API."""
        if not self._is_cyrillic(prompt):
            return prompt
        try:
            content, _ = await self.chat_free(
                [
                    {
                        "role": "system",
                        "content": (
                            "You are an image-prompt translator. Translate the user's "
                            "image description to concise English for an image generation "
                            "model. Reply ONLY with the English description, no quotes, "
                            "no explanations."
                        ),
                    },
                    {"role": "user", "content": prompt[:800]},
                ],
                max_tokens=300,
            )
            content = content.strip().strip('"').strip("'")
            return content[:900] if content else prompt
        except Exception:
            return prompt  # лучше попробовать с оригиналом, чем не генерить вовсе

    async def generate_image_free(self, prompt: str, width: int = 1024, height: int = 1024):
        """Бесплатная генерация картинки (без ключа). Возвращает bytes.
        Бесплатный сервис часто отвечает 402/500 при перегрузке — повторяем с новым seed."""
        en_prompt = await self._translate_prompt(prompt)
        q = urllib.parse.quote(en_prompt[:1200], safe="")
        params = f"?width={width}&height={height}&nologo=true"
        if config.FREE_IMAGE_MODEL:
            params += f"&model={config.FREE_IMAGE_MODEL}"
        url = f"{self.free_image_base}/{q}{params}"

        last_err = None
        for _ in range(6):
            seed = random.randint(0, 999999)
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        url + f"&seed={seed}",
                        timeout=aiohttp.ClientTimeout(total=240),
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.read()
                            # сервис иногда отдаёт JSON вместо картинки
                            if not data.startswith(b"{"):
                                return data
                            last_err = Exception(f"Free image API: {data[:300]}")
                        else:
                            last_err = Exception(f"Free image API {resp.status}")
            except Exception as e:
                last_err = e
            await asyncio.sleep(2)
        raise Exception(f"Генерация не удалась (бесплатный сервис перегружен). {last_err}")

    async def generate_image(self, prompt: str):
        """Старый платный метод (оставлен как запасной, ботом не используется)."""
        payload = {
            "model": config.API_IMAGE_MODEL,
            "prompt": prompt,
            "n": 1,
            "size": "1024x1024",
            "response_format": "b64_json",
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/images/generations",
                headers=self.headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=240),
            ) as resp:
                data = await resp.json()
                if resp.status != 200:
                    raise Exception(f"API {resp.status}: {data}")
                item = data["data"][0]
                if item.get("b64_json"):
                    return base64.b64decode(item["b64_json"])
                if item.get("url"):
                    async with session.get(item["url"]) as img:
                        return await img.read()
                raise Exception("No image in response")

api = APIClient()
