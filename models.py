# models.py

from sqlalchemy import Column, BigInteger, Enum as SQLAEnum
from db_base import Base  # ⬅️ Тоже импорт из db_base
import enum

class UserRole(enum.Enum):
    admin = "admin"
    user = "user"

class User(Base):
    __tablename__ = "users"

    tg_id = Column(BigInteger, primary_key=True)
    role = Column(SQLAEnum(UserRole), nullable=False)
