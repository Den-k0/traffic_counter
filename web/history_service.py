from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException
from typing import Callable, Tuple

from web.models import TrafficLog, TrafficStatus, ObjectType
from web.schemas import HistoricalTrafficData
from config import AppConfig


class HistoryService:
    """Сервіс для агрегації історичних даних трафіку з бази даних."""

    @staticmethod
    def _get_interval_config(
        interval: str, now_local: datetime
    ) -> Tuple[datetime, timedelta, Callable[[datetime], str], str]:
        """Визначає параметри групування даних
        для SQL запиту залежно від обраного інтервалу.

        Args:
            interval (str): Назва інтервалу (1min, hour, day, week, etc.).
            now_local (datetime): Поточний локальний час.

        Returns:
            Tuple[datetime, timedelta, Callable, str]:
                - Час початку вибірки.
                - Крок часу для генерації порожніх бакетів.
                - Функція для форматування дати у мітку (Label).
                - Формат дати для SQL функції strftime.

        Raises:
            HTTPException: Якщо передано невалідний інтервал.
        """
        if interval == "1min":
            return (
                now_local - timedelta(minutes=15),
                timedelta(minutes=1),
                lambda dt: dt.strftime("%H:%M"), '%Y-%m-%d %H:%M'
            )
        elif interval == "15min":
            return (
                now_local - timedelta(hours=4),
                timedelta(minutes=15),
                lambda dt: f"{dt.hour:02d}:{(dt.minute // 15) * 15:02d}",
                '%Y-%m-%d %H:%M'
            )
        elif interval == "hour":
            return (
                now_local - timedelta(hours=24),
                timedelta(hours=1),
                lambda dt: dt.strftime("%H:00"),
                '%Y-%m-%d %H:00'
            )
        elif interval == "day":
            return (
                now_local - timedelta(days=7),
                timedelta(days=1),
                lambda dt: dt.strftime("%d.%m"),
                '%Y-%m-%d'
            )
        elif interval == "week":
            def get_week_label(dt: datetime) -> str:
                monday = dt - timedelta(days=dt.weekday())
                sunday = monday + timedelta(days=6)
                return f"{monday.strftime('%d.%m')}-{sunday.strftime('%d.%m')}"
            return (
                now_local - timedelta(weeks=4),
                timedelta(days=7),
                get_week_label,
                '%Y-%m-%d'
            )
        elif interval == "month":
            return (
                now_local - timedelta(days=365),
                timedelta(days=20),
                lambda dt: dt.strftime("%m.%Y"),
                '%Y-%m'
            )
        elif interval == "year":
            return (
                now_local - timedelta(days=365 * 5),
                timedelta(days=100),
                lambda dt: dt.strftime("%Y"),
                '%Y'
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid interval specified"
            )

    @staticmethod
    def get_historical_data(
        interval: str, obj_type: str, db: Session
    ) -> list[HistoricalTrafficData]:
        """Витягує та агрегує історичні дані трафіку для графіка.

        Використовує SQL GROUP BY для оптимізації пам'яті
        (замість вивантаження всіх записів).

        Args:
            interval (str): Часовий інтервал угруповання.
            obj_type (str): Тип об'єкта для фільтрації
                            ('all', 'person', 'transport').
            db (Session): Сесія SQLAlchemy.

        Returns:
            list[HistoricalTrafficData]: Список агрегованих даних для
                                         побудови графіка на фронтенді.
        """
        tz_local = ZoneInfo(AppConfig.TIMEZONE)
        now_local = datetime.now(tz_local)

        start_time_local, step, get_bucket_key, sql_fmt = (
            HistoryService._get_interval_config(interval, now_local)
        )
        start_time_utc = start_time_local.astimezone(ZoneInfo("UTC"))

        labels = []
        curr = start_time_local
        while curr <= now_local:
            labels.append(get_bucket_key(curr))
            curr += step
        labels.append(get_bucket_key(now_local))
        labels = list(dict.fromkeys(labels))

        grouped_data = {label: {"total": 0, "states": {}} for label in labels}

        query = db.query(
            func.strftime(sql_fmt, TrafficLog.timestamp).label('bucket'),
            TrafficLog.traffic_state,
            func.count(TrafficLog.id).label('count')
        ).filter(TrafficLog.timestamp >= start_time_utc)

        if obj_type == "person":
            query = query.filter(TrafficLog.object_class == ObjectType.PERSON)
        elif obj_type == "transport":
            query = query.filter(TrafficLog.object_class != ObjectType.PERSON)

        query = query.group_by('bucket', TrafficLog.traffic_state)
        db_results = query.all()

        parse_fmt_map = {
            '%Y-%m-%d %H:%M': '%Y-%m-%d %H:%M',
            '%Y-%m-%d %H:00': '%Y-%m-%d %H:00',
            '%Y-%m-%d': '%Y-%m-%d',
            '%Y-%m': '%Y-%m',
            '%Y': '%Y'
        }
        parse_fmt = parse_fmt_map[sql_fmt]

        for bucket_str, state, count in db_results:
            if not bucket_str:
                continue

            dt_utc = datetime.strptime(bucket_str, parse_fmt).replace(
                tzinfo=ZoneInfo("UTC")
            )
            dt_local = dt_utc.astimezone(tz_local)
            time_key = get_bucket_key(dt_local)

            if time_key in grouped_data:
                grouped_data[time_key]["total"] += count
                grouped_data[time_key]["states"][state] = (
                    grouped_data[time_key]["states"].get(state, 0) + count
                )

        results = []
        for time_key in labels:
            data = grouped_data[time_key]
            states = data["states"]

            dominant = max(
                states, key=states.get
            ) if states else TrafficStatus.FREE
            state_str = dominant.value if isinstance(
                dominant, TrafficStatus
            ) else dominant

            results.append(HistoricalTrafficData(
                timestamp_group=time_key,
                total_objects=data["total"],
                average_intensity=float(data["total"]),
                dominant_state=state_str
            ))

        return results

    @staticmethod
    def get_current_buckets(now: datetime) -> dict:
        """Генерує готові мітки часу для всіх можливих фільтрів фронтенда.

        Використовується WebSocket-броадкастером
        для реалізації патерну Backend-Driven UI.

        Args:
            now (datetime): Поточний локальний час сервера.

        Returns:
            dict: Словник з готовими відформатованими мітками для графіку.
        """
        monday = now - timedelta(days=now.weekday())
        sunday = monday + timedelta(days=6)
        return {
            "1min": now.strftime("%H:%M"),
            "15min": f"{now.hour:02d}:{(now.minute // 15) * 15:02d}",
            "hour": now.strftime("%H:00"),
            "day": now.strftime("%d.%m"),
            "week": f"{monday.strftime('%d.%m')}-{sunday.strftime('%d.%m')}",
            "month": now.strftime("%m.%Y"),
            "year": now.strftime("%Y")
        }
