"""Головний вхідний файл застосунку.

Відповідає за конфігурацію логера та запуск ASGI-сервера Uvicorn.
"""
import logging
import logging.config
from dotenv import load_dotenv
import uvicorn

load_dotenv()

from logging_config import LOGGING_CONFIG

if __name__ == "__main__":
    logging.config.dictConfig(LOGGING_CONFIG)
    logger = logging.getLogger("TrafficAnalyzer")
    logger.info("🚀 Запуск сервера Traffic Counter...")
    
    uvicorn.run(
        "web.app:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=False, 
        log_config=None
    )
