import asyncio
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from db_base import Base  # Здесь находится Base = declarative_base()
from config import DATABASE_URL  # Убедись, что этот URL подключается к PostgreSQL

# Создание движка
engine: AsyncEngine = create_async_engine(DATABASE_URL, echo=True)

async def init_db():
    async with engine.begin() as conn:
        # Создание всех таблиц на основе моделей, зарегистрированных в Base
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Таблицы успешно созданы.")

if __name__ == "__main__":
    asyncio.run(init_db())
