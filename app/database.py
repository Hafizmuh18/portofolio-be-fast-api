# app/database.py
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

if not SQLALCHEMY_DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set. Please check your .env file.")

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_recycle=3600
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- TAMBAHKAN FUNGSI INI DI SINI ---
def create_db_and_tables():
    # Import models here to ensure they are registered with Base.metadata
    # Contoh: Jika models.py Anda mendefinisikan tabel seperti Room dan Message
    # Anda perlu memastikan models.py diimpor *sebelum* create_all dipanggil.
    # Biasanya, Anda akan mengimpor `models` di main.py, dan itu cukup.
    # Tapi untuk memastikan, kita bisa impor di sini juga jika diperlukan.

    # Contoh import jika models.py ada di folder app
    from . import models 

    Base.metadata.create_all(bind=engine)
# --- AKHIR PENAMBAHAN ---