import threading
import queue
import logging

logger = logging.getLogger("TrafficAnalyzer.State")


class VideoStreamState:
    """Клас для потокобезпечного керування глобальним станом застосунку.
    
    Відповідає за зберігання останнього кадру, бізнес-метрик трафіку 
    та керування чергою логів для запису в БД.
    """
    def __init__(self) -> None:
        """Ініціалізує початковий стан та примітиви синхронізації."""
        self._latest_frame: bytes = b""
        self._total_objects: int = 0
        self._intensity: int = 0
        self._traffic_state: str = "FREE"
        self._total_persons: int = 0      
        self._total_transport: int = 0    
        self._active_viewers: int = 0     
        
        self.is_running: bool = False
        
        self._lock = threading.Lock()
        self.log_queue: queue.Queue = queue.Queue()

    def update_frame(self, frame_bytes: bytes) -> None:
        """Потокобезпечно оновлює останній згенерований кадр.

        Args:
            frame_bytes (bytes): Закодоване зображення у форматі JPEG.
        """
        with self._lock:
            self._latest_frame = frame_bytes

    def get_frame(self) -> bytes:
        """Потокобезпечно повертає останній кадр.

        Returns:
            bytes: Закодоване зображення.
        """
        with self._lock:
            return self._latest_frame

    def clear_frame(self) -> None:
        """Очищає буфер кадру для економії пам'яті, коли глядачів немає."""
        with self._lock:
            self._latest_frame = b""

    def increment_viewers(self) -> None:
        """Реєструє нового глядача відеопотоку."""
        with self._lock:
            self._active_viewers += 1
            logger.info(f"👥 Нове підключення до відеопотоку. Активних глядачів: {self._active_viewers}")

    def decrement_viewers(self) -> None:
        """Відміняє реєстрацію глядача відеопотоку."""
        with self._lock:
            if self._active_viewers > 0:
                self._active_viewers -= 1
            logger.info(f"👥 Відключення від відеопотоку. Активних глядачів: {self._active_viewers}")

    def has_viewers(self) -> bool:
        """Перевіряє, чи є активні глядачі.

        Returns:
            bool: True, якщо відеопотік переглядають, інакше False.
        """
        with self._lock:
            return self._active_viewers > 0

    def update_stats(self, total: int, intensity: int, state: str, total_persons: int, total_transport: int) -> None:
        """Потокобезпечно оновлює метрики трафіку.

        Args:
            total (int): Загальна кількість зафіксованих об'єктів.
            intensity (int): Кількість об'єктів за останнє часове вікно.
            state (str): Поточний стан трафіку (FREE, NORMAL, HEAVY).
            total_persons (int): Загальна кількість людей.
            total_transport (int): Загальна кількість транспорту.
        """
        with self._lock:
            self._total_objects = total
            self._intensity = intensity
            self._traffic_state = state
            self._total_persons = total_persons
            self._total_transport = total_transport

    def get_stats(self) -> dict:
        """Потокобезпечно повертає поточну статистику.

        Returns:
            dict: Словник з ключами total_objects, intensity, traffic_state, total_persons, total_transport.
        """
        with self._lock:
            return {
                "total_objects": self._total_objects,
                "intensity": self._intensity,
                "traffic_state": self._traffic_state,
                "total_persons": self._total_persons,
                "total_transport": self._total_transport
            }

global_state = VideoStreamState()
