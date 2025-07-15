from aiogram.fsm.state import State, StatesGroup

class AddProperty(StatesGroup):
    location = State()
    media = State()
    description = State()
    condition = State()
    parking = State()
    bathrooms = State()
    additions = State()
    price = State()
    confirm = State()
