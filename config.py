import os
import numpy as np

class Config:
    """Набір констант для швидкого налаштування застосунку."""
    
    # SSH та Доступи
    RPI_IP: str = os.getenv("RPI_IP", "")
    RPI_USER: str = os.getenv("RPI_USER", "")
    RPI_PASS: str = os.getenv("RPI_PASS", "")
    
    # Мережа та Стрім
    STREAM_PORT: int = 8888
    STREAM_TIMEOUT: int = 15
    
    # ML Модель
    YOLO_MODEL: str = "yolov8l.mlpackage" 
    CONFIDENCE_THRESHOLD: float = 0.25
    IOU_THRESHOLD: float = 0.4
    INFERENCE_SIZE: int = 640
    TRACKER_CONFIG: str = "custom_tracker.yaml"
    TARGET_CLASSES: list[int] = [0, 2, 3, 5, 7] 
    
    # Геометрія (ROI)
    FRAME_WIDTH: int = 640
    FRAME_HEIGHT: int = 360
    LINE_POSITION: int = 380
    ROAD_POLYGON: np.ndarray = np.array([
        [0, 170],     
        [640, 170],   
        [640, 340],   
        [0, 340]      
    ], np.int32)

    # Параметри зображення
    USE_CLAHE: bool = False

    # Логіка трафіку
    FREE_FLOW_LIMIT: int = 10
    JAM_LIMIT: int = 25
    INTENSITY_WINDOW_SEC: int = 60
