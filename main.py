import cv2
import numpy as np
import logging
import time
import os
import paramiko
from dotenv import load_dotenv
from ultralytics import YOLO
from imutils.video import VideoStream

from config import Config
from utils import ImageUtils

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("TrafficAnalyzer")

def main():
    logger.info("Ініціалізація системи...")
    
    # --- БЛОК SSH ТА ОРКЕСТРАЦІЇ ---
    load_dotenv()
    RPI_IP = os.getenv("RPI_IP")
    RPI_USER = os.getenv("RPI_USER")
    RPI_PASS = os.getenv("RPI_PASS")
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(RPI_IP, username=RPI_USER, password=RPI_PASS)
        ssh.exec_command("pkill rpicam-vid")
        time.sleep(1)

        logger.info("Запуск трансляції на Raspberry Pi...")
        stream_cmd = "nohup rpicam-vid -t 0 --framerate 20 --saturation 0 --inline --listen -o tcp://0.0.0.0:8888 >/dev/null 2>&1 &"
        ssh.exec_command(stream_cmd)

        logger.info("Синхронізація: очікування підняття порту на рівні ОС...")
        # Виконуємо bash-скрипт прямо на малині, який чекає появи порту без TCP-підключення
        wait_cmd = "timeout 15 bash -c 'while ! ss -ltn | grep -q :8888; do sleep 0.1; done; echo READY'"
        stdin, stdout, stderr = ssh.exec_command(wait_cmd)
        
        # Скрипт блокується тут і чекає, поки малина не відповість "READY"
        status = stdout.read().decode().strip()

        if status != "READY":
            logger.error("Помилка: rpicam-vid не зміг відкрити порт за 15 секунд.")
            ssh.close()
            exit(1)
            
        logger.info("Порт 8888 перейшов у стан LISTEN. Миттєве підключення OpenCV...")
    except Exception as e:
        logger.error(f"Помилка SSH: {e}")
        return
    # -------------------------------
    
    try:
        model = YOLO(Config.YOLO_MODEL, task="detect")
        logger.info(f"Модель {Config.YOLO_MODEL} успішно завантажена.")
    except Exception as e:
        logger.error(f"Помилка завантаження моделі: {e}")
        return
    
    # Використовуємо IP з .env для стріму
    cap = VideoStream(f"tcp://{RPI_IP}:8888").start()
    time.sleep(2.0)

    total_objects = 0
    counted_object_ids = set()
    crossing_timestamps = []
    previous_centroids = {}

    logger.info("Початок обробки відео...")

    try:
        while True:
            frame = cap.read()
            
            if frame is None:
                continue # Кадр ще летить по мережі, пропускаємо ітерацію

            frame = cv2.resize(frame, (Config.FRAME_WIDTH, Config.FRAME_HEIGHT))
            (h, w) = frame.shape[:2]

            if Config.USE_CLAHE:
                frame_input = ImageUtils.apply_clahe(frame)
            else:
                frame_input = frame

            # Трекінг 
            results = model.track(
                frame_input, 
                conf=Config.CONFIDENCE_THRESHOLD,
                iou=0.4,
                persist=True, 
                tracker="custom_tracker.yaml",
                classes=Config.TARGET_CLASSES,
                imgsz=640,
                verbose=False
            )

            current_centroids = {}

            # Візуалізація робочої зони (Полігону) та лінії підрахунку
            cv2.polylines(frame, [Config.ROAD_POLYGON], isClosed=True, color=(255, 0, 0), thickness=2)
            cv2.line(frame, (Config.LINE_POSITION, 0), (Config.LINE_POSITION, h), (0, 255, 255), 2)

            line_color = (0, 255, 255) 

            for r in results:
                boxes = r.boxes
                for box in boxes:
                    if box.id is None:
                        continue
                        
                    track_id = int(box.id.item())
                    cls_id = int(box.cls[0])
                    label = model.names[cls_id].upper()

                    x1, y1, x2, y2 = box.xyxy[0]
                    startX, startY, endX, endY = int(x1), int(y1), int(x2), int(y2)
                    
                    centerY = int((startY + endY) / 2.0)
                    centerX = int((startX + endX) / 2.0)

                    # Перевірка чи знаходиться центр об'єкта всередині полігону
                    # Значення >= 0 означає, що точка всередині або на межі
                    is_inside_polygon = cv2.pointPolygonTest(Config.ROAD_POLYGON, (centerX, centerY), False) >= 0

                    if is_inside_polygon:
                        current_centroids[track_id] = (centerX, centerY)

                        cv2.circle(frame, (centerX, centerY), 4, (0, 255, 0), -1)
                        cv2.putText(frame, f"{label} {track_id}", 
                                   (startX, startY - 10),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                        cv2.rectangle(frame, (startX, startY), (endX, endY), (0, 255, 0), 1)

                        if track_id in previous_centroids:
                            prev_x = previous_centroids[track_id][0]
                            curr_x = centerX

                            crossed_LR = prev_x < Config.LINE_POSITION and curr_x >= Config.LINE_POSITION
                            crossed_RL = prev_x >= Config.LINE_POSITION and curr_x < Config.LINE_POSITION

                            if crossed_LR or crossed_RL:
                                if track_id not in counted_object_ids:
                                    total_objects += 1
                                    counted_object_ids.add(track_id)
                                    crossing_timestamps.append(time.time())
                                    line_color = (0, 0, 255)
                                    logger.info(f"Зафіксовано: ID {track_id} | Тип: {label} | Всього: {total_objects}")

            previous_centroids = current_centroids.copy()

            cv2.line(frame, (Config.LINE_POSITION, 0), (Config.LINE_POSITION, h), line_color, 3 if line_color == (0,0,255) else 2)

            current_time = time.time()
            crossing_timestamps = [t for t in crossing_timestamps if current_time - t <= 60]
            objects_per_minute = len(crossing_timestamps)

            if objects_per_minute <= Config.FREE_FLOW_LIMIT:
                status_text = "Traffic: FREE"
                status_color = (0, 255, 0)
            elif objects_per_minute <= Config.JAM_LIMIT:
                status_text = "Traffic: NORMAL"
                status_color = (0, 255, 255)
            else:
                status_text = "Traffic: HEAVY"
                status_color = (0, 0, 255)
            
            cv2.putText(frame, status_text, (20, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, status_color, 3)
            cv2.putText(frame, f"Intensity: {objects_per_minute}/min", (20, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(frame, f"Total objects: {total_objects}", (20, 90),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

            cv2.imshow("Traffic Analyzer", frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    except KeyboardInterrupt:
        logger.info("Завершення роботи...")
    finally:
        cap.stop()
        cv2.destroyAllWindows()
        # --- ЗУПИНКА КАМЕРИ ПРИ ВИХОДІ ---
        try:
            ssh.exec_command("pkill rpicam-vid")
            ssh.close()
        except:
            pass

if __name__ == "__main__":
    main()
