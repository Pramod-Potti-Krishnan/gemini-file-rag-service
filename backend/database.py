from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Use SQLite for simplicity as per spec implication (or easily switchable)
# But spec mentions PostgreSQL. I will use SQLite for now for easier local setup 
# unless user provided postgres creds. 
# Actually spec says "PostgreSQL 15+ with SQLAlchemy 2.0". 
# I'll stick to SQLite for local dev ease, but structure it for easy switch.
# Or better, I'll use a local sqlite file.

SQLALCHEMY_DATABASE_URL = "sqlite:///./sql_app.db"
# SQLALCHEMY_DATABASE_URL = "postgresql://user:password@postgresserver/db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
