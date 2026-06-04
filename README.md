# Traffic Counter

### 🧠 Model Setup (Apple Silicon)

Before running the application, you need to download the YOLOv8 Large weights and export them to the CoreML format (optimized for Mac).

Run the following command in your terminal:

```bash
yolo export model=yolov8l.pt format=coreml
