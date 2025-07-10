from sqlalchemy import Column, Integer, BigInteger, String, Enum as PgEnum, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from db_base import Base
import enum
from datetime import datetime

# 👤 Роли пользователей
class UserRole(enum.Enum):
    admin = "admin"
    user = "user"

# 👤 Модель пользователя
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    tg_id = Column(BigInteger, unique=True, nullable=False)
    name = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    role = Column(PgEnum(UserRole), nullable=False, default=UserRole.user)

    created_at = Column(DateTime, default=datetime.utcnow)  # ⏱ Дата регистрации
    is_active = Column(Boolean, default=True)               # ✅ Статус активности

    properties = relationship("Property", back_populates="creator")  # 🔗 Связь с объектами

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
    description = Column(String)
    status = Column(PgEnum(PropertyStatus), default=PropertyStatus.available)

    created_by = Column(BigInteger, ForeignKey("users.tg_id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)  # ⏱ Дата создания объекта

    creator = relationship("User", back_populates="properties")  # 🔗 Обратная связь с пользователем
