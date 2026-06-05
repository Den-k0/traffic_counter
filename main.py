import logging
import os
from dotenv import load_dotenv

load_dotenv()

import cv2
from ultralytics import YOLO
from imutils.video import VideoStream

from config import Config
from utils import ImageUtils
from camera.camera_controller import SSHCameraController
from tracking.line_counter import LineCounter
from metrics.traffic_state import TrafficStateTracker
from ui.overlay import Visualizer

# Налаштування логування для всіх модулів
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger("TrafficAnalyzer")

def process_video_stream(cap: VideoStream, model: YOLO, counter: LineCounter, traffic_state: TrafficStateTracker) -> None:
    """Обробляє кадри з відеопотоку в нескінченному циклі."""
    try:
        while True:
            frame = cap.read()
            if frame is None:
                continue 
            
            # Попередня обробка кадру (зміна розміру, CLAHE)
            frame = cv2.resize(frame, (Config.FRAME_WIDTH, Config.FRAME_HEIGHT))
            frame_input = ImageUtils.apply_clahe(frame) if Config.USE_CLAHE else frame

            # Inference та трекінг
            results = model.track(
                frame_input, 
                conf=Config.CONFIDENCE_THRESHOLD, 
                iou=Config.IOU_THRESHOLD,
                persist=True, 
                tracker=Config.TRACKER_CONFIG,
                classes=Config.TARGET_CLASSES, 
                imgsz=Config.INFERENCE_SIZE,
                verbose=False
            )

            # Якщо немає результатів, пропускаємо рендеринг
            if not results or not len(results):
                continue

            # Обробка треків та оновлення лічильника
            prev_total = counter.total_objects
            events = counter.process_tracks(results[0].boxes, model.names)
            
            # Реєстрація перетину для оновлення стану трафіку
            if counter.total_objects > prev_total:
                traffic_state.register_crossing()

            # Отримання метрик для HUD
            intensity, state, state_color = traffic_state.get_metrics()

            # Рендерінґ UI та вивід кадру
            frame = Visualizer.render(
                frame, events, counter.total_objects, 
                intensity, state, state_color, counter.line_color
            )

            # Відображення кадру
            cv2.imshow("Traffic Analyzer", frame)
            
            # Вихід за натисканням 'q' або при отриманні сигналу зупинки
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    except KeyboardInterrupt:
        logger.info("Отримано сигнал зупинки (Ctrl+C)...")
    finally:
        cap.stop()
        cv2.destroyAllWindows()
        logger.info("Обробку відеопотоку завершено.")


def main() -> None:
    """Оркестратор: Ініціалізує компоненти, підключає камеру та запускає цикл."""
    logger.info("Ініціалізація системи...")

    # Ініціалізація лічильника та трекера трафіку
    counter = LineCounter(polygon=Config.ROAD_POLYGON, line_position=Config.LINE_POSITION)
    traffic_state = TrafficStateTracker(
        free_limit=Config.FREE_FLOW_LIMIT, 
        jam_limit=Config.JAM_LIMIT, 
        window_seconds=Config.INTENSITY_WINDOW_SEC
    )

    # Завантаження моделі з обробкою помилок
    try:
        model = YOLO(Config.YOLO_MODEL, task="detect")
        logger.info(f"Модель {Config.YOLO_MODEL} завантажена.")
    except Exception as e:
        logger.error(f"Помилка завантаження моделі: {e}")
        return

    # МЕНЕДЖЕР КОНТЕКСТУ: безпечне підключення та відключення камери
    try:
        with SSHCameraController(Config.RPI_IP, Config.RPI_USER, Config.RPI_PASS) as camera:
            
            # Підключення до камери та запуск трансляції
            cap = VideoStream(camera.stream_url).start()
            logger.info("Початок трансляції...")

            # Головний цикл обробки відеопотоку
            process_video_stream(cap, model, counter, traffic_state)
            
            logger.info("Роботу системи завершено.")

    except ConnectionError as e:
        logger.error(e)

if __name__ == "__main__":
    main()
