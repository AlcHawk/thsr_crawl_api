from sqlalchemy import Column, Integer, String, DateTime, Float
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()

class StationData(Base):
    """車站數據模型"""
    __tablename__ = "hsr_vis_data"

    id = Column(Integer, primary_key=True, index=True)
    year_month = Column(String, index=True)  # 年度/月份
    station_sequence = Column(Integer)  # 車站序號
    station = Column(String)  # 車站名稱
    visitor_number = Column(Integer)  # 旅客人數
    entry_exit = Column(String)  # 進出站類型
    created_at = Column(DateTime, default=datetime.now)  # 創建時間

    def __repr__(self):
        return f"<StationData(year_month='{self.year_month}', station='{self.station}', visitor_number={self.visitor_number}, entry_exit='{self.entry_exit}')>" 