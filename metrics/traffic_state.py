import time
from collections import deque


class TrafficStateTracker:
    """Відповідає за підрахунок інтенсивності трафіку у ковзному вікні.

    Args:
        free_limit (int): Поріг для стану FREE.
        jam_limit (int): Поріг для стану JAM/HEAVY.
        window_seconds (int): Вікно для підрахунку інтенсивності.
    """

    def __init__(
        self,
        free_limit: int = 10,
        jam_limit: int = 25,
        window_seconds: int = 60,
    ) -> None:
        self.crossing_timestamps: deque[float] = deque()
        self.free_limit: int = free_limit
        self.jam_limit: int = jam_limit
        self.window_seconds: int = window_seconds

    def register_crossing(self) -> None:
        """Додає поточний таймстемп при виявленому перетині лінії."""
        self.crossing_timestamps.append(time.time())

    def get_metrics(self) -> tuple[int, str, tuple[int, int, int]]:
        """Повертає (intensity, state, color) для поточної множини таймстемпів.

        Видаляє старіші записи за межами `window_seconds`.
        """
        current_time = time.time()

        # Швидке очищення O(1): видаляємо старі записи зліва (найстаріші)
        while (
            self.crossing_timestamps
            and current_time - self.crossing_timestamps[0]
            > self.window_seconds
        ):
            self.crossing_timestamps.popleft()

        intensity = len(self.crossing_timestamps)

        if intensity <= self.free_limit:
            state = "FREE"
            color = (0, 255, 0)
        elif intensity <= self.jam_limit:
            state = "NORMAL"
            color = (0, 255, 255)
        else:
            state = "HEAVY"
            color = (0, 0, 255)

        return intensity, state, color
