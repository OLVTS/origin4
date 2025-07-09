import asyncio
from functools import wraps

from aiogram import Bot, Dispatcher, F, types
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from config import BOT_TOKEN, ADMIN_IDS
from database import AsyncSessionLocal, init_db
from models import User, UserRole

# Инициализация
dp = Dispatcher(storage=MemoryStorage())
bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.MARKDOWN)

# 🔒 Декоратор для ограничения доступа по ADMIN_IDS
def admin_only(handler):
    @wraps(handler)
    async def wrapper(event, *args, **kwargs):
        tg_id = event.from_user.id if isinstance(event, (Message, CallbackQuery)) else None
        if tg_id not in ADMIN_IDS:
            if isinstance(event, Message):
                await event.answer("🚫 У вас нет доступа к этой команде.")
            elif isinstance(event, CallbackQuery):
                await event.answer("🚫 Недостаточно прав.", show_alert=True)
            return
        return await handler(event, *args, **kwargs)
    return wrapper

# 👋 Команда /start — регистрация пользователя
@dp.message(F.text == "/start")
async def cmd_start(message: Message):
    tg_id = message.from_user.id
    session = AsyncSessionLocal()

    stmt = select(User).where(User.tg_id == tg_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        role = UserRole.admin if tg_id in ADMIN_IDS else UserRole.user
        new_user = User(tg_id=tg_id, role=role)
        session.add(new_user)
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
        await message.answer(
            f"👋 Привет! Ты зарегистрирован как *{role.value}*.",
            reply_markup=admin_menu() if role == UserRole.admin else None
        )
    else:
        await message.answer(
            f"👋 С возвращением! Ты уже зарегистрирован.",
            reply_markup=admin_menu() if user.role == UserRole.admin else None
        )

    await session.close()

# 🛠 Кнопочное админ-меню
def admin_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Список пользователей", callback_data="admin_users")],
        [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="admin_back")]
    ])

# Команда /menu — только для админов
@dp.message(F.text == "/menu")
@admin_only
async def show_admin_menu(message: Message):
    await message.answer("🛠 Админ-меню", reply_markup=admin_menu())

# Обработка кнопки "Список пользователей"
@dp.callback_query(F.data == "admin_users")
@admin_only
async def show_users(callback: types.CallbackQuery):
    session = AsyncSessionLocal()

    stmt = select(User).where(User.role != UserRole.admin)
    result = await session.execute(stmt)
    users = result.scalars().all()

    if not users:
        text = "🙁 Нет зарегистрированных пользователей."
    else:
        text = "📋 *Список пользователей:*\n" + "\n".join(
            [f"• `{user.tg_id}` – {user.role.value}" for user in users]
        )

    back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
    ])

    await callback.answer()
    await callback.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=back_keyboard)
    await session.close()

# Обработка кнопки "Назад"
@dp.callback_query(F.data == "admin_back")
@admin_only
async def back_to_admin_menu(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.edit_text("🛠 Админ-меню", reply_markup=admin_menu())

# 🚀 Запуск бота
if __name__ == "__main__":
    async def main():
        print("Бот запущен...")
        await init_db()
        await dp.start_polling(bot)

    asyncio.run(main())
