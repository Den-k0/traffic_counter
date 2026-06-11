import threading
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import logging

from camera.state import global_state
from camera.video_processor import VideoPipeline
from web.workers import db_writer_worker
from web.routes import router
from web.db import SessionLocal
from web.models import TrafficLog, ObjectType
from config import TrafficConfig

logger = logging.getLogger("TrafficAnalyzer.App")


def fetch_initial_stats_from_db():
    """Вивантажує початкову статистику з бази даних при старті сервера.

    Необхідно для відновлення роботи системи після перезапуску (щоб не скидати
    лічильники в 0). Читає загальну кількість та перетини за останню хвилину.

    Returns:
        tuple:
            - Словник із ключами total, persons, transport.
            - Список float таймстемпів перетинів за останню хвилину.
    """
    try:
        with SessionLocal() as db:
            initial_total = db.query(TrafficLog).count()
            initial_persons = db.query(TrafficLog).filter(
                TrafficLog.object_class == ObjectType.PERSON
            ).count()
            initial_transport = initial_total - initial_persons

            one_min_ago = datetime.now(ZoneInfo("UTC")) - timedelta(
                seconds=TrafficConfig.INTENSITY_WINDOW_SEC
            )
            recent_logs = db.query(TrafficLog).filter(
                TrafficLog.timestamp >= one_min_ago
            ).all()
            crossing_timestamps = [
                log.timestamp.timestamp() for log in recent_logs
            ]

            return {
                "total": initial_total,
                "persons": initial_persons,
                "transport": initial_transport
            }, crossing_timestamps
    except Exception as e:
        logger.error(f"Помилка ініціалізації з БД: {e}")
        return {"total": 0, "persons": 0, "transport": 0}, []

bg_threads = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Керує життєвим циклом (Startup/Shutdown) FastAPI застосунку.

    Оркеструє запуск та коректне завершення фонових потоків (відео та БД).

    Args:
        app (FastAPI): Інстанс FastAPI.
    """
    global_state.is_running = True

    initial_totals, initial_timestamps = fetch_initial_stats_from_db()

    try:
        pipeline = VideoPipeline(initial_totals, initial_timestamps)
    except Exception as e:
        logger.critical(f"Не вдалося запустити VideoPipeline: {e}")
        yield
        return

    bg_threads['video'] = threading.Thread(target=pipeline.run, daemon=True)
    bg_threads['db'] = threading.Thread(target=db_writer_worker, daemon=True)

    bg_threads['video'].start()
    bg_threads['db'].start()

    yield

    global_state.is_running = False

    if 'video' in bg_threads:
        bg_threads['video'].join(timeout=5.0)
    if 'db' in bg_threads:
        bg_threads['db'].join(timeout=5.0)

app = FastAPI(title="Traffic Counter API", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="web/static"), name="static")
app.include_router(router)
