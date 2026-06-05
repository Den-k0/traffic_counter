import cv2
import logging
import numpy as np

logger = logging.getLogger("TrafficAnalyzer.Utils")


class ImageUtils:
    """Утилітний клас для операцій над зображенням."""

    @staticmethod
    def apply_clahe(image: np.ndarray) -> np.ndarray:
        """Застосовує CLAHE до L-каналу LAB-простору для покращення контрасту.

        Повертає оброблене зображення або оригінал у випадку помилки.
        """
        try:
            lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)

            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            cl = clahe.apply(l)

            limg = cv2.merge((cl, a, b))
            final = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
            return final
        except Exception:
            logger.exception("Помилка в обробці CLAHE")
            return image
