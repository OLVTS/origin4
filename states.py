from aiogram.fsm.state import StatesGroup, State

class AddProperty(StatesGroup):
    location = State()
    description = State()
    condition = State()
    parking = State()
    bathrooms = State()
    additions = State()
    price = State()
    confirm = State()
