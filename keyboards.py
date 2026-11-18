from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def main_menu(is_admin: bool = False):
    kb = [
        [KeyboardButton(text="💬 Текст"), KeyboardButton(text="🖼 Картинка")],
        [KeyboardButton(text="📁 Файл"), KeyboardButton(text="📊 Мой профиль")],
        [KeyboardButton(text="⭐ Купить Premium")],
    ]
    if is_admin:
        kb.append([KeyboardButton(text="👑 Админ-панель")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def admin_menu():
    kb = [
        [KeyboardButton(text="👥 Пользователи")],
        [KeyboardButton(text="📈 Статистика")],
        [KeyboardButton(text="📨 Заявки")],
        [KeyboardButton(text="⚙️ Режим бота")],
        [KeyboardButton(text="⬅️ Назад")],
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def user_actions(user_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ Выдать Premium", callback_data=f"prem_{user_id}")],
        [InlineKeyboardButton(text="🚫 Заблокировать", callback_data=f"block_{user_id}")],
        [InlineKeyboardButton(text="➕ Токены", callback_data=f"addtok_{user_id}")],
        [InlineKeyboardButton(text="📜 Логи", callback_data=f"logs_{user_id}")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data=f"stats_{user_id}")],
    ])

def mode_selector():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Экономный", callback_data="mode_econom")],
        [InlineKeyboardButton(text="⚖️ Обычный", callback_data="mode_normal")],
        [InlineKeyboardButton(text="🔥 Максимум", callback_data="mode_max")],
    ])

def cancel_kb():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True)