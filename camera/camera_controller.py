import time
import paramiko
import logging
from config import Config

logger = logging.getLogger("TrafficAnalyzer.Camera")

class SSHCameraController:
    """Контролер SSH-стріму для Raspberry Pi.

    Args:
        ip (str): IP адреса Raspberry Pi.
        user (str): SSH користувач.
        password (str): SSH пароль.
        max_retries (int): Кількість спроб підключення.
    """

    def __init__(self, ip, user, password, max_retries=3):
        self.ip = ip
        self.user = user
        self.password = password
        self.max_retries = max_retries
        self.ssh = None
        self.stream_url = f"tcp://{self.ip}:{Config.STREAM_PORT}"

    def __enter__(self):
        """Запускає стрім при вході в контекст. Бере на себе помилки запуску.

        Повертає себе як ресурс для використання в `with`.
        """
        if not self.start_stream():
            raise ConnectionError("Не вдалося запустити трансляцію з Raspberry Pi.")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Гарантовано зупиняє стрім та закриває SSH з'єднання.

        Якщо під час роботи виникла помилка, логуватиме її та не подаватиме
        подаватиме її далі (повертає False).
        """
        self.stop_stream()
        if exc_type:
            logger.error(f"Аварійне завершення роботи камери: {exc_val}")
        return False

    def start_stream(self):
        """Спроба підключитися по SSH і запустити `rpicam-vid` на віддаленому хості.

        Повертає True при успіху або False після max_retries.
        """
        if not all([self.ip, self.user, self.password]):
            logger.error("Відсутні SSH-доступи (IP, USER або PASS) у .env файлі!")
            return False

        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(f"Підключення до {self.ip} (спроба {attempt}/{self.max_retries})...")
                self.ssh.connect(self.ip, username=self.user, password=self.password, timeout=5)
                
                self.ssh.exec_command("pkill rpicam-vid")
                time.sleep(1)

                logger.info("Запуск трансляції...")
                cmd = f"nohup rpicam-vid -t 0 --framerate 20 --saturation 0 --inline --listen -o tcp://0.0.0.0:{Config.STREAM_PORT} >/dev/null 2>&1 &"
                self.ssh.exec_command(cmd)

                logger.info("Очікування підняття порту...")
                wait_cmd = f"timeout {Config.STREAM_TIMEOUT} bash -c 'while ! ss -ltn | grep -q :{Config.STREAM_PORT}; do sleep 0.1; done; echo READY'"
                _, stdout, _ = self.ssh.exec_command(wait_cmd)
                
                if stdout.read().decode().strip() == "READY":
                    logger.info("Порт відкритий. Буферизація H.264...")
                    return True
                else:
                    raise Exception("Таймаут очікування порту")

            except Exception as e:
                logger.error(f"Помилка ініціалізації: {e}")
                if attempt == self.max_retries:
                    logger.critical("Не вдалося запустити камеру після всіх спроб.")
                    return False
                time.sleep(2) # Пауза перед наступною спробою

    def stop_stream(self):
        """Зупиняє процес на віддаленому хості та закриває SSH-з'єднання."""
        if self.ssh:
            logger.info("Вимкнення камери та закриття SSH...")
            try:
                self.ssh.exec_command("pkill rpicam-vid")
                self.ssh.close()
            except Exception as e:
                logger.debug(f"Помилка при закритті SSH: {e}")
