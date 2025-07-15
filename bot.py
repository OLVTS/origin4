import asyncio
from functools import wraps
from aiogram import Bot, Dispatcher, F, types
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (InlineKeyboardMarkup, InlineKeyboardButton,
                           ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove)
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from config import BOT_TOKEN, ADMIN_IDS
from database import AsyncSessionLocal, init_db
from models import User, UserRole, Property, PropertyStatus
from states import AddProperty

dp = Dispatcher(storage=MemoryStorage())
bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.MARKDOWN)


# ---------- DECORATOR ----------
def admin_only(handler):
    @wraps(handler)
    async def wrapper(event, *args, **kwargs):
        tg_id = event.from_user.id
        if tg_id not in ADMIN_IDS:
            if isinstance(event, types.CallbackQuery):
                await event.answer("🚫 Недостаточно прав.", show_alert=True)
            else:
                await event.answer("🚫 У вас нет доступа.")
            return
        return await handler(event, *args, **kwargs)
    return wrapper


# ---------- MENUS ----------
def admin_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("📋 Список пользователей", callback_data="admin_users")],
        [InlineKeyboardButton("📄 Добавить объект", callback_data="admin_add")],
        [InlineKeyboardButton("🔙 Назад в меню", callback_data="admin_back")]
    ])


# ---------- /START ----------
@dp.message(F.text == "/start")
async def cmd_start(message: types.Message):
    tg_id = message.from_user.id
    async with AsyncSessionLocal() as session:
        user = (await session.execute(select(User).where(User.tg_id == tg_id))).scalar_one_or_none()

        if not user:
            role = UserRole.admin if tg_id in ADMIN_IDS else UserRole.user
            session.add(User(tg_id=tg_id, role=role))
            try:
                await session.commit()
            except IntegrityError:
                await session.rollback()

            await message.answer(f"👋 Привет! Ты зарегистрирован как *{role.value}*.",
                                 parse_mode="Markdown")
        else:
            await message.answer("👋 С возвращением!")

    # сразу показываем меню админу
    if tg_id in ADMIN_IDS:
        await show_admin_menu(message)


# ---------- ADMIN MENU ----------
@dp.message(F.text == "/menu")
@admin_only
async def show_admin_menu(message: types.Message):
    await message.answer("🛠 Админ-меню", reply_markup=admin_menu())


@dp.callback_query(F.data == "admin_back")
@admin_only
async def callback_menu(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.edit_text("🛠 Админ-меню", reply_markup=admin_menu())


# ---------- USER LIST ----------
@dp.callback_query(F.data == "admin_users")
@admin_only
async def callback_users(callback: types.CallbackQuery):
    async with AsyncSessionLocal() as session:
        users = (await session.execute(select(User))).scalars().all()

    text = "🙁 Нет пользователей." if not users else \
        "📋 *Пользователи:*\n" + "\n".join(f"• `{u.tg_id}` – {u.role.value}" for u in users)

    await callback.answer()
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=admin_menu())


# ---------- ADD OBJECT (CALLBACK) ----------
@dp.callback_query(F.data == "admin_add")
@admin_only
async def admin_add_object(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await start_add_property(callback.message, state)


# ---------- FSM: ADD PROPERTY ----------
@dp.message(F.text == "/add_object")
async def start_add_property(message: types.Message, state: FSMContext):
    await state.clear()
    await state.set_state(AddProperty.location)
    await message.answer("📍 Введите локацию:", reply_markup=ReplyKeyboardRemove())


@dp.message(AddProperty.location)
async def step_location(message: types.Message, state: FSMContext):
    await state.update_data(location=message.text, media=[])
    await state.set_state(AddProperty.media)
   kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="✅ Завершить загрузку", callback_data="finish_media")]
    ])
    await message.answer("📸 Прикрепите фото/видео объекта и нажмите кнопку.", reply_markup=kb)


@dp.message(AddProperty.media, F.photo | F.video)
async def collect_media(message: types.Message, state: FSMContext):
    data = await state.get_data()
    media = data["media"]
    file_id = message.photo[-1].file_id if message.photo else message.video.file_id
    media.append(file_id)
    await state.update_data(media=media)
    await message.answer("✅ Медиа добавлено.")


@dp.callback_query(F.data == "finish_media")
async def finish_media(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(AddProperty.description)
    await callback.message.answer("🛏 Комнаты / этаж / этажность:", reply_markup=ReplyKeyboardRemove())


@dp.message(AddProperty.description)
async def step_description(message: types.Message, state: FSMContext):
    await state.update_data(description=message.text)
    await state.set_state(AddProperty.condition)
    await message.answer("🧱 Состояние объекта:")


@dp.message(AddProperty.condition)
async def step_condition(message: types.Message, state: FSMContext):
    await state.update_data(condition=message.text)
    await state.set_state(AddProperty.parking)
    await message.answer("🚗 Парковка (Подземный/Наземный/Нет):")


@dp.message(AddProperty.parking)
async def step_parking(message: types.Message, state: FSMContext):
    await state.update_data(parking=message.text)
    await state.set_state(AddProperty.bathrooms)
    await message.answer("🚽 Кол-во санузлов:")


@dp.message(AddProperty.bathrooms)
async def step_bathrooms(message: types.Message, state: FSMContext):
    await state.update_data(bathrooms=message.text)
    await state.set_state(AddProperty.additions)
    await message.answer("✏ Дополнения:")


@dp.message(AddProperty.additions)
async def step_additions(message: types.Message, state: FSMContext):
    await state.update_data(additions=message.text)
    await state.set_state(AddProperty.price)
    await message.answer("💰 Цена (в числах):")


@dp.message(AddProperty.price)
async def step_price(message: types.Message, state: FSMContext):
    await state.update_data(price=message.text)
    data = await state.get_data()

    preview = (
        f"*Предпросмотр:*\n"
        f"📍 {data['location']}\n"
        f"🛏 {data['description']}\n"
        f"🧱 {data['condition']}\n"
        f"🚗 {data['parking']}\n"
        f"🚽 {data['bathrooms']}\n"
        f"✏ {data['additions']}\n"
        f"💰 *{data['price']}*"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("✅ Сохранить", callback_data="save_object")],
        [InlineKeyboardButton("❌ Отменить", callback_data="cancel_object")]
    ])
    await state.set_state(AddProperty.confirm)
    await message.answer(preview, parse_mode="Markdown", reply_markup=kb)


@dp.callback_query(F.data == "save_object")
async def save_object(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    async with AsyncSessionLocal() as session:
        try:
            prop = Property(
                title=data["description"] or data["location"],
                description=data["description"],
                location=data["location"],
                condition=data["condition"],
                parking=data["parking"],
                bathrooms=int(data["bathrooms"]),
                additions=data["additions"],
                price=data["price"],
                created_by=callback.from_user.id
            )
            session.add(prop)
            await session.commit()
            await callback.message.edit_text(f"✅ Объект #{prop.id} успешно добавлен!")
        except SQLAlchemyError:
            await session.rollback()
            await callback.message.edit_text("❌ Ошибка при сохранении.")
    await state.clear()


@dp.callback_query(F.data == "cancel_object")
async def cancel_object(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Добавление объекта отменено.")


# ---------- ENTRY POINT ----------
if __name__ == "__main__":
    async def main():
        import models  # регистрация моделей
        await init_db()  # создаём таблицы, если ещё нет
        print("Бот запущен...")
        await dp.start_polling(bot)

    asyncio.run(main())
