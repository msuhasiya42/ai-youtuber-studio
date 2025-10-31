import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase


DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@postgres:5432/youtubestudio")


class Base(DeclarativeBase):
    pass


engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


