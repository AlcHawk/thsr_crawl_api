import sys
import os
from pathlib import Path

# 添加專案根目錄到 Python 路徑
project_root = str(Path(__file__).parent.parent)
sys.path.insert(0, project_root)

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import pytest
from datetime import datetime
import pandas as pd
import time

from app.main import app
from app.database.database import get_db
from app.database.models import Base, StationData
from app.crawler.scraper import HSRAnalyzer

# 測試數據庫配置
SQLALCHEMY_DATABASE_URL = "postgresql://hsr_user:33taoTHSR@localhost:5432/hsr_data"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session():
    """創建測試數據庫會話"""
    # 創建所有表
    Base.metadata.create_all(bind=engine)
    
    # 創建會話
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        # 清空表而不是刪除表
        for table in reversed(Base.metadata.sorted_tables):
            db.execute(table.delete())
        db.commit()
        db.close()

@pytest.fixture(scope="function")
def client(db_session):
    """創建測試客戶端"""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)

def test_root(client):
    """測試根路徑"""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to HSR Crawler API"}

def test_crawl_data(client, db_session):
    """測試爬蟲觸發"""
    # 添加正確的請求體
    response = client.post("/crawl", json={"year_month": "2024-01", "save_all": False})
    assert response.status_code == 200
    assert response.json()["message"] == "Data crawled and saved successfully"
    
    # 驗證數據是否已保存到數據庫
    result = db_session.query(StationData).first()
    assert result is not None
    
    # 驗證數據的完整性
    all_data = db_session.query(StationData).all()
    assert len(all_data) > 0  # 確保有數據
    
    # 驗證數據格式
    for data in all_data:
        assert data.year_month is not None
        assert data.station is not None
        assert data.visitor_number is not None
        assert data.entry_exit in ["進站", "出站"]
        
    # 驗證數據的合理性
    stations = set(data.station for data in all_data)
    expected_stations = {"南港", "台北", "板橋", "桃園", "新竹", "苗栗", 
                        "台中", "彰化", "雲林", "嘉義", "台南", "左營"}
    assert expected_stations.issubset(stations)  # 確保所有預期車站都存在
    
    # 驗證旅客人數的合理性
    for data in all_data:
        assert data.visitor_number >= 0  # 旅客人數不應為負
        assert isinstance(data.visitor_number, int)  # 旅客人數應為整數

def test_get_data(client, db_session):
    """測試資料查詢"""
    # 先執行爬蟲獲取數據
    response = client.post("/crawl", json={"year_month": "2024-01", "save_all": False})
    assert response.status_code == 200
    assert response.json()["message"] == "Data crawled and saved successfully"
    
    # 等待爬蟲完成
    time.sleep(2)  # 給爬蟲一些時間完成
    
    # 測試不帶參數的查詢
    response = client.get("/data")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert data[0]["station"] == "南港"
    assert data[0]["visitor_number"] >= 0
    assert data[0]["entry_exit"] in ["進站", "出站"]
    
    # 測試按年月查詢
    response = client.get("/data?year_month=2024-01")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert data[0]["year_month"] == "2024-01"
    
    # 測試按車站查詢
    response = client.get("/data?station=台北")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert data[0]["station"] == "台北"
    assert data[0]["visitor_number"] >= 0
    
    # 測試按進出站類型查詢
    response = client.get("/data?entry_exit=進站")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert all(item["entry_exit"] == "進站" for item in data)
    
    # 測試組合查詢
    response = client.get("/data?year_month=2024-01&station=台北&entry_exit=進站")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert data[0]["year_month"] == "2024-01"
    assert data[0]["station"] == "台北"
    assert data[0]["entry_exit"] == "進站"

def test_error_handling(client):
    """測試錯誤處理"""
    # 測試無效的爬蟲請求
    # 1. 缺少必要參數
    response = client.post("/crawl", json={})
    assert response.status_code == 422
    
    # 2. 無效的參數類型
    response = client.post("/crawl", json={"year_month": 2024, "save_all": "false"})
    assert response.status_code == 422
    
    # 3. 無效的日期格式
    response = client.post("/crawl", json={"year_month": "2024/01", "save_all": False})
    assert response.status_code == 422
    
    # 測試無效的數據查詢
    # 1. 無效的參數名稱
    response = client.get("/data?invalid_param=value")
    assert response.status_code == 422
    
    # 2. 無效的日期格式
    response = client.get("/data?year_month=2024/01")
    assert response.status_code == 422
    
    # 3. 無效的車站名稱
    response = client.get("/data?station=不存在")
    assert response.status_code == 422
    
    # 4. 無效的進出站類型
    response = client.get("/data?entry_exit=無效類型")
    assert response.status_code == 422 