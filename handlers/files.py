import os
import tempfile
from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import config
from database import db
from api_client import api
from keyboards import main_menu

router = Router()

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 МБ


class FileState(StatesGroup):
    waiting = State()


@router.message(F.text == "📁 Файл")
async def file_start(message: Message, state: FSMContext):
    await state.set_state(FileState.waiting)
    await message.answer("📎 Отправь файл (до 20 МБ). Можно с подписью-запросом.")


@router.message(FileState.waiting, F.document)
async def file_process(message: Message, state: FSMContext, user_id: int):
    doc = message.document
    file_name = doc.file_name or "file"
    if doc.file_size and doc.file_size > MAX_FILE_SIZE:
        await message.answer("❌ Файл больше 20 МБ.")
        return

    user = await db.get_user(user_id)
    file_limit = (config.PREMIUM_LIMITS["file_tokens"]
                  if user["tariff"] == "premium" else config.FREE_LIMITS["file_tokens"])

    if user["tokens_file"] >= file_limit:
        await state.clear()
        await message.answer("⚠️ Лимит токенов на файлы исчерпан.")
        return

    await message.answer("⏳ Читаю файл...")
    try:
        file = await message.bot.get_file(doc.file_id)
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file_name)[1]) as tmp:
            await message.bot.download_file(file.file_path, tmp.name)
            tmp_path = tmp.name

        text_content = ""
        ext = os.path.splitext(file_name)[1].lower()

        if ext in {".txt", ".md", ".py", ".json", ".csv", ".log"}:
            with open(tmp_path, "r", encoding="utf-8", errors="ignore") as f:
                text_content = f.read()
        elif ext == ".pdf":
            try:
                from pypdf import PdfReader
                reader = PdfReader(tmp_path)
                text_content = "\n".join(p.extract_text() or "" for p in reader.pages)
            except Exception as e:
                await message.answer(f"❌ Не удалось прочитать PDF: {e}")
                os.unlink(tmp_path)
                await state.clear()
                return
        elif ext == ".docx":
            try:
                from docx import Document
                d = Document(tmp_path)
                text_content = "\n".join(p.text for p in d.paragraphs)
            except Exception as e:
                await message.answer(f"❌ Не удалось прочитать DOCX: {e}")
                os.unlink(tmp_path)
                await state.clear()
                return
        else:
            await message.answer(f"❌ Формат {ext} не поддерживается.")
            os.unlink(tmp_path)
            await state.clear()
            return

        os.unlink(tmp_path)

        if len(text_content) > 50000:
            text_content = text_content[:50000] + "\n...[обрезано]"

        prompt = message.caption or "Проанализируй этот файл и дай краткое содержание."
        mode = config.MODES.get(user["bot_mode"], config.MODES["normal"])

        content, tokens = await api.chat(
            [{"role": "user", "content": f"{prompt}\n\n---\n{text_content}"}],
            max_tokens=mode["max_tokens"],
        )
        await db.add_tokens(user_id, "tokens_file", tokens)
        await db.log_action(user_id, "file", f"{file_name}: {prompt}", content, tokens)
        await state.clear()

        if len(content) > 4000:
            for i in range(0, len(content), 4000):
                await message.answer(content[i:i + 4000])
        else:
            await message.answer(content, reply_markup=main_menu(user_id == config.ADMIN_ID))
    except Exception as e:
        if "tmp_path" in locals() and tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
        await message.answer(f"❌ Ошибка: {e}")
        await state.clear()