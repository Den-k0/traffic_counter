import numpy as np

class Config:
    """Централізована конфігурація проєкту."""
    
    VIDEO_PATH = "tcp://raspberrypi.local:8888"
    YOLO_MODEL = "yolov8m.mlpackage" # CoreML формат

    # === Полігон дороги (Polygon ROI) ===
    ROAD_POLYGON = np.array([
        [0, 170],     # Верхній лівий край
        [640, 170],   # Верхній правий край
        [640, 340],   # Нижній правий край
        [0, 340]      # Нижній лівий край
    ], np.int32)

    LINE_POSITION = 380  # Лінія підрахунку по осі X

    # === Параметри ===
    CONFIDENCE_THRESHOLD = 0.25
    USE_CLAHE = False
    FRAME_WIDTH = 640
    FRAME_HEIGHT = 360

    # Класи: 0 (пішохід), 2 (авто), 3 (мотоцикл), 5 (автобус), 7 (вантажівка)
    TARGET_CLASSES = [0, 2, 3, 5, 7]

    # === Параметри завантаженості ===
    FREE_FLOW_LIMIT = 10 # До 10 авто/хв - вільно
    JAM_LIMIT = 25 # Від 10 до 25 - ускладнено, більше - затор
