"""Database configuration and session management"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./casino_bonuses.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dependency for FastAPI to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)
    
    # Simple migration for SQLite to add new columns if they don't exist
    if "sqlite" in DATABASE_URL:
        with engine.connect() as conn:
            try:
                conn.execute("ALTER TABLE bonuses ADD COLUMN is_claimed BOOLEAN DEFAULT 0")
            except Exception:
                pass # Column likely exists
            
            try:
                conn.execute("ALTER TABLE bonuses ADD COLUMN claimed_at DATETIME")
            except Exception:
                pass # Column likely exists
