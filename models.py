from sqlalchemy import (
    Column, Integer, BigInteger, String,
    Enum as PgEnum, ForeignKey, DateTime
)
from sqlalchemy.orm import relationship
from db_base import Base  # Убедись, что импорт из общего файла
from datetime import datetime
import enum

# 👤 Роли пользователей
class UserRole(enum.Enum):
    admin = "admin"
    user = "user"

# 👤 Модель пользователя
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    tg_id = Column(BigInteger, unique=True, nullable=False)
    name = Column(String, nullable=True)   # имя
    phone = Column(String, nullable=True)  # номер
    role = Column(PgEnum(UserRole), nullable=False, default=UserRole.user)

    # связь с объектами
    properties = relationship("Property", back_populates="creator", cascade="all, delete")

# 📦 Статус объекта недвижимости
class PropertyStatus(enum.Enum):
    available = "В продаже"
    sold = "Продано"
    price_changed = "Снижение/Повышение цены"
    removed = "Снято с продажи"

# 🏠 Модель объекта недвижимости
class Property(Base):
    __tablename__ = "properties"

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)

    # 🏠 Характеристики объекта
    rooms = Column(String, nullable=True)
    floor = Column(String, nullable=True)
    total_floors = Column(String, nullable=True)
    area = Column(String, nullable=True)
    condition = Column(String, nullable=True)
    parking = Column(String, nullable=True)
    bathrooms = Column(Integer, nullable=True)
    additions = Column(String, nullable=True)
    price = Column(String, nullable=True)
    media_group_id = Column(String, nullable=True)

    # 🔧 Статус и автор
    status = Column(PgEnum(PropertyStatus), default=PropertyStatus.available)
    created_by = Column(BigInteger, ForeignKey("users.tg_id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # связь с создателем
    creator = relationship("User", back_populates="properties")
