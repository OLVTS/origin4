from sqlalchemy import Column, Integer, BigInteger, String, Enum as PgEnum, ForeignKey
from db_base import Base  # <-- ВАЖНО: импорт из db_base
import enum

# 👤 Роли пользователей
class UserRole(enum.Enum):
    admin = "admin"
    user = "user"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    tg_id = Column(BigInteger, unique=True, nullable=False)
    role = Column(PgEnum(UserRole), nullable=False, default=UserRole.user)

class PropertyStatus(enum.Enum):
    available = "В продаже"
    sold = "Продано"
    price_changed = "Снижение/Повышение цены"
    removed = "Снято с продажи"

class Property(Base):
    __tablename__ = "properties"

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(String)
    status = Column(PgEnum(PropertyStatus), default=PropertyStatus.available)
    created_by = Column(BigInteger, ForeignKey("users.tg_id"), nullable=False)
