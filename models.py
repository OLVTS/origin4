from sqlalchemy import (
    Column, Integer, BigInteger, String,
    Enum as PgEnum, ForeignKey, DateTime, Numeric
)
from sqlalchemy.orm import relationship
from db_base import Base
from datetime import datetime
import enum


# ---------- ENUMS ----------
class UserRole(enum.Enum):
    admin = "admin"
    user = "user"

class PropertyStatus(enum.Enum):
    available = "В продаже"
    sold = "Продано"
    price_changed = "Снижение/Повышение цены"
    removed = "Снято с продажи"


# ---------- USER ----------
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    tg_id = Column(BigInteger, unique=True, nullable=False)
    name = Column(String)
    phone = Column(String)
    role = Column(PgEnum(UserRole), nullable=False, default=UserRole.user)
    created_at = Column(DateTime, default=datetime.utcnow)

    properties = relationship(
        "Property",
        back_populates="creator",
        cascade="all, delete-orphan"
    )


# ---------- PROPERTY ----------
class Property(Base):
    __tablename__ = "properties"

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(String)

    # характеристики
    location = Column(String)
    rooms = Column(String)
    floor = Column(String)
    total_floors = Column(String)
    area = Column(Numeric)
    condition = Column(String)
    parking = Column(String)
    bathrooms = Column(Integer)
    additions = Column(String)
    price = Column(Numeric)

    media_group_id = Column(String)

    status = Column(PgEnum(PropertyStatus), default=PropertyStatus.available)
    created_by = Column(BigInteger, ForeignKey("users.tg_id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    creator = relationship("User", back_populates="properties")
