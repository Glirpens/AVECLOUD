from datetime import datetime
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import config
from database import db
from keyboards import admin_menu, user_actions, mode_selector, main_menu

router = Router()


class AdminStates(StatesGroup):
    add_tokens = State()
    broadcast = State()


def _is_admin(user_id: int) -> bool:
    return user_id == config.ADMIN_ID


@router.message(F.text == "👥 Пользователи")
async def users_list(message: Message, user_id: int, is_admin: bool):
    if not is_admin:
        return
    users = await db.get_all_users()
    if not users:
        await message.answer("Пользователей нет.")
        return
    for u in users[:20]:
        status = "🚫" if u["is_blocked"] else ("⭐" if u["tariff"] == "premium" else "👤")
        await message.answer(
            f"{status} ID: {u['user_id']}\n"
            f"@{u['username']}\n"
            f"Тариф: {u['tariff']} | Режим: {u['bot_mode']}\n"
            f"Текст: {u['tokens_text']} | Файлы: {u['tokens_file']} | Картинки: {u['images_count']}",
            reply_markup=user_actions(u["user_id"]),
        )


@router.callback_query(F.data.startswith("prem_"))
async def cb_premium(call: CallbackQuery):
    if call.from_user.id != config.ADMIN_ID:
        await call.answer("Нет доступа", show_alert=True)
        return
    target = int(call.data.split("_")[1])
    user = await db.get_user(target)
    if user is None:
        await call.answer("Пользователь не найден", show_alert=True)
        return
    new_tariff = "free" if user["tariff"] == "premium" else "premium"
    await db.update_field(target, "tariff", new_tariff)
    await call.message.answer(f"✅ Тариф пользователя {target} → {new_tariff}")
    await call.answer("Готово")


@router.callback_query(F.data.startswith("block_"))
async def cb_block(call: CallbackQuery):
    if call.from_user.id != config.ADMIN_ID:
        await call.answer("Нет доступа", show_alert=True)
        return
    target = int(call.data.split("_")[1])
    user = await db.get_user(target)
    if user is None:
        await call.answer("Пользователь не найден", show_alert=True)
        return
    new_block = 0 if user["is_blocked"] else 1
    await db.update_field(target, "is_blocked", new_block)
    await call.message.answer(
        f"✅ Пользователь {target} {'заблокирован' if new_block else 'разблокирован'}"
    )
    await call.answer("Готово")


@router.callback_query(F.data.startswith("addtok_"))
async def cb_add_tokens(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != config.ADMIN_ID:
        await call.answer("Нет доступа", show_alert=True)
        return
    target = int(call.data.split("_")[1])
    await state.update_data(target=target)
    await state.set_state(AdminStates.add_tokens)
    await call.message.answer(
        "Введи: `тип количество`\n"
        "типы: text, file\n"
        "пример: `text 5000`"
    )
    await call.answer()


@router.message(AdminStates.add_tokens)
async def process_add_tokens(message: Message, state: FSMContext, is_admin: bool):
    if not is_admin:
        return
    try:
        parts = message.text.split()
        if len(parts) != 2:
            raise ValueError("нужно ровно два слова: тип и число")
        if parts[0] == "text":
            field = "tokens_text"
        elif parts[0] == "file":
            field = "tokens_file"
        else:
            raise ValueError("тип может быть только text или file")
        amount = int(parts[1])
        data = await state.get_data()
        target = data.get("target")
        if target is None:
            raise ValueError("цель не найдена, начни заново")
        await db.add_tokens(target, field, amount)
        await message.answer(f"✅ Добавлено {amount} токенов ({field}) пользователю {target}")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")
    await state.clear()


@router.callback_query(F.data.startswith("logs_"))
async def cb_logs(call: CallbackQuery):
    if call.from_user.id != config.ADMIN_ID:
        await call.answer("Нет доступа", show_alert=True)
        return
    target = int(call.data.split("_")[1])
    logs = await db.get_user_logs(target, limit=10)
    if not logs:
        await call.message.answer("Логов нет.")
        await call.answer()
        return
    text = f"📜 Последние 10 действий {target}:\n\n"
    for log in logs:
        text += (
            f"[{log['created_at'][:19]}] {log['action_type']}: "
            f"{log['request'][:60]}... ({log['tokens_used']} ток.)\n"
        )
    await call.message.answer(text[:4000])
    await call.answer()


@router.callback_query(F.data.startswith("stats_"))
async def cb_stats(call: CallbackQuery):
    if call.from_user.id != config.ADMIN_ID:
        await call.answer("Нет доступа", show_alert=True)
        return
    target = int(call.data.split("_")[1])
    text = f"📊 Статистика {target}:\n\n"
    for period in ["hour", "day", "week", "all"]:
        s = await db.get_stats(target, period)
        text += f"{period}: {s['count']} действий, {s['total']} токенов\n"
    await call.message.answer(text)
    await call.answer()


@router.message(F.text == "📈 Статистика")
async def global_stats(message: Message, is_admin: bool):
    if not is_admin:
        return
    text = "📊 Глобальная статистика:\n\n"
    for period in ["hour", "day", "week", "all"]:
        s = await db.get_stats(None, period)
        text += f"{period}: {s['count']} действий, {s['total']} токенов\n"
    await message.answer(text)


@router.message(F.text == "📨 Заявки")
async def applications(message: Message, is_admin: bool):
    if not is_admin:
        return
    apps = await db.get_pending_applications()
    if not apps:
        await message.answer("Заявок нет.")
        return
    for a in apps:
        u = await db.get_user(a["user_id"])
        uname = u["username"] if u else "?"
        await message.answer(
            f"📨 Заявка #{a['id']}\n"
            f"ID: {a['user_id']} (@{uname})\n"
            f"Дата: {a['created_at'][:19]}",
            reply_markup=user_actions(a["user_id"]),
        )


@router.message(F.text == "⚙️ Режим бота")
async def mode_menu(message: Message, is_admin: bool):
    if not is_admin:
        return
    await message.answer("Выбери режим бота (для себя):", reply_markup=mode_selector())


@router.callback_query(F.data.startswith("mode_"))
async def mode_set(call: CallbackQuery):
    if call.from_user.id != config.ADMIN_ID:
        await call.answer("Нет доступа", show_alert=True)
        return
    mode = call.data.split("_")[1]
    if mode not in config.MODES:
        await call.answer("Неизвестный режим")
        return
    await db.update_field(call.from_user.id, "bot_mode", mode)
    await call.message.answer(f"✅ Режим: {mode}")
    await call.answer("Готово")