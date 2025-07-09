from aiogram import Router, F, types
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from database import AsyncSessionLocal
from models import User, UserRole
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from config import ADMIN_IDS

router = Router()

class Registration(StatesGroup):
    name = State()
    phone = State()

@router.message(F.text == "/start")
async def start_handler(message: types.Message, state: FSMContext):
    session = AsyncSessionLocal()
    stmt = select(User).where(User.tg_id == message.from_user.id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    await session.close()

    if user:
        await message.answer("👋 С возвращением! Ты уже зарегистрирован.")
    else:
        await message.answer("Привет! Давай зарегистрируемся.\n\nКак тебя зовут?")
        await state.set_state(Registration.name)

@router.message(Registration.name)
async def get_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Отправить номер", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

    await message.answer("Теперь нажми кнопку ниже и отправь свой номер телефона:", reply_markup=kb)
    await state.set_state(Registration.phone)

@router.message(Registration.phone, F.contact)
async def get_phone(message: types.Message, state: FSMContext):
    data = await state.get_data()
    name = data["name"]
    phone = message.contact.phone_number
    tg_id = message.from_user.id

    role = UserRole.admin if tg_id in ADMIN_IDS else UserRole.user

    session = AsyncSessionLocal()
    user = User(tg_id=tg_id, name=name, phone=phone, role=role)
    session.add(user)
    try:
        await session.commit()
        await message.answer("✅ Регистрация завершена!", reply_markup=ReplyKeyboardRemove())
    except IntegrityError:
        await session.rollback()
        await message.answer("❌ Ошибка при регистрации.")
    finally:
        await session.close()
        await state.clear()
