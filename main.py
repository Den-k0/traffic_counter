import cv2
import numpy as np
import logging

from config import Config
from utils import ImageUtils
from tracker import CentroidTracker


# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("TrafficCounter")

def main():
    logger.info("Ініціалізація системи...")
    
    # 1. Завантаження моделі
    try:
        net = cv2.dnn.readNetFromCaffe(Config.MODEL_PROTO, Config.MODEL_WEIGHTS)
    except Exception as e:
        logger.error(f"Не вдалося завантажити нейромережу: {e}")
        return

    # 2. Відеопотік
    cap = cv2.VideoCapture(Config.VIDEO_PATH)
    if not cap.isOpened():
        logger.error("Не вдалося відкрити відеофайл або камеру.")
        return

    tracker = CentroidTracker(maxDisappeared=40)
    total_cars = 0
    counted_object_ids = set()

    logger.info("Початок обробки відео...")

    try:
        while True:
            success, frame = cap.read()
            if not success:
                logger.info("Відео завершено. Перезапуск...")
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue

            frame = cv2.resize(frame, (Config.FRAME_WIDTH, Config.FRAME_HEIGHT))
            (h, w) = frame.shape[:2]

            # Покращення контрасту
            if Config.USE_CLAHE:
                frame_input = ImageUtils.apply_clahe(frame)
            else:
                frame_input = frame

            # Детекція
            blob = cv2.dnn.blobFromImage(cv2.resize(frame_input, (300, 300)), 
                                         0.007843, (300, 300), 127.5)
            net.setInput(blob)
            detections = net.forward()

            rects = []
            current_labels = []

            for i in np.arange(0, detections.shape[2]):
                confidence = detections[0, 0, i, 2]
                if confidence > Config.CONFIDENCE_THRESHOLD:
                    idx = int(detections[0, 0, i, 1])
                    label = Config.ALL_CLASSES[idx]

                    if label in Config.VEHICLES:
                        box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                        (startX, startY, endX, endY) = box.astype("int")

                        # Перевірка зони (ROI)
                        centerY = int((startY + endY) / 2.0)
                        if Config.ZONE_TOP < centerY < Config.ZONE_BOTTOM:
                            rects.append(box.astype("int"))
                            current_labels.append(label)

            # Оновлення трекера
            objects, previous_objects, labels, deregistered_ids = tracker.update(rects, current_labels)

            # Очищення пам'яті
            for old_id in deregistered_ids:
                if old_id in counted_object_ids:
                    counted_object_ids.remove(old_id)

            # === ВІЗУАЛІЗАЦІЯ ===
            cv2.line(frame, (Config.LINE_POSITION, Config.ZONE_TOP), 
                     (Config.LINE_POSITION, Config.ZONE_BOTTOM), (0, 255, 255), 2)
            cv2.line(frame, (0, Config.ZONE_TOP), (w, Config.ZONE_TOP), (255, 0, 0), 1)
            cv2.line(frame, (0, Config.ZONE_BOTTOM), (w, Config.ZONE_BOTTOM), (255, 0, 0), 1)

            for (objectID, centroid) in objects.items():
                display_label = labels[objectID].upper()
                
                # Завжди зелений колір
                color = (0, 255, 0)

                cv2.circle(frame, (centroid[0], centroid[1]), 4, color, -1)
                cv2.putText(frame, f"{display_label} {objectID}", 
                           (centroid[0] - 10, centroid[1] - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

                # Логіка підрахунку
                prev_centroid = previous_objects[objectID]
                
                crossed_LR = prev_centroid[0] < Config.LINE_POSITION and centroid[0] >= Config.LINE_POSITION
                crossed_RL = prev_centroid[0] >= Config.LINE_POSITION and centroid[0] < Config.LINE_POSITION

                if crossed_LR or crossed_RL:
                    if objectID not in counted_object_ids:
                        total_cars += 1
                        counted_object_ids.add(objectID)
                        
                        # Візуальний ефект
                        cv2.line(frame, (Config.LINE_POSITION, Config.ZONE_TOP), 
                                 (Config.LINE_POSITION, Config.ZONE_BOTTOM), (0, 0, 255), 4)
                        
                        # Логування події
                        logger.info(f"Зафіксовано: ID {objectID} | Тип: {display_label} | Всього: {total_cars}")

            cv2.putText(frame, f"Count: {total_cars}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)

            cv2.imshow("Traffic Counter", frame)
            cv2.waitKey(1) # Потрібно для оновлення вікна, але без перевірки клавіш

    except KeyboardInterrupt:
        logger.info("Отримано сигнал зупинки. Завершення роботи...")
    finally:
        cap.release()
        cv2.destroyAllWindows()
        logger.info("Програму завершено коректно.")

if __name__ == "__main__":
    main()
