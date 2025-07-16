import asyncio
from functools import wraps
from aiogram import Bot, Dispatcher, F, types
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from sqlalchemy import select, delete
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
import logging

from config import BOT_TOKEN, ADMIN_IDS, CHANNEL_USERNAME
from database import AsyncSessionLocal, init_db
from models import User, UserRole, Property, PropertyStatus
from states import AddProperty, EditProperty

logging.basicConfig(level=logging.INFO)
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
        [InlineKeyboardButton(text="📋 Список пользователей", callback_data="admin_users")],
        [InlineKeyboardButton(text="🏠 Все объекты", callback_data="admin_properties")],
        [InlineKeyboardButton(text="📄 Добавить объект", callback_data="admin_add")],
        [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="admin_back")]
    ])

def property_actions(property_id: int, is_admin: bool = False) -> InlineKeyboardMarkup:
    buttons = [[InlineKeyboardButton(text="✏ Редактировать", callback_data=f"edit_property_{property_id}")]]
    if is_admin:
        buttons.append([InlineKeyboardButton(text="🗑 Удалить", callback_data=f"delete_property_{property_id}")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="my_objects" if not is_admin else "admin_properties")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

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

            await message.answer(f"👋 Привет! Ты зарегистрирован как *{role.value}*.\n"
                                "Используй /add_object для добавления объекта или /my_objects для просмотра своих объектов.",
                                parse_mode="Markdown")
        else:
            await message.answer("👋 С возвращением!\n"
                                "Используй /add_object для добавления объекта или /my_objects для просмотра своих объектов.",
                                parse_mode="Markdown")

        if tg_id in ADMIN_IDS:
            await message.answer("🛠 Админ-меню", reply_markup=admin_menu())

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

# ---------- PROPERTY LIST (USER) ----------
@dp.message(F.text == "/my_objects")
async def my_objects(message: types.Message):
    tg_id = message.from_user.id
    async with AsyncSessionLocal() as session:
        properties = (await session.execute(select(Property).where(Property.created_by == tg_id))).scalars().all()

    if not properties:
        await message.answer("🙁 У вас нет объектов. Добавьте новый с помощью /add_object.")
        return

    for prop in properties:
        text = (
            f"*Объект #{prop.id}*\n"
            f"📍 {prop.location}\n"
            f"🛏 {prop.description}\n"
            f"🧱 {prop.condition}\n"
            f"🚗 {prop.parking}\n"
            f"🚽 {prop.bathrooms}\n"
            f"✏ {prop.additions}\n"
            f"💰 *{prop.price}*"
        )
        await message.answer(text, parse_mode="Markdown", reply_markup=property_actions(prop.id))

# ---------- PROPERTY LIST (ADMIN) ----------
@dp.callback_query(F.data == "admin_properties")
@admin_only
async def admin_properties(callback: types.CallbackQuery):
    async with AsyncSessionLocal() as session:
        properties = (await session.execute(select(Property))).scalars().all()

    if not properties:
        await callback.message.edit_text("🙁 Нет объектов.", reply_markup=admin_menu())
        return

    for prop in properties:
        text = (
            f"*Объект #{prop.id}* (создал: `{prop.created_by}`)\n"
            f"📍 {prop.location}\n"
            f"🛏 {prop.description}\n"
            f"🧱 {prop.condition}\n"
            f"🚗 {prop.parking}\n"
            f"🚽 {prop.bathrooms}\n"
            f"✏ {prop.additions}\n"
            f"💰 *{prop.price}*"
        )
        await callback.message.answer(text, parse_mode="Markdown", reply_markup=property_actions(prop.id, is_admin=True))
    await callback.answer()

# ---------- ADD OBJECT ----------
@dp.message(F.text == "/add_object")
async def start_add_property(message: types.Message, state: FSMContext):
    async with AsyncSessionLocal() as session:
        user = (await session.execute(select(User).where(User.tg_id == message.from_user.id))).scalar_one_or_none()
        if not user:
            await message.answer("🚫 Вы не зарегистрированы. Используй /start для регистрации.")
            return
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
    try:
        int(message.text)  # Валидация
        await state.update_data(bathrooms=message.text)
        await state.set_state(AddProperty.additions)
        await message.answer("✏ Дополнения:")
    except ValueError:
        await message.answer("❌ Пожалуйста, введите число для количества санузлов.")

@dp.message(AddProperty.additions)
async def step_additions(message: types.Message, state: FSMContext):
    await state.update_data(additions=message.text)
    await state.set_state(AddProperty.price)
    await message.answer("💰 Цена (в числах):")

@dp.message(AddProperty.price)
async def step_price(message: types.Message, state: FSMContext):
    try:
        float(message.text)  # Валидация
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
            [InlineKeyboardButton(text="✅ Сохранить", callback_data="save_object")],
            [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_object")]
        ])
        await state.set_state(AddProperty.confirm)
        await message.answer(preview, parse_mode="Markdown", reply_markup=kb)
    except ValueError:
        await message.answer("❌ Пожалуйста, введите цену в числах.")

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
                media_group_id=",".join(data.get("media", [])),  # Сохраняем file_id медиа
                created_by=callback.from_user.id
            )
            session.add(prop)
            await session.commit()

            # Публикация в канал
            message_text = (
                f"*Новый объект #{prop.id}*\n"
                f"📍 {data['location']}\n"
                f"🛏 {data['description']}\n"
                f"🧱 {data['condition']}\n"
                f"🚗 {data['parking']}\n"
                f"🚽 {data['bathrooms']}\n"
                f"✏ {data['additions']}\n"
                f"💰 *{data['price']}*"
            )
            media = data.get("media", [])
            if media:
                from aiogram.types import InputMediaPhoto, InputMediaVideo
                media_group = []
                for file_id in media:
                    media_group.append(InputMediaPhoto(media=file_id) if file_id.startswith("Ag") else InputMediaVideo(media=file_id))
                await bot.send_media_group(chat_id=CHANNEL_USERNAME, media=media_group)
                await bot.send_message(chat_id=CHANNEL_USERNAME, text=message_text, parse_mode="Markdown")
            else:
                await bot.send_message(chat_id=CHANNEL_USERNAME, text=message_text, parse_mode="Markdown")

            await callback.message.edit_text(f"✅ Объект #{prop.id} успешно добавлен и опубликован в канале!")
        except SQLAlchemyError as e:
            await session.rollback()
            await callback.message.edit_text(f"❌ Ошибка при сохранении: {str(e)}")
        except Exception as e:
            await callback.message.edit_text(f"❌ Ошибка при отправке в канал: {str(e)}")
    await state.clear()

@dp.callback_query(F.data == "cancel_object")
async def cancel_object(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Добавление объекта отменено.")

# ---------- EDIT PROPERTY ----------
@dp.callback_query(F.data.startswith("edit_property_"))
async def start_edit_property(callback: types.CallbackQuery, state: FSMContext):
    property_id = int(callback.data.split("_")[-1])
    async with AsyncSessionLocal() as session:
        prop = (await session.execute(select(Property).where(Property.id == property_id))).scalar_one_or_none()
        if not prop:
            await callback.message.edit_text("❌ Объект не найден.")
            return
        if prop.created_by != callback.from_user.id and callback.from_user.id not in ADMIN_IDS:
            await callback.message.edit_text("🚫 Вы не можете редактировать этот объект.")
            return

    await state.update_data(property_id=property_id)
    await state.set_state(EditProperty.field)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📍 Локация", callback_data="edit_field_location")],
        [InlineKeyboardButton(text="🛏 Описание", callback_data="edit_field_description")],
        [InlineKeyboardButton(text="🧱 Состояние", callback_data="edit_field_condition")],
        [InlineKeyboardButton(text="🚗 Парковка", callback_data="edit_field_parking")],
        [InlineKeyboardButton(text="🚽 Санузлы", callback_data="edit_field_bathrooms")],
        [InlineKeyboardButton(text="✏ Дополнения", callback_data="edit_field_additions")],
        [InlineKeyboardButton(text="💰 Цена", callback_data="edit_field_price")],
        [InlineKeyboardButton(text="📸 Медиа", callback_data="edit_field_media")],
        [InlineKeyboardButton(text="✅ Завершить", callback_data="finish_edit")]
    ])
    await callback.message.edit_text("✏ Выберите поле для редактирования:", reply_markup=kb)
    await callback.answer()

@dp.callback_query(F.data.startswith("edit_field_"))
async def edit_field(callback: types.CallbackQuery, state: FSMContext):
    field = callback.data.split("_")[-1]
    await state.update_data(edit_field=field)
    await state.set_state(EditProperty.value)
    field_names = {
        "location": "локацию",
        "description": "описание",
        "condition": "состояние",
        "parking": "парковку",
        "bathrooms": "количество санузлов",
        "additions": "дополнения",
        "price": "цену",
        "media": "медиа (прикрепите новые файлы)"
    }
    await callback.message.answer(f"Введите новое значение для {field_names[field]}:", reply_markup=ReplyKeyboardRemove())
    await callback.answer()

@dp.message(EditProperty.value)
async def save_field(message: types.Message, state: FSMContext):
    data = await state.get_data()
    property_id = data["property_id"]
    field = data["edit_field"]

    async with AsyncSessionLocal() as session:
        prop = (await session.execute(select(Property).where(Property.id == property_id))).scalar_one_or_none()
        if not prop:
            await message.answer("❌ Объект не найден.")
            return

        try:
            if field == "bathrooms":
                int(message.text)  # Валидация
            elif field == "price":
                float(message.text)  # Валидация
            elif field == "media":
                await message.answer("❌ Используйте кнопку для загрузки медиа.")
                return

            setattr(prop, field, message.text)
            await session.commit()
            await message.answer(f"✅ Поле {field} обновлено!")
        except ValueError:
            await message.answer(f"❌ Пожалуйста, введите корректное значение для {field}.")
            return
        except SQLAlchemyError:
            await session.rollback()
            await message.answer("❌ Ошибка при сохранении.")

@dp.message(EditProperty.value, F.photo | F.video)
async def save_media(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if data["edit_field"] != "media":
        await message.answer("❌ Используйте кнопку для изменения других полей.")
        return

    property_id = data["property_id"]
    file_id = message.photo[-1].file_id if message.photo else message.video.file_id

    async with AsyncSessionLocal() as session:
        prop = (await session.execute(select(Property).where(Property.id == property_id))).scalar_one_or_none()
        if not prop:
            await message.answer("❌ Объект не найден.")
            return

        try:
            media = prop.media_group_id.split(",") if prop.media_group_id else []
            media.append(file_id)
            prop.media_group_id = ",".join(media)
            await session.commit()
            await message.answer("✅ Медиа добавлено!")
        except SQLAlchemyError:
            await session.rollback()
            await message.answer("❌ Ошибка при сохранении.")

@dp.callback_query(F.data == "finish_edit")
async def finish_edit(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    property_id = data.get("property_id")
    async with AsyncSessionLocal() as session:
        prop = (await session.execute(select(Property).where(Property.id == property_id))).scalar_one_or_none()
        if not prop:
            await callback.message.edit_text("❌ Объект не найден.")
            return

        text = (
            f"*Объект #{prop.id}*\n"
            f"📍 {prop.location}\n"
            f"🛏 {prop.description}\n"
            f"🧱 {prop.condition}\n"
            f"🚗 {prop.parking}\n"
            f"🚽 {prop.bathrooms}\n"
            f"✏ {prop.additions}\n"
            f"💰 *{prop.price}*"
        )
        await callback.message.edit_text(f"✅ Редактирование завершено:\n{text}", parse_mode="Markdown",
                                         reply_markup=property_actions(prop.id, is_admin=callback.from_user.id in ADMIN_IDS))
    await state.clear()
    await callback.answer()

# ---------- DELETE PROPERTY (ADMIN) ----------
@dp.callback_query(F.data.startswith("delete_property_"))
@admin_only
async def delete_property(callback: types.CallbackQuery):
    property_id = int(callback.data.split("_")[-1])
    async with AsyncSessionLocal() as session:
        try:
            await session.execute(delete(Property).where(Property.id == property_id))
            await session.commit()
            await callback.message.edit_text(f"✅ Объект #{property_id} удалён!", reply_markup=admin_menu())
        except SQLAlchemyError:
            await session.rollback()
            await callback.message.edit_text("❌ Ошибка при удалении.")
    await callback.answer()

# ---------- ENTRY POINT ----------
if __name__ == "__main__":
    async def main():
        import models  # регистрация моделей
        await init_db()  # создаём таблицы
        logging.info("Бот запущен...")
        await dp.start_polling(bot)

    asyncio.run(main())
