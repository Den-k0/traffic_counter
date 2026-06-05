import cv2
import numpy as np
from typing import Any
from config import Config


class Visualizer:
    """Допоміжні методи рендерингу для UI/HUD."""

    @staticmethod
    def draw_text_with_outline(
        img: np.ndarray, 
        text: str, 
        pos: tuple[int, int], 
        font_scale: float, 
        text_color: tuple[int, int, int], 
        thickness: int = 2
    ) -> None:
        """Малює текст з чорним контуром для кращої читабельності."""
        cv2.putText(img, text, pos, cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 0, 0), thickness + 3)
        cv2.putText(img, text, pos, cv2.FONT_HERSHEY_SIMPLEX, font_scale, text_color, thickness)

    @staticmethod
    def render(
        frame: np.ndarray, 
        events: list[dict[str, Any]], 
        total_objects: int, 
        intensity: int, 
        state: str, 
        state_color: tuple[int, int, int], 
        line_color: tuple[int, int, int]
    ) -> np.ndarray:
        """Накладає ROI, лінію підрахунку, bounding box'и та HUD на кадр.

        Args:
            frame (np.ndarray): OpenCV image.
            events (list[dict[str, Any]]): список подій трекінгу ({id,label,bbox,centroid}).
            total_objects (int): загальна кількість за сесію.
            intensity (int): інтенсивність (об'єктів за хвилину).
            state (str): поточний стан трафіку.
            state_color (tuple[int, int, int]): колір тексту стану.
            line_color (tuple[int, int, int]): колір лінії (змінюється при перетині).
        Returns:
            np.ndarray: frame з накладеним UI.
        """
        h, _ = frame.shape[:2]

        # Статичні зони
        cv2.polylines(frame, [Config.ROAD_POLYGON], isClosed=True, color=(255, 0, 0), thickness=2)
        cv2.line(frame, (Config.LINE_POSITION, 0), (Config.LINE_POSITION, h), line_color, 3 if line_color == (0, 0, 255) else 2)

        # Динамічні об'єкти (з tracking events)
        for ev in events:
            x1, y1, x2, y2 = ev["bbox"]
            cx, cy = ev["centroid"]
            label = f"{ev['label']} {ev['id']}"

            cv2.circle(frame, (cx, cy), 4, (0, 255, 0), -1)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 1)
            Visualizer.draw_text_with_outline(frame, label, (x1, y1 - 10), 0.5, (0, 255, 0), 1)

        # UI Статистика
        Visualizer.draw_text_with_outline(frame, f"Traffic State: {state}", (20, 30), 0.9, state_color)
        Visualizer.draw_text_with_outline(frame, f"Intensity: {intensity}/min", (20, 60), 0.7, (255, 255, 255))
        Visualizer.draw_text_with_outline(frame, f"Total objects: {total_objects}", (20, 90), 0.7, (255, 255, 255))

        return frame
