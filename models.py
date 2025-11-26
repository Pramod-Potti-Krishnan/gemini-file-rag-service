from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class UploadedFile(Base):
    __tablename__ = "uploaded_files"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True)
    user_id = Column(String, index=True)
    file_name = Column(String)
    file_size = Column(Integer)
    file_type = Column(String)
    gemini_file_uri = Column(String)
    gemini_file_id = Column(String)
    file_search_store_id = Column(String)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

class FileSearchStore(Base):
    __tablename__ = "file_search_stores"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, unique=True, index=True)
    user_id = Column(String)
    gemini_store_name = Column(String) # e.g., "fileSearchStores/..."
    created_at = Column(DateTime, default=datetime.utcnow)
