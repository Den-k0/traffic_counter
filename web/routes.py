import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.orm import Session
from typing import List

from web.db import get_db
from web.schemas import HistoricalTrafficData
from web.history_service import HistoryService
from camera.state import global_state
from config import AppConfig

router = APIRouter()

class ConnectionManager:
    """Менеджер для керування активними WebSocket з'єднаннями."""
    
    def __init__(self) -> None:
        """Ініціалізує список активних клієнтів."""
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        """Приймає підключення та додає до списку розсилки."""
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        """Видаляє підключення зі списку при відключенні клієнта."""
        self.active_connections.remove(websocket)

    async def broadcast(self, data: dict) -> None:
        """Розсилає JSON повідомлення всім підключеним клієнтам (Broadcast Pattern)."""
        for connection in self.active_connections:
            await connection.send_json(data)

manager = ConnectionManager()

async def stats_broadcaster() -> None:
    """Асинхронне фонове завдання для розсилки телеметрії.
    
    Раз на секунду зчитує глобальний стан, генерує часові мітки для графіка 
    і розсилає ці дані всім WebSocket клієнтам.
    """
    while global_state.is_running:
        if manager.active_connections:
            stats = global_state.get_stats()
            now = datetime.now(ZoneInfo(AppConfig.TIMEZONE))
            await manager.broadcast({
                "time": now.strftime("%H:%M:%S"),
                "buckets": HistoryService.get_current_buckets(now),
                "intensity": stats["intensity"],
                "total_objects": stats["total_objects"],
                "traffic_state": stats["traffic_state"],
                "total_persons": stats.get("total_persons", 0),
                "total_transport": stats.get("total_transport", 0)
            })
        await asyncio.sleep(1)

@router.on_event("startup")
async def startup_event() -> None:
    """Хук, що спрацьовує при старті FastAPI для запуску броадкастера."""
    asyncio.create_task(stats_broadcaster())

@router.get("/")
async def index() -> FileResponse:
    """Віддає головну HTML сторінку дашборду."""
    return FileResponse("web/templates/index.html")

@router.websocket("/ws/stats")
async def websocket_stats(websocket: WebSocket) -> None:
    """Ендпоінт для встановлення WebSocket з'єднання з клієнтом."""
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except (WebSocketDisconnect, asyncio.CancelledError):
        manager.disconnect(websocket)

@router.get("/video_feed")
async def video_feed(request: Request) -> StreamingResponse:
    """Ендпоінт для стрімінгу обробленого відео (MJPEG).
    
    Реєструє підключення для оптимізації рендеру відео на бекенді.
    Якщо клієнтів немає — рендер та кодування кадрів вимикається.
    """
    async def frame_generator():
        global_state.increment_viewers()
        try:
            last_sent_frame = None
            while global_state.is_running:
                if await request.is_disconnected():
                    break
                current_frame = global_state.get_frame()
                if current_frame and current_frame != last_sent_frame:
                    last_sent_frame = current_frame
                    yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + last_sent_frame + b"\r\n")
                await asyncio.sleep(0.03)
        finally:
            global_state.decrement_viewers()
            
    return StreamingResponse(frame_generator(), media_type="multipart/x-mixed-replace; boundary=frame")

@router.get("/api/history", response_model=list[HistoricalTrafficData])
async def get_historical_data(interval: str, obj_type: str = "all", db: Session = Depends(get_db)):
    """REST API ендпоінт для отримання історичних даних для графіку.

    Args:
        interval (str): Назва часового фільтра (1min, 15min, hour, etc.).
        obj_type (str): Фільтр за типом об'єкта (all, transport, person).
        db (Session): Сесія підключення до БД (впорскується автоматично).

    Returns:
        list[HistoricalTrafficData]: Список агрегованих точок даних.
    """
    return HistoryService.get_historical_data(interval=interval, obj_type=obj_type, db=db)
