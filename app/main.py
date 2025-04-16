from fastapi import FastAPI, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, field_validator
import logging
from datetime import datetime
import os
import re
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from app.routers import api

from app.database.database import get_db, Base, engine
from app.database.models import StationData
from app.crawler.scraper import HSRAnalyzer
from app.logger import setup_logger

# 設置日誌
logger = setup_logger()
logger.info("啟動 FastAPI 服務...")

app = FastAPI(
    title="HSR Crawler API",
    description="用於爬取高鐵網站數據的API服務",
    version="1.0.0"
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class CrawlRequest(BaseModel):
    year_month: str
    save_all: bool = False

    @field_validator('year_month')
    @classmethod
    def validate_year_month(cls, v: str) -> str:
        logger.info(f"正在驗證 year_month: {v}")  # 添加這行
        if not re.match(r'^\d{4}-\d{2}$', v):
            raise ValueError('year_month must be in format YYYY-MM')
        return v

# 定義有效的車站名稱列表
VALID_STATIONS = {
    "南港", "台北", "板橋", "桃園", "新竹", "苗栗", "台中", 
    "彰化", "雲林", "嘉義", "台南", "左營"
}

@app.get("/")
async def root():
    return {"message": "Welcome to HSR Crawler API"}

@app.post("/crawl")
async def crawl_data(request: CrawlRequest, db: Session = Depends(get_db)):
    try:
        logger.info("開始執行爬蟲...")
        analyzer = HSRAnalyzer()
        analyzer.analyze_structure(db)
            
        logger.info("爬蟲執行完成")
        return {"message": "Data crawled and saved successfully"}
    except Exception as e:
        logger.error(f"爬蟲執行時發生錯誤: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/data")
async def get_data(
    request: Request,
    year_month: Optional[str] = Query(None, pattern=r'^\d{4}-\d{2}$', description="格式必須為 YYYY-MM"),
    station: Optional[str] = Query(None, description="車站名稱"),
    visitor_number: Optional[int] = Query(None, ge=0, description="旅客人數必須大於等於 0"),
    entry_exit: Optional[str] = Query(None, pattern=r'^(進站|出站)$', description="必須為 '進站' 或 '出站'"),
    db: Session = Depends(get_db)
):
    """查詢數據"""
    try:
        # 檢查是否有未知的查詢參數
        query_params = request.query_params
        allowed_params = {'year_month', 'station', 'visitor_number', 'entry_exit'}
        unknown_params = set(query_params.keys()) - allowed_params
        if unknown_params:
            raise HTTPException(status_code=422, detail=f"未知的查詢參數: {', '.join(unknown_params)}")

        # 檢查車站名稱是否有效
        if station and station not in VALID_STATIONS:
            raise HTTPException(status_code=422, detail=f"無效的車站名稱: {station}")

        query = db.query(StationData)
        
        if year_month:
            query = query.filter(StationData.year_month == year_month)
        if station:
            query = query.filter(StationData.station == station)
        if visitor_number is not None:
            query = query.filter(StationData.visitor_number == visitor_number)
        if entry_exit:
            query = query.filter(StationData.entry_exit == entry_exit)
            
        results = query.all()
        return results
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查詢數據時發生錯誤: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def main():
    """主程式入口"""
    try:
        analyzer = HSRAnalyzer()
        
        # 創建資料庫會話
        db = next(get_db())
        try:
            analyzer.analyze_structure(db)
            logger.info("高鐵爬蟲程式執行完成")
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"程式執行時發生錯誤: {e}")

if __name__ == "__main__":
    logger.info("啟動 FastAPI 服務...")
    # 從環境變數獲取端口，默認為 8000
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port) 