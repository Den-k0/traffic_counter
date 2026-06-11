"""Схеми Pydantic для валідації та серіалізації даних API."""
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from web.models import TrafficStatus, ObjectType


class TrafficLogBase(BaseModel):
    """Базова схема логування трафіку."""
    object_class: ObjectType
    traffic_state: TrafficStatus


class TrafficLogCreate(TrafficLogBase):
    """Схема для створення нового запису."""
    pass


class TrafficLogResponse(TrafficLogBase):
    """Схема відповіді API з деталями перетину."""
    id: int
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class HistoricalTrafficData(BaseModel):
    """Схема агрегованих даних для побудови графіка на фронтенді.

    Attributes:
        timestamp_group (str): Згрупована мітка часу
                               (наприклад, '14:00' або '15.06').
        total_objects (int): Сумарна кількість об'єктів за цей бакет часу.
        average_intensity (float): Середня інтенсивність (швидкість потоку).
        dominant_state (str): Найчастіший стан трафіку у цьому бакеті
                              (FREE/NORMAL/HEAVY).
    """
    timestamp_group: str
    total_objects: int
    average_intensity: float
    dominant_state: str
