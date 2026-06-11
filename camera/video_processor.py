import cv2
import time
import logging

from ultralytics import YOLO
from imutils.video import VideoStream

from config import MLConfig, GeometryConfig, TrafficConfig, SSHConfig
from camera.camera_controller import SSHCameraController
from camera.line_counter import LineCounter
from camera.traffic_state import TrafficStateTracker
from camera.overlay import Visualizer
from camera.state import global_state

logger = logging.getLogger("TrafficAnalyzer.Pipeline")


class VideoPipeline:
    """Ізольований клас для обробки відеопотоку та детекції об'єктів.
    
    Відповідає за ініціалізацію нейромережі, отримання кадрів з камери,
    трекінг об'єктів та генерацію подій перетину контрольної лінії.
    """
    
    def __init__(self, initial_totals: dict, initial_timestamps: list) -> None:
        """Ініціалізує пайплайн та відновлює стан з бази даних.

        Args:
            initial_totals (dict): Словник з початковими лічильниками об'єктів.
            initial_timestamps (list): Список таймстемпів перетинів за останню хвилину.
            
        Raises:
            Exception: Якщо не вдалося завантажити YOLO модель.
        """
        logger.info("Ініціалізація VideoPipeline...")
        try:
            self.model = YOLO(MLConfig.YOLO_MODEL, task="detect")
        except Exception as e:
            logger.error(f"Помилка завантаження моделі: {e}")
            raise e

        self.counter = LineCounter(polygon=GeometryConfig.ROAD_POLYGON, line_position=GeometryConfig.LINE_POSITION)
        self.counter.total_objects = initial_totals.get("total", 0)
        self.total_persons = initial_totals.get("persons", 0)
        self.total_transport = initial_totals.get("transport", 0)

        self.traffic_state = TrafficStateTracker(
            free_limit=TrafficConfig.FREE_FLOW_LIMIT,
            jam_limit=TrafficConfig.JAM_LIMIT,
            window_seconds=TrafficConfig.INTENSITY_WINDOW_SEC
        )
        self.traffic_state.crossing_timestamps.extend(initial_timestamps)

        init_intensity, init_state, _ = self.traffic_state.get_metrics()
        global_state.update_stats(
            self.counter.total_objects, init_intensity, init_state, 
            self.total_persons, self.total_transport
        )

    def run(self) -> None:
        """Головний цикл пайплайну з авто-перепідключенням до камери.
        
        Спрощує підключення по SSH, запускає трансляцію та делегує 
        обробку кадрів внутрішньому методу. Відновлює з'єднання при збоях.
        """
        logger.info("Фоновий потік обробки відео запущено.")
        while global_state.is_running:
            try:
                logger.info("Спроба встановити SSH з'єднання з Raspberry Pi...")
                with SSHCameraController(SSHConfig.RPI_IP, SSHConfig.RPI_USER, SSHConfig.RPI_PASS) as camera:
                    cap = VideoStream(camera.stream_url).start()
                    logger.info("Трансляцію з камери успішно запущено.")
                    self._process_stream(cap)
            except Exception as e:
                logger.error(f"Помилка в циклі обробки відео/SSH-камери: {e}")
                
            if global_state.is_running:
                logger.info("Пауза 5 секунд перед наступною спробою підключення...")
                time.sleep(5)
        
        logger.info("Потік обробки відео зупинено.")

    def _process_stream(self, cap: VideoStream) -> None:
        """Внутрішній цикл покадрової обробки відеопотоку.

        Виконує детекцію через YOLO, рахує перетини, оновлює глобальний стан
        і рендерить UI, якщо на сайті є активні глядачі.

        Args:
            cap (VideoStream): Об'єкт відеопотоку (imutils).
        """
        consecutive_none_frames = 0

        while global_state.is_running:
            frame = cap.read()
            
            if frame is None:
                consecutive_none_frames += 1
                if consecutive_none_frames > 300:
                    logger.warning("⚠️ Втрачено зв'язок із стрімом. Ініціюємо перепідключення...")
                    break
                time.sleep(0.03)
                continue
            
            consecutive_none_frames = 0
            frame = cv2.resize(frame, (GeometryConfig.FRAME_WIDTH, GeometryConfig.FRAME_HEIGHT))
            
            results = self.model.track(
                frame, conf=MLConfig.CONFIDENCE_THRESHOLD, iou=MLConfig.IOU_THRESHOLD,
                persist=True, tracker=MLConfig.TRACKER_CONFIG, classes=MLConfig.TARGET_CLASSES,
                imgsz=MLConfig.INFERENCE_SIZE, verbose=False
            )

            if results and len(results):
                events, new_crossings = self.counter.process_tracks(results[0].boxes, self.model.names)
                if new_crossings:
                    for obj_class in new_crossings:
                        self.traffic_state.register_crossing()
                        if obj_class == "PERSON":
                            self.total_persons += 1
                        else:
                            self.total_transport += 1
                    
                    intensity, state, state_color = self.traffic_state.get_metrics()
                    for obj_class in new_crossings:
                        global_state.log_queue.put((obj_class, state))
                else:
                    intensity, state, state_color = self.traffic_state.get_metrics()
            else:
                events = []
                intensity, state, state_color = self.traffic_state.get_metrics()

            global_state.update_stats(
                self.counter.total_objects, intensity, state, 
                self.total_persons, self.total_transport
            )

            if global_state.has_viewers():
                if not results or not len(results):
                    ret, buffer = cv2.imencode('.jpg', frame)
                else:
                    frame_rendered = Visualizer.render(
                        frame, events, self.counter.total_objects, intensity, state, state_color, self.counter.line_color
                    )
                    ret, buffer = cv2.imencode('.jpg', frame_rendered)
                
                if ret:
                    global_state.update_frame(buffer.tobytes())
            else:
                global_state.clear_frame()

            time.sleep(0.03)

        cap.stop()
