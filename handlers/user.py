from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import config
from database import db
from api_client import api
from keyboards import main_menu, mode_selector

router = Router()


class TextState(StatesGroup):
    waiting = State()


class ImageState(StatesGroup):
    waiting = State()


def _reset_if_needed(user) -> dict:
    """Сбрасывает лимиты, если истёк период. Возвращает dict с актуальными значениями."""
    now = datetime.now()
    updates = {}

    last_reset = datetime.fromisoformat(user["last_reset"]) if user["last_reset"] else now
    if user["tariff"] == "premium":
        period = timedelta(days=1)
    else:
        period = timedelta(days=3)

    if now - last_reset >= period:
        updates["tokens_text"] = 0
        updates["tokens_file"] = 0
        updates["last_reset"] = now.isoformat()

    last_img = datetime.fromisoformat(user["last_image_reset"]) if user["last_image_reset"] else now
    if user["tariff"] == "premium":
        img_period = timedelta(days=1)
    else:
        img_period = timedelta(days=14)

    if now - last_img >= img_period:
        updates["images_count"] = 0
        updates["last_image_reset"] = now.isoformat()

    return updates


async def _apply_reset(user_id: int, updates: dict):
    for k, v in updates.items():
        await db.update_field(user_id, k, v)


@router.message(Command("start"))
async def start(message: Message, user_id: int, is_admin: bool):
    user = await db.get_user(user_id)
    updates = _reset_if_needed(user)
    if updates:
        await _apply_reset(user_id, updates)
    tariff = "⭐ Premium" if user["tariff"] == "premium" else "Free"
    await message.answer(
        f"👋 Привет, {message.from_user.full_name}!\n\n"
        f"Тариф: {tariff}\n"
        f"Режим бота: {user['bot_mode']}\n\n"
        f"Выбери действие:",
        reply_markup=main_menu(is_admin),
    )


@router.message(F.text == "📊 Мой профиль")
async def profile(message: Message, user_id: int):
    user = await db.get_user(user_id)
    updates = _reset_if_needed(user)
    if updates:
        await _apply_reset(user_id, updates)
        user = await db.get_user(user_id)

    if user["tariff"] == "premium":
        file_limit = config.PREMIUM_LIMITS["file_tokens"]
    else:
        file_limit = config.FREE_LIMITS["file_tokens"]

    await message.answer(
        f"👤 ID: {user['user_id']}\n"
        f"📛 Username: @{user['username']}\n"
        f"⭐ Тариф: {user['tariff']}\n"
        f"⚙️ Режим бота: {user['bot_mode']}\n\n"
        f"📝 Текст: ♾ бесплатно\n"
        f"📁 Файлы: {user['tokens_file']} / {file_limit}\n"
        f"🖼 Картинки: ♾ бесплатно\n"
        f"📅 Регистрация: {user['registered_at'][:10]}"
    )


@router.message(F.text == "💬 Текст")
async def text_start(message: Message, state: FSMContext):
    await state.set_state(TextState.waiting)
    await message.answer("✍️ Отправь текст запроса (бесплатно ♾):")


@router.message(TextState.waiting)
async def text_process(message: Message, state: FSMContext, user_id: int):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_menu(user_id == config.ADMIN_ID))
        return

    user = await db.get_user(user_id)
    updates = _reset_if_needed(user)
    if updates:
        await _apply_reset(user_id, updates)
        user = await db.get_user(user_id)

    # Обычное общение — бесплатно, лимиты не проверяем, токены не списываем.
    mode = config.MODES.get(user["bot_mode"], config.MODES["normal"])
    await message.answer("⏳ Обрабатываю...")
    try:
        content, tokens = await api.chat_free(
            [{"role": "user", "content": message.text}],
            max_tokens=mode["max_tokens"],
        )
        await db.log_action(user_id, "text", message.text, content, 0)
        await state.clear()

        if len(content) > 4000:
            for i in range(0, len(content), 4000):
                await message.answer(content[i:i + 4000])
        else:
            await message.answer(content, reply_markup=main_menu(user_id == config.ADMIN_ID))
    except Exception as e:
        await message.answer(f"❌ Ошибка API: {e}")
        await state.clear()


@router.message(F.text == "🖼 Картинка")
async def image_start(message: Message, state: FSMContext):
    await state.set_state(ImageState.waiting)
    await message.answer("🎨 Опиши картинку (бесплатно ♾):")


@router.message(ImageState.waiting)
async def image_process(message: Message, state: FSMContext, user_id: int):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_menu(user_id == config.ADMIN_ID))
        return

    await message.answer("🎨 Генерирую...")
    try:
        img_bytes = await api.generate_image_free(message.text)
        await db.update_field(user_id, "images_count",
                              (await db.get_user(user_id))["images_count"] + 1)
        await db.log_action(user_id, "image", message.text, "[image]", 0)
        await message.answer_photo(BufferedInputFile(img_bytes, filename="image.png"), reply_markup=main_menu(user_id == config.ADMIN_ID))
    except Exception as e:
        await message.answer(f"❌ Ошибка генерации: {e}")
    await state.clear()


@router.message(F.text == "⭐ Купить Premium")
async def buy_premium(message: Message, user_id: int):
    await db.create_application(user_id)
    await message.answer("📨 Заявка отправлена. Администратор свяжется с тобой.")


@router.message(F.text == "👑 Админ-панель")
async def admin_panel(message: Message, is_admin: bool):
    if not is_admin:
        return
    from keyboards import admin_menu
    await message.answer("👑 Админ-панель:", reply_markup=admin_menu())


@router.message(F.text == "⬅️ Назад")
async def back(message: Message, user_id: int):
    await message.answer("Главное меню", reply_markup=main_menu(user_id == config.ADMIN_ID))