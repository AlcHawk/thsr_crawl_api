from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.ext.declarative import declarative_base as old_declarative_base
import os
from dotenv import load_dotenv
from app.logger import setup_logger

# 設置日誌
logger = setup_logger()

# 加載環境變數
load_dotenv()

# 檢查是否在 Render 環境
if "RENDER" in os.environ:
    SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")
    if not SQLALCHEMY_DATABASE_URL:
        raise ValueError("在 Render 環境中必須設置 DATABASE_URL 環境變數")
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)
    logger.info(f"使用 Render 資料庫 URL: {SQLALCHEMY_DATABASE_URL}")
else:
    # 本地開發環境
    DB_USER = os.getenv("DB_USER", "hsr_user")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "33taoTHSR")
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "hsr_data")
    
    SQLALCHEMY_DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    logger.info(f"使用本地資料庫 URL: {SQLALCHEMY_DATABASE_URL}")

# 創建數據庫引擎
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# 創建會話工廠
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 創建基類
Base = declarative_base()

def get_db():
    """獲取數據庫會話"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 