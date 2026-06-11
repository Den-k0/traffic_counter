"""Модуль налаштування підключення до бази даних (SQLAlchemy).

Створює підключення до SQLite та визначає
базовий декларативний клас для моделей.
"""
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

# База даних знаходиться у корені проєкту
PROJECT_DIR = Path(__file__).parent.parent
DB_PATH = PROJECT_DIR / "traffic.db"
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Session:
    """Генератор сесій бази даних.

    Автоматично закриває з'єднання після завершення обробки HTTP-запиту.

    Yields:
        Session: Активна сесія SQLAlchemy.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
