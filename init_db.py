import asyncio
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from db_base import Base
from config import DATABASE_URL
import models  # обязательно импортируй модели!

engine: AsyncEngine = create_async_engine(DATABASE_URL, echo=True)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Таблицы успешно созданы.")

if __name__ == "__main__":
    asyncio.run(init_db())
