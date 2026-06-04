import time
from collections import deque


class TrafficStateTracker:
    """Відповідає за підрахунок інтенсивності трафіку у ковзному вікні.

    Args:
        free_limit (int): Порог для стану FREE.
        jam_limit (int): Порог для стану JAM/HEAVY.
        window_seconds (int): Розмір вікна у секундах для підрахунку інтенсивності.
    """

    def __init__(self, free_limit=10, jam_limit=25, window_seconds=60):
        # Використовуємо чергу замість списку для швидкого очищення
        self.crossing_timestamps = deque()
        self.free_limit = free_limit
        self.jam_limit = jam_limit
        self.window_seconds = window_seconds

    def register_crossing(self):
        """Додає поточний таймстемп при виявленому перетині лінії."""
        self.crossing_timestamps.append(time.time())

    def get_metrics(self):
        """Повертає (intensity, state, color) для поточної множини таймстемпів.

        Видаляє старіші записи за межами `window_seconds`.
        """
        current_time = time.time()

        # Швидке очищення O(1): видаляємо старі записи зліва (найстаріші)
        while self.crossing_timestamps and current_time - self.crossing_timestamps[0] > self.window_seconds:
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
