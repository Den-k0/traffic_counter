import cv2
import logging
import os
from dotenv import load_dotenv
from ultralytics import YOLO
from imutils.video import VideoStream

from config import Config
from utils import ImageUtils
from camera.camera_controller import SSHCameraController
from tracking.line_counter import LineCounter
from metrics.traffic_state import TrafficStateTracker
from ui.overlay import Visualizer

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger("TrafficAnalyzer")

def main():
    """Запускає основний цикл обробки відео.

    Ініціалізує компоненти (лічильник, трекер стану),
    завантажує модель і читає кадри з `SSHCameraController`.
    При натисненні 'q' або KeyboardInterrupt виконує коректний shutdown.
    """
    logger.info("Ініціалізація системи...")
    load_dotenv()

    # Створюємо об'єкти конфігурації
    counter = LineCounter(polygon=Config.ROAD_POLYGON, line_position=Config.LINE_POSITION)
    traffic_state = TrafficStateTracker(
        free_limit=Config.FREE_FLOW_LIMIT, 
        jam_limit=Config.JAM_LIMIT, 
        window_seconds=Config.INTENSITY_WINDOW_SEC
    )

    # Завантаження моделі
    try:
        model = YOLO(Config.YOLO_MODEL, task="detect")
        logger.info(f"Модель {Config.YOLO_MODEL} завантажена.")
    except Exception as e:
        logger.error(f"Помилка завантаження моделі: {e}")
        return

    # МЕНЕДЖЕР КОНТЕКСТУ: Камера автоматично вимкнеться, коли ми вийдемо з блоку `with`
    try:
        with SSHCameraController(os.getenv("RPI_IP"), os.getenv("RPI_USER"), os.getenv("RPI_PASS")) as camera:
            
            cap = VideoStream(camera.stream_url).start()
            logger.info("Початок обробки відео...")

            try:
                while True:
                    frame = cap.read()
                    if frame is None:
                        continue 

                    frame = cv2.resize(frame, (Config.FRAME_WIDTH, Config.FRAME_HEIGHT))
                    frame_input = ImageUtils.apply_clahe(frame) if Config.USE_CLAHE else frame

                    # Inference
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

                    # Захист від порожнього результату (якщо кадр пошкоджено)
                    if not results or not len(results):
                        continue

                    # Оновлення логіки підрахунку
                    prev_total = counter.total_objects
                    events = counter.process_tracks(results[0].boxes, model.names)
                    
                    # Якщо кількість змінилася, реєструємо перетин у таймстемпах
                    if counter.total_objects > prev_total:
                        traffic_state.register_crossing()

                    # Отримання метрик
                    intensity, state, state_color = traffic_state.get_metrics()

                    # Рендерінґ
                    frame = Visualizer.render(
                        frame, events, counter.total_objects, 
                        intensity, state, state_color, counter.line_color
                    )

                    cv2.imshow("Traffic Analyzer", frame)
                    
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break

            except KeyboardInterrupt:
                logger.info("Отримано сигнал зупинки...")
            finally:
                cap.stop()
                cv2.destroyAllWindows()
                logger.info("Обробку завершено.") # Камеру зупиняти не треба, `with` зробить це сам!

    except ConnectionError as e:
        logger.error(e)

if __name__ == "__main__":
    main()
