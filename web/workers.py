import logging
import queue
from camera.state import global_state
from web.db import SessionLocal
from web.models import TrafficLog

logger = logging.getLogger("TrafficAnalyzer.Worker")

def db_writer_worker() -> None:
    """Ізольований фоновий потік для пакетного запису в базу даних.
    
    Читає події з черги `global_state.log_queue` та виконує масовий (batch) 
    insert у базу даних SQLite. Гарантує, що операції I/O з базою не блокують 
    комп'ютерний зір.
    """
    logger.info("Фоновий потік БД запущено.")

    while global_state.is_running or not global_state.log_queue.empty():
        try:
            item = global_state.log_queue.get(timeout=0.5)
            batch = [item]

            while not global_state.log_queue.empty():
                try:
                    batch.append(global_state.log_queue.get_nowait())
                except queue.Empty:
                    break

            with SessionLocal() as db:
                try:
                    for obj_class, traffic_state in batch:
                        db.add(TrafficLog(object_class=obj_class, traffic_state=traffic_state))
                    db.commit()
                except Exception as e:
                    logger.error(f"Помилка фонового запису в БД: {e}")
                    db.rollback()

        except queue.Empty:
            continue

    logger.info("Фоновий потік БД успішно зупинено.")
