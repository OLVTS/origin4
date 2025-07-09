import asyncio
from aiogram import Bot, Dispatcher, F, types
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from config import BOT_TOKEN, ADMIN_IDS
from database import AsyncSessionLocal, init_db
from models import User, UserRole, Property, PropertyStatus
from states import AddProperty

from functools import wraps
from aiogram.types import Message, CallbackQuery

dp = Dispatcher(storage=MemoryStorage())
bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.MARKDOWN)

# --- Декоратор ---
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

# --- Меню ---
def admin_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Список пользователей", callback_data="admin_users")],
        [InlineKeyboardButton(text="📄 Добавить объект", callback_data="admin_add")],
        [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="admin_back")]
    ])

@dp.message(F.text == "/menu")
@admin_only
async def show_admin_menu(message: Message):
    await message.answer("🛠 Админ-меню", reply_markup=admin_menu())

@dp.callback_query(F.data == "admin_back")
@admin_only
async def back_to_admin_menu(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.edit_text("🛠 Админ-меню", reply_markup=admin_menu())

@dp.callback_query(F.data == "admin_users")
@admin_only
async def show_users(callback: types.CallbackQuery):
    async with AsyncSessionLocal() as session:
        stmt = select(User).where(User.role != UserRole.admin)
        result = await session.execute(stmt)
        users = result.scalars().all()

    if not users:
        text = "🙁 Нет зарегистрированных пользователей."
    else:
        text = "📋 *Список пользователей:*\n" + "\n".join(
            [f"• `{user.tg_id}` – {user.role.value}" for user in users]
        )

    await callback.answer()
    await callback.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=admin_menu())

# --- /start ---
@dp.message(F.text == "/start")
async def cmd_start(message: Message):
    tg_id = message.from_user.id
    async with AsyncSessionLocal() as session:
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
            await message.answer(f"👋 Привет! Ты зарегистрирован как *{role.value}*.",
                                 reply_markup=admin_menu() if role == UserRole.admin else None)
        else:
            await message.answer("👋 С возвращением! Ты уже зарегистрирован.",
                                 reply_markup=admin_menu() if user.role == UserRole.admin else None)

# --- /help ---
@dp.message(F.text == "/help")
async def show_help(message: Message):
    await message.answer(
        "🤖 *Доступные команды:*\n"
        "/start — регистрация\n"
        "/menu — админ-меню (если вы админ)\n"
        "/add_object — добавить объект\n"
        "/help — справка",
        parse_mode=ParseMode.MARKDOWN
    )

# --- FSM шаги добавления объекта ---
@dp.message(F.text == "/add_object")
async def start_add_property(message: Message, state: FSMContext):
    await state.set_state(AddProperty.location)
    await message.answer("📍 Введите локацию:", reply_markup=ReplyKeyboardRemove())

@dp.message(AddProperty.location)
async def step_location(message: Message, state: FSMContext):
    await state.update_data(location=message.text)
    await state.set_state(AddProperty.description)
    await message.answer("🛏 Комнаты/этаж/этажность:")

@dp.message(AddProperty.description)
async def step_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await state.set_state(AddProperty.condition)
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=txt)] for txt in ["Евроремонт", "Без ремонта", "Коробка"]],
        resize_keyboard=True)
    await message.answer("🧱 Состояние объекта:", reply_markup=keyboard)

@dp.message(AddProperty.condition)
async def step_condition(message: Message, state: FSMContext):
    await state.update_data(condition=message.text)
    await state.set_state(AddProperty.parking)
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=txt)] for txt in ["Подземный", "Наземный", "Нет"]],
        resize_keyboard=True)
    await message.answer("🚗 Парковка:", reply_markup=keyboard)

@dp.message(AddProperty.parking)
async def step_parking(message: Message, state: FSMContext):
    await state.update_data(parking=message.text)
    await state.set_state(AddProperty.bathrooms)
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=str(i))] for i in range(1, 6)],
        resize_keyboard=True)
    await message.answer("🚽 Кол-во санузлов:", reply_markup=keyboard)

@dp.message(AddProperty.bathrooms)
async def step_bathrooms(message: Message, state: FSMContext):
    await state.update_data(bathrooms=message.text)
    await state.set_state(AddProperty.additions)
    await message.answer("✏ Дополнения:", reply_markup=ReplyKeyboardRemove())

@dp.message(AddProperty.additions)
async def step_additions(message: Message, state: FSMContext):
    await state.update_data(additions=message.text)
    await state.set_state(AddProperty.price)
    await message.answer("💰 Цена:")

@dp.message(AddProperty.price)
async def step_price(message: Message, state: FSMContext):
    await state.update_data(price=message.text)
    data = await state.get_data()

    text = "*Предпросмотр объекта:*\n"
    if data.get("location"): text += f"📍 {data['location']}\n"
    if data.get("description"): text += f"🛏 {data['description']}\n"
    if data.get("condition"): text += f"🧱 {data['condition']}\n"
    if data.get("parking"): text += f"🚗 {data['parking']}\n"
    if data.get("bathrooms"): text += f"🚽 {data['bathrooms']}\n"
    if data.get("additions"): text += f"✏ {data['additions']}\n"
    if data.get("price"): text += f"💰 *{data['price']}*"

    await state.set_state(AddProperty.confirm)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Сохранить", callback_data="save_object")],
        [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_object")]
    ])
    await message.answer(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)

@dp.callback_query(F.data == "save_object")
async def confirm_save(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    async with AsyncSessionLocal() as session:
        try:
            obj = Property(
                created_by=callback.from_user.id,
                location=data.get("location"),
                description=data.get("description"),
                condition=data.get("condition"),
                parking=data.get("parking"),
                bathrooms=int(data.get("bathrooms")) if data.get("bathrooms") else None,
                additions=data.get("additions"),
                price=data.get("price"),
                status=PropertyStatus.available
            )
            session.add(obj)
            await session.commit()
            await callback.message.edit_text("✅ Объект успешно добавлен!")
        except SQLAlchemyError:
            await session.rollback()
            await callback.message.edit_text("❌ Ошибка при сохранении объекта.")
        finally:
            await state.clear()

@dp.callback_query(F.data == "cancel_object")
async def cancel_add(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Добавление объекта отменено.")

# --- Запуск ---
if __name__ == "__main__":
    async def main():
        print("Бот запущен...")
        import models  # Важно для регистрации моделей
        await init_db()
        await dp.start_polling(bot)

    asyncio.run(main())
