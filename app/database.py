from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import os
from dotenv import load_dotenv
from typing import Generator
from contextlib import contextmanager

# Load environment variables
load_dotenv()

# PostgreSQL Configuration - Added type hints and validation
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD") or "postgres"  # Explicit fallback
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "ussd_db")

# Construct connection URL with validation
if not all([POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_HOST, POSTGRES_DB]):
    raise ValueError("Missing required PostgreSQL configuration")

SQLALCHEMY_DATABASE_URL = (
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)

# Engine configuration with additional production-ready settings
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,          # Checks connections before use
    pool_size=10,               # Maintain 10 connections
    max_overflow=20,            # Allow up to 20 temporary connections
    pool_recycle=3600,          # Recycle connections after 1 hour
    pool_timeout=30,            # Wait 30 seconds for a connection
    echo=False                  # Set to True for debugging SQL queries
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False  # Added for better session control
)

Base = declarative_base()

# Improved get_db with context manager and type hints
@contextmanager
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()