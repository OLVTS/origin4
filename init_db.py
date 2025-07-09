import asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from database import engine, Base

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Таблицы успешно созданы.")

if __name__ == "__main__":
    asyncio.run(init_db())