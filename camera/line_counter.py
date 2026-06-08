import cv2
import logging
import numpy as np
from collections import OrderedDict
from typing import Any

logger = logging.getLogger("TrafficAnalyzer.Counter")


class LineCounter:
    """Простий лічильник перетинів по лінії.

    Args:
        polygon (np.ndarray): Полігон ROI (numpy array of points).
        line_position (int): X-позиція лінії підрахунку.
        max_cache_size (int): Максимальний розмір кеша зареєстрованих ID.
    """

    def __init__(
        self,
        polygon: np.ndarray,
        line_position: int,
        max_cache_size: int = 1000,
    ) -> None:
        self.polygon: np.ndarray = polygon
        self.line_position: int = line_position

        self.total_objects: int = 0
        self.counted_ids: OrderedDict[int, bool] = (
            OrderedDict()
        )  # черга для безпечного очищення
        self.max_cache_size: int = max_cache_size

        self.previous_centroids: dict[int, tuple[int, int]] = {}
        self.line_color: tuple[int, int, int] = (0, 255, 255)

    def process_tracks(
        self, boxes: Any, class_names: dict[int, str]
    ) -> list[dict[str, Any]]:
        """Обробляє результати трекера та повертає події для рендерингу.

        Args:
            boxes (Any): Об'єкт з `boxes` від Ultralytics track API.
            class_names (dict[int, str]): Словник імен класів моделі.

        Returns:
            list[dict[str, Any]]: Список подій виду {id, label,
                                  bbox, centroid}.
        """
        current_centroids: dict[int, tuple[int, int]] = {}
        self.line_color = (0, 255, 255)
        events: list[dict[str, Any]] = []

        for box in boxes:
            if box.id is None:
                continue

            track_id = int(box.id.item())
            cls_id = int(box.cls[0])
            label = class_names[cls_id].upper()

            x1, y1, x2, y2 = map(int, box.xyxy[0])
            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2

            # Перевірка полігону
            if cv2.pointPolygonTest(self.polygon, (cx, cy), False) >= 0:
                current_centroids[track_id] = (cx, cy)
                events.append(
                    {
                        "id": track_id,
                        "label": label,
                        "bbox": (x1, y1, x2, y2),
                        "centroid": (cx, cy),
                    }
                )

                if track_id in self.previous_centroids:
                    prev_x = self.previous_centroids[track_id][0]

                    crossed_lr = (
                        prev_x < self.line_position
                        and cx >= self.line_position
                    )
                    crossed_rl = (
                        prev_x >= self.line_position
                        and cx < self.line_position
                    )

                    if (
                        crossed_lr or crossed_rl
                    ) and track_id not in self.counted_ids:
                        self.total_objects += 1
                        self.counted_ids[track_id] = True
                        self.line_color = (0, 0, 255)
                        logger.info(
                            f"Зафіксовано: ID {track_id} | Тип: {label} | "
                            f"Всього: {self.total_objects}"
                        )

        self.previous_centroids = current_centroids.copy()

        # БЕЗПЕЧНЕ очищення: видалення тільки найстаріших ID
        while len(self.counted_ids) > self.max_cache_size:
            self.counted_ids.popitem(last=False)

        return events
