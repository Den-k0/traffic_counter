import numpy as np

class Config:
    """Набір констант для швидкого налаштування застосунку."""
    
    # Мережа та Стрім
    STREAM_PORT = 8888
    STREAM_TIMEOUT = 15
    
    # ML Модель
    YOLO_MODEL = "yolov8l.mlpackage" 
    CONFIDENCE_THRESHOLD = 0.25
    IOU_THRESHOLD = 0.4
    INFERENCE_SIZE = 640
    TRACKER_CONFIG = "custom_tracker.yaml"
    TARGET_CLASSES = [0, 2, 3, 5, 7] 
    
    # Геометрія (ROI)
    FRAME_WIDTH = 640
    FRAME_HEIGHT = 360
    LINE_POSITION = 380
    ROAD_POLYGON = np.array([
        [0, 170],     
        [640, 170],   
        [640, 340],   
        [0, 340]      
    ], np.int32)

    # Параметри зображення
    USE_CLAHE = False

    # Логіка трафіку
    FREE_FLOW_LIMIT = 10
    JAM_LIMIT = 25
    INTENSITY_WINDOW_SEC = 60
