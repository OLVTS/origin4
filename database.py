from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "postgresql+asyncpg://postgres:rvFXEjFPTnnjfuMSiVqKSBweNUKhHnaf@centerbeam.proxy.rlwy.net:34016/railway"

engine = create_async_engine(DATABASE_URL, echo=False)
Base = declarative_base()

AsyncSessionLocal = sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession,
)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
