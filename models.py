from sqlalchemy import Column, Integer, BigInteger, String, Enum as PgEnum, ForeignKey
from sqlalchemy.orm import declarative_base
import enum

Base = declarative_base()

# 👤 Роли пользователей
class UserRole(enum.Enum):
    admin = "admin"
    user = "user"

# 👤 Модель пользователя
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    tg_id = Column(BigInteger, unique=True, nullable=False)
    role = Column(PgEnum(UserRole), nullable=False, default=UserRole.user)

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
    
    # 👤 ID пользователя, который создал объект
    created_by = Column(BigInteger, ForeignKey("users.tg_id"), nullable=False)
