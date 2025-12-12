import cv2


class ImageUtils:
    """Клас для обробки зображень."""

    @staticmethod
    def apply_clahe(image):
        """
        Застосовує адаптивний контраст (CLAHE) для покращення видимості 
        темних об'єктів.
        """
        try:
            lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            cl = clahe.apply(l)
            
            limg = cv2.merge((cl, a, b))
            final = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
            return final
        except Exception as e:
            print(f"Помилка в обробці CLAHE: {e}")
            return image
