class Config:
    """
    Централізована конфігурація проєкту.
    """
    # === Шляхи ===
    VIDEO_PATH = "video.mp4" # або 0 для камери
    MODEL_PROTO = 'MobileNetSSD_deploy.prototxt'
    MODEL_WEIGHTS = 'MobileNetSSD_deploy.caffemodel'

    # === Зони та Лінії ===
    ZONE_TOP = 115       # Верхня межа (Y min)
    ZONE_BOTTOM = 300    # Нижня межа (Y max)
    LINE_POSITION = 350  # Лінія підрахунку (X)

    # === Параметри ===
    CONFIDENCE_THRESHOLD = 0.20
    USE_CLAHE = False
    FRAME_WIDTH = 640
    FRAME_HEIGHT = 360

    # === Класи ===
    ALL_CLASSES = ["background", "aeroplane", "bicycle", "bird", "boat",
                   "bottle", "bus", "car", "cat", "chair", "cow", "diningtable",
                   "dog", "horse", "motorbike", "person", "pottedplant", "sheep",
                   "sofa", "train", "tvmonitor"]

    # Фільтр об'єктів (тільки транспорт)
    VEHICLES = ["car", "bus", "motorbike", "train", "bicycle"]
