"""Моделі бази даних (SQLAlchemy) та перерахування (Enums) системи."""
import enum
from datetime import datetime
from zoneinfo import ZoneInfo
from sqlalchemy.orm import Mapped, mapped_column
from web.db import Base

class TrafficStatus(str, enum.Enum):
    """Стани завантаженості дороги."""
    FREE = "FREE"
    NORMAL = "NORMAL"
    HEAVY = "HEAVY"

class ObjectType(str, enum.Enum):
    """Типи об'єктів, які розпізнає нейромережа."""
    PERSON = "PERSON"         # клас 0
    CAR = "CAR"               # клас 2
    MOTORCYCLE = "MOTORCYCLE" # клас 3
    BUS = "BUS"               # клас 5
    TRUCK = "TRUCK"           # клас 7

class TrafficLog(Base):
    """Модель ORM для таблиці логів трафіку.
    
    Кожен запис — це один зафіксований перетин контрольної лінії.
    """
    __tablename__ = "traffic_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    
    timestamp: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(ZoneInfo("UTC"))
    )
    
    object_class: Mapped[ObjectType] = mapped_column(index=True)
    traffic_state: Mapped[TrafficStatus] = mapped_column(index=True)
