"""Конфігураційний модуль застосунку.

Використовує pydantic-settings для безпечного завантаження змінних оточення
та звичайні класи для організації конфігураційного простору імен (namespaces).
"""
import numpy as np
from pydantic_settings import BaseSettings, SettingsConfigDict


class EnvSettings(BaseSettings):
    """Схема валідації змінних оточення з файлу .env.
    
    Гарантує (Fail-Fast), що застосунок не запуститься
    без обов'язкових облікових даних до Raspberry Pi.
    """
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8", 
        extra="ignore"
    )
    
    rpi_ip: str
    rpi_user: str
    rpi_pass: str

env = EnvSettings()


class SSHConfig:
    """SSH доступи до Raspberry Pi."""
    RPI_IP: str = env.rpi_ip
    RPI_USER: str = env.rpi_user
    RPI_PASS: str = env.rpi_pass


class StreamConfig:
    """Мережеві налаштування відеотрансляції."""
    STREAM_PORT: int = 8888
    STREAM_TIMEOUT: int = 15


class MLConfig:
    """Налаштування нейромережі (YOLO) та параметри трекера."""
    YOLO_MODEL: str = "yolov8m.mlpackage"
    CONFIDENCE_THRESHOLD: float = 0.25
    IOU_THRESHOLD: float = 0.4
    INFERENCE_SIZE: int = 640
    TRACKER_CONFIG: str = "custom_tracker.yaml"
    # 0 - людина, 2 - авто, 3 - мото, 5 - автобус, 7 - вантажівка
    TARGET_CLASSES: list[int] = [0, 2, 3, 5, 7]


class TrafficConfig:
    """Логіка підрахунку та визначення станів трафіку."""
    FREE_FLOW_LIMIT: int = 10
    JAM_LIMIT: int = 25
    INTENSITY_WINDOW_SEC: int = 60


class GeometryConfig:
    """Геометрія кадру (ROI) та параметри обробки зображення."""
    FRAME_WIDTH: int = 640
    FRAME_HEIGHT: int = 360
    LINE_POSITION: int = 350
    ROAD_POLYGON: np.ndarray = np.array([
        [0, 160],   # Верхній лівий кут
        [640, 160], # Верхній правий кут
        [640, 330], # Нижній правий кут
        [0, 330]    # Нижній лівий кут
    ], np.int32)


class AppConfig:
    """Загальні налаштування бекенд-застосунку."""
    TIMEZONE: str = "Europe/Kyiv"
