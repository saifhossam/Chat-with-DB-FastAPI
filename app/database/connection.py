from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.database.models import Base


database_url = settings.database_url

if database_url.startswith("postgresql://"):
    database_url = database_url.replace(
        "postgresql://",
        "postgresql+psycopg://",
        1
    )


engine = create_engine(
    database_url,

    # SQLite محتاج check_same_thread=False
    connect_args={
        "check_same_thread": False
    } if database_url.startswith("sqlite") else {},

    # يتأكد إن الـ connection لسه شغال قبل استخدامه
    pool_pre_ping=True,

    # يجدد الـ connections القديمة بعد 30 دقيقة
    pool_recycle=1800,
)


SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False
)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()