from sqlalchemy import Column, BigInteger, Enum
from database import Base
import enum

class UserRole(enum.Enum):
    admin = "admin"
    user = "user"

class User(Base):
    __tablename__ = "users"
    tg_id = Column(BigInteger, primary_key=True)
    role = Column(Enum(UserRole, native_enum=False), nullable=False)