from typing import List, Dict, Optional
import requests
from pyquery import PyQuery as pq
import pandas as pd
from datetime import datetime, timedelta
import logging
import os
import io
import psycopg2
from psycopg2.extras import execute_values
from sqlalchemy.orm import Session

from app.database.models import StationData
from app.logger import setup_logger

# 設置全局 logger
logger = setup_logger()

class HSRAnalyzer:
    """高鐵網站分析器"""
    
    def __init__(self):
        """初始化分析器"""
        self.logger = logger
        self.url = "https://www.thsrc.com.tw/ArticleContent/a3b630bb-1066-4352-a1ef-58c7b4e8ef7c"
        self.session = requests.Session()
        self.base_url = "https://www.thsrc.com.tw/corp/9571df11-8524-4935-8a46-0d5a72e6bc7c"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        # 從環境變數獲取資料庫連接資訊
        self.db_params = {
            'dbname': os.getenv('DB_NAME', 'hsr_data'),
            'user': os.getenv('DB_USER', 'hsr_user'),
            'password': os.getenv('DB_PASSWORD', '33taoTHSR'),
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': os.getenv('DB_PORT', '5432')
        }
        self.logger.info(f"初始化爬蟲，目標網址: {self.base_url}")
        
    def get_db_connection(self):
        """建立資料庫連接"""
        try:
            return psycopg2.connect(**self.db_params)
        except Exception as e:
            self.logger.error(f"資料庫連接失敗: {e}")
            return None
            
    def get_page_content(self, params: Optional[Dict] = None) -> Optional[str]:
        """獲取網頁內容"""
        try:
            self.logger.info("開始獲取網頁內容...")
            response = requests.get(self.base_url, headers=self.headers, params=params)
            response.raise_for_status()
            self.logger.info("網頁內容獲取成功")
            return response.text
        except requests.RequestException as e:
            self.logger.error(f"獲取網頁內容時發生錯誤: {e}")
            return None
            
    def find_tab_buttons(self, content: str) -> Dict[str, Dict[str, str]]:
        """尋找進站和出站的切換按鈕"""
        doc = pq(content)
        buttons = {}
        
        # 尋找所有可能的切換按鈕
        tab_elements = doc("a, button, input[type='button'], input[type='submit']")
        
        for element in tab_elements.items():
            text = element.text().strip()
            if "進站" in text:
                buttons["entry"] = {
                    "href": element.attr("href") or "",
                    "onclick": element.attr("onclick") or "",
                    "class": element.attr("class") or "",
                    "id": element.attr("id") or "",
                    "data-target": element.attr("data-target") or ""
                }
            elif "出站" in text:
                buttons["exit"] = {
                    "href": element.attr("href") or "",
                    "onclick": element.attr("onclick") or "",
                    "class": element.attr("class") or "",
                    "id": element.attr("id") or "",
                    "data-target": element.attr("data-target") or ""
                }
                
        self.logger.info(f"找到的切換按鈕: {buttons}")
        return buttons

    def analyze_page_structure(self, content: str):
        """詳細分析網頁結構"""
        doc = pq(content)
        
        # 1. 分析所有表格
        tables = doc("table")
        self.logger.info(f"\n找到 {len(tables)} 個表格")
        
        for i, table in enumerate(tables.items()):
            self.logger.info(f"\n表格 {i+1} 分析:")
            # 獲取表格的 class 和 id
            table_class = table.attr("class")
            table_id = table.attr("id")
            self.logger.info(f"表格 class: {table_class}")
            self.logger.info(f"表格 id: {table_id}")
            
            # 獲取表格的父元素
            parent = table.parent()
            parent_class = parent.attr("class")
            parent_id = parent.attr("id")
            self.logger.info(f"父元素 class: {parent_class}")
            self.logger.info(f"父元素 id: {parent_id}")
            
            # 獲取表格標題
            caption = table("caption")
            if caption:
                self.logger.info(f"表格標題: {caption.text()}")
                
            # 獲取表格前後的文字
            prev_text = table.prev().text()
            next_text = table.next().text()
            self.logger.info(f"表格前文字: {prev_text[:100]}...")
            self.logger.info(f"表格後文字: {next_text[:100]}...")
            
            # 獲取表格內容示例
            first_row = table("tr").eq(0)
            self.logger.info(f"第一行內容: {first_row.text()}")
            
    def find_passenger_table(self, content: str, tabtag: str) -> Optional[pq]:
        """尋找各站進出旅客人數表格"""
        doc = pq(content)
        
        # 方法1：通過表格標籤尋找
        tables = doc(f"div{tabtag}")
        if len(tables) == 1:
            self.logger.info(f"通過標籤找到目標表格: {tabtag}")
            return tables
        else:
            self.logger.warning(f"找到多個表格: {len(tables)}")
            return None

        self.logger.warning("未找到各站進出旅客人數表格")
        return None
        
    def transform_data(self, df: pd.DataFrame, table_type: str) -> pd.DataFrame:
        """轉換資料結構"""
        try:
            # 輸出原始表格內容以便分析
            self.logger.info("原始表格內容:")
            self.logger.info(f"欄位名稱: {df.columns.tolist()}")
            self.logger.info(f"表格形狀: {df.shape}")
            self.logger.info("完整表格內容:")
            self.logger.info(df)
            
            # 移除空行
            df = df.dropna(how='all')
            
            # 重置索引
            df = df.reset_index(drop=True)
            
            df_transformed = df.melt(id_vars = ["年度 / 月份"], var_name = "車站", value_vars = ["南港", "台北", "板橋", "桃園", "新竹", "苗栗", "台中", "彰化", "雲林", "嘉義", "台南", "左營", "總計"], value_name = "旅客人數")

            df_transformed["車站序"] = 0
            df_transformed.loc[df_transformed["車站"] == "南港", "車站序"] = 1
            df_transformed.loc[df_transformed["車站"] == "台北", "車站序"] = 2
            df_transformed.loc[df_transformed["車站"] == "板橋", "車站序"] = 3
            df_transformed.loc[df_transformed["車站"] == "桃園", "車站序"] = 4
            df_transformed.loc[df_transformed["車站"] == "新竹", "車站序"] = 5
            df_transformed.loc[df_transformed["車站"] == "苗栗", "車站序"] = 6
            df_transformed.loc[df_transformed["車站"] == "台中", "車站序"] = 7
            df_transformed.loc[df_transformed["車站"] == "彰化", "車站序"] = 8
            df_transformed.loc[df_transformed["車站"] == "雲林", "車站序"] = 9
            df_transformed.loc[df_transformed["車站"] == "嘉義", "車站序"] = 10
            df_transformed.loc[df_transformed["車站"] == "台南", "車站序"] = 11
            df_transformed.loc[df_transformed["車站"] == "左營", "車站序"] = 12
            df_transformed.loc[df_transformed["車站"] == "總計", "車站序"] = 13

            df_transformed["進出站"] = table_type

            df_transformed.rename(columns = {
                    "年度 / 月份": "year_month", 
                    "車站序": "station_sequence",
                    "車站": "station",
                    "旅客人數": "visitor_number",
                    "進出站": "entry_exit"
                }, inplace = True)

            # 輸出轉換後的表格內容
            self.logger.info("轉換後的表格內容:")
            self.logger.info(f"欄位名稱: {df_transformed.columns.tolist()}")
            self.logger.info(f"表格形狀: {df_transformed.shape}")
            self.logger.info("完整轉換後內容:")
            self.logger.info(df_transformed)
            
            self.logger.info(f"資料轉換完成，進出站類型: {table_type}")
            return df_transformed
            
        except Exception as e:
            self.logger.error(f"資料轉換時發生錯誤: {e}")
            return pd.DataFrame()
            
    def save_to_postgresql(self, db: Session, df: pd.DataFrame, table_type: str, save_all: bool = False) -> bool:
        """將數據保存到 PostgreSQL 資料庫"""
        try:
            self.logger.info(f"開始保存數據到資料庫，表格類型: {table_type}")
            self.logger.info(f"原始數據形狀: {df.shape}")
            
            # 轉換資料結構
            df_transformed = self.transform_data(df, table_type)
            if df_transformed.empty:
                self.logger.error("資料轉換失敗，無法保存到資料庫")
                return False
                
            self.logger.info(f"轉換後的數據形狀: {df_transformed.shape}")
            self.logger.info(f"轉換後的數據示例:\n{df_transformed.head()}")
                
            # 檢查資料庫是否為空
            is_empty = db.query(StationData).count() == 0
            self.logger.info(f"資料庫是否為空: {is_empty}")
            
            # 檢查是否包含進站或出站的資料
            has_entry_data = db.query(StationData).filter(StationData.entry_exit == "進站").count() == 0
            has_exit_data = db.query(StationData).filter(StationData.entry_exit == "出站").count() == 0
            self.logger.info(f"資料庫中是否有進站資料: {has_entry_data}")
            self.logger.info(f"資料庫中是否有出站資料: {has_exit_data}")
            
            # 獲取上個月的年月
            today = datetime.now()
            last_month = today.replace(day=1) - timedelta(days=1)
            last_month_str = last_month.strftime("%Y-%m")
            self.logger.info(f"上個月的年月: {last_month_str}")
            
            # 準備插入數據
            if is_empty or save_all or has_entry_data or has_exit_data:
                # 如果資料庫為空或需要保存所有資料，插入所有資料
                self.logger.info("插入所有資料")
                for _, row in df_transformed.iterrows():
                    try:
                        new_record = StationData(
                            year_month=row['year_month'],
                            station_sequence=row['station_sequence'],
                            station=row['station'],
                            visitor_number=row['visitor_number'],
                            entry_exit=row['entry_exit']
                        )
                        db.add(new_record)
                        self.logger.info(f"添加記錄: {new_record}")
                    except Exception as e:
                        self.logger.error(f"添加記錄時發生錯誤: {e}")
                        self.logger.error(f"問題記錄: {row}")
            else:
                # 如果資料庫不為空，只插入上個月的資料
                self.logger.info(f"只插入上個月的資料: {last_month_str}")
                # 只保留上個月的資料
                df_last_month = df_transformed[df_transformed['year_month'] == last_month_str]
                if df_last_month.empty:
                    self.logger.info("沒有上個月的資料需要插入")
                    return True
                    
                for _, row in df_last_month.iterrows():
                    try:
                        new_record = StationData(
                            year_month=row['year_month'],
                            station_sequence=row['station_sequence'],
                            station=row['station'],
                            visitor_number=row['visitor_number'],
                            entry_exit=row['entry_exit']
                        )
                        db.add(new_record)
                        self.logger.info(f"添加記錄: {new_record}")
                    except Exception as e:
                        self.logger.error(f"添加記錄時發生錯誤: {e}")
                        self.logger.error(f"問題記錄: {row}")
            
            # 提交事務
            db.commit()
            self.logger.info("數據已成功保存到 PostgreSQL 資料庫")
            return True
            
        except Exception as e:
            self.logger.error(f"保存到 PostgreSQL 時發生錯誤: {e}")
            db.rollback()
            return False
            
    def save_table_to_excel(self, table: pq, filename: str, table_type: str):
        """將表格內容保存到 Excel 檔案"""
        try:
            # 創建輸出目錄
            output_dir = "output"
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
                
            # 完整的檔案路徑
            filepath = os.path.join(output_dir, filename)
            
            # 將表格轉換為 HTML 字串
            html_str = str(table)
            
            # 使用 StringIO 來讀取 HTML 字串
            with io.StringIO(html_str) as f:
                # 讀取表格數據
                df = pd.read_html(f)[0]
            
            # 轉換資料結構
            df_transformed = self.transform_data(df, table_type)
            if df_transformed.empty:
                self.logger.error("資料轉換失敗，無法保存檔案")
                return False
            
            # 保存為 Excel
            df_transformed.to_excel(filepath, index=False, engine='openpyxl')
            
            self.logger.info(f"表格內容已保存到 Excel 檔案: {filepath}")
            return True
        except Exception as e:
            self.logger.error(f"保存 Excel 檔案時發生錯誤: {e}")
            return False
            
    def check_monthly_data(self, year_month: str) -> bool:
        """檢查資料庫中是否已有當月的資料"""
        conn = self.get_db_connection()
        if not conn:
            return False
            
        try:
            cursor = conn.cursor()
            
            # 檢查是否有當月資料
            check_query = """
            SELECT COUNT(*) FROM hsr_vis_data 
            WHERE "year_month" = %s
            """
            cursor.execute(check_query, (year_month,))
            count = cursor.fetchone()[0]
            
            return count > 0
            
        except Exception as e:
            self.logger.error(f"檢查資料時發生錯誤: {e}")
            return False
            
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()
                
    def analyze_structure(self, db: Session = None):
        """分析網頁結構並提取數據"""
        self.logger.info("開始分析網頁結構...")
        
        # 獲取上個月的年月
        today = datetime.now()
        last_month = today.replace(day=1) - timedelta(days=1)
        year_month = last_month.strftime("%Y-%m")
        
        # 檢查是否已有當月資料
        if self.check_monthly_data(year_month):
            self.logger.info(f"資料庫中已有 {year_month} 的資料，跳過爬取")
            return
        
        else:
            # 獲取初始頁面內容
            content = self.get_page_content()
            if not content:
                self.logger.error("無法獲取網頁內容，分析終止")
                return
                
            # 尋找切換按鈕
            buttons = self.find_tab_buttons(content)
            
            # 分析進站數據
            if "entry" in buttons:
                self.logger.info("開始分析進站數據...")
                entry_button = buttons["entry"]
                
                # 根據按鈕屬性決定如何獲取數據
                if entry_button["href"]:
                    # 如果有 href，使用它作為參數
                    entry_content = self.get_page_content(params={"type": "entry"})
                    if entry_content:
                        table = self.find_passenger_table(entry_content, tabtag=entry_button["href"])
                        if table:
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            # 將表格轉換為 DataFrame
                            html_str = str(table)
                            with io.StringIO(html_str) as f:
                                self.df = pd.read_html(f)[0]
                            self.table_type = "進站"
                            # 保存為 Excel 檔案
                            self.save_table_to_excel(table, f"entry_passenger_table_{timestamp}.xlsx", "進站")
                            # 保存到資料庫
                            if db:
                                self.save_to_postgresql(db, self.df, self.table_type, save_all=False)
                        
            # 分析出站數據
            if "exit" in buttons:
                self.logger.info("開始分析出站數據...")
                exit_button = buttons["exit"]
                
                # 根據按鈕屬性決定如何獲取數據
                if exit_button["href"]:
                    # 如果有 href，使用它作為參數
                    exit_content = self.get_page_content(params={"type": "exit"})
                    if exit_content:
                        table = self.find_passenger_table(exit_content, tabtag=exit_button["href"])
                        if table:
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            # 將表格轉換為 DataFrame
                            html_str = str(table)
                            with io.StringIO(html_str) as f:
                                self.df = pd.read_html(f)[0]
                            self.table_type = "出站"
                            # 保存為 Excel 檔案
                            self.save_table_to_excel(table, f"exit_passenger_table_{timestamp}.xlsx", "出站")
                            # 保存到資料庫
                            if db:
                                self.save_to_postgresql(db, self.df, self.table_type, save_all=False)
                
if __name__ == "__main__":
    logger.info("程式開始執行")
    scraper = HSRAnalyzer()
    scraper.analyze_structure()
    logger.info("程式執行完成") 