import time
import paramiko
import logging
from typing import Optional, Type, Any
from config import StreamConfig

logger = logging.getLogger("TrafficAnalyzer.Camera")


class SSHCameraController:
    """Контролер SSH-з'єднання для віддаленого запуску камери на Raspberry Pi.

    Керує життєвим циклом стріму (rpicam-vid), використовуючи протокол TCP.
    Реалізує інтерфейс Context Manager для безпечного закриття.

    Args:
        ip (str): IP адреса Raspberry Pi у локальній мережі.
        user (str): SSH користувач.
        password (str): SSH пароль.
        max_retries (int, optional): Кількість спроб підключення. За замовчуванням 3.
    """

    def __init__(
        self, ip: str, user: str, password: str, max_retries: int = 3
    ) -> None:
        self.ip: str = ip
        self.user: str = user
        self.password: str = password
        self.max_retries: int = max_retries
        self.ssh: Optional[paramiko.SSHClient] = None
        self.stream_url: str = f"tcp://{self.ip}:{StreamConfig.STREAM_PORT}"

    def __enter__(self) -> "SSHCameraController":
        """Встановлює з'єднання при вході в контекст.

        Returns:
            SSHCameraController: Екземпляр контролера.

        Raises:
            ConnectionError: Якщо підключитися не вдалося після всіх спроб.
        """
        if not self.start_stream():
            raise ConnectionError(
                "Не вдалося запустити трансляцію з Raspberry Pi."
            )
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[Any],
    ) -> bool:
        """Гарантовано вимикає камеру та
        закриває сесію при виході з контексту.
        """
        self.stop_stream()
        if exc_type:
            logger.error(f"Аварійне завершення роботи камери: {exc_val}")
        return False

    def start_stream(self) -> bool:
        """Спроба підключитися по SSH і запустити трансляцію `rpicam-vid`.

        Вбиває старі завислі процеси, запускає новий та чекає відкриття порту.

        Returns:
            bool: True при успішному запуску, False при невдачі.
        """
        if not all([self.ip, self.user, self.password]):
            logger.error(
                "Відсутні SSH-доступи (IP, USER або PASS) у .env файлі!"
            )
            return False

        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(
                    f"Підключення до {self.ip} "
                    f"(спроба {attempt}/{self.max_retries})..."
                )
                self.ssh.connect(
                    self.ip,
                    username=self.user,
                    password=self.password,
                    timeout=5,
                    look_for_keys=False,
                    allow_agent=False
                )

                self.ssh.exec_command("pkill rpicam-vid")
                time.sleep(1)

                logger.info("Запуск трансляції...")
                cmd = (
                    f"nohup rpicam-vid -t 0 --framerate 20 "
                    f"--saturation 0 --inline --listen -o "
                    f"tcp://0.0.0.0:{StreamConfig.STREAM_PORT} >/dev/null 2>&1 &"
                )
                self.ssh.exec_command(cmd)

                logger.info("Очікування підняття порту...")
                wait_cmd = (
                    f"timeout {StreamConfig.STREAM_TIMEOUT} bash -c "
                    f"'while ! ss -ltn | grep -q :{StreamConfig.STREAM_PORT}; "
                    "do sleep 0.1; done; echo READY'"
                )
                _, stdout, _ = self.ssh.exec_command(wait_cmd)

                if stdout.read().decode().strip() == "READY":
                    logger.info("Порт відкритий. Буферизація H.264...")
                    return True
                else:
                    raise Exception("Таймаут очікування порту")

            except Exception as e:
                logger.error(f"Помилка ініціалізації: {e}")
                if attempt == self.max_retries:
                    logger.critical(
                        "Не вдалося запустити камеру після всіх спроб."
                    )
                    return False
                time.sleep(2)

        return False

    def stop_stream(self) -> None:
        """Зупиняє процес трансляції на
        віддаленому хості та закриває SSH-сесію.
        """
        if self.ssh:
            logger.info("Вимкнення камери та закриття SSH...")
            try:
                self.ssh.exec_command("pkill rpicam-vid")
                self.ssh.close()
            except Exception as e:
                logger.debug(f"Помилка при закритті SSH: {e}")
