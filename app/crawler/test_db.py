import psycopg2
import logging

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_connection():
    """測試 PostgreSQL 連接"""
    try:
        # 資料庫連接參數
        conn_params = {
            'dbname': 'hsr_data',
            'user': 'hsr_user',  # 或使用你創建的用戶名
            'password': '33taoTHSR',  # 替換為你的密碼
            'host': 'localhost',
            'port': '5432'
        }
        
        # 建立連接
        logger.info("嘗試連接資料庫...")
        conn = psycopg2.connect(**conn_params)
        
        # 創建游標
        cursor = conn.cursor()
        
        # 測試查詢
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        logger.info(f"PostgreSQL 版本: {version[0]}")
        
        # 測試表格創建
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS test_table (
                id SERIAL PRIMARY KEY,
                test_column VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        logger.info("測試表格創建成功")
        
        # 測試數據插入
        cursor.execute("INSERT INTO test_table (test_column) VALUES (%s)", ("測試數據",))
        logger.info("測試數據插入成功")
        
        # 測試數據查詢
        cursor.execute("SELECT * FROM test_table")
        rows = cursor.fetchall()
        logger.info(f"查詢結果: {rows}")
        
        # 清理測試數據
        cursor.execute("DROP TABLE IF EXISTS test_table")
        logger.info("測試表格已刪除")
        
        # 提交事務
        conn.commit()
        logger.info("所有測試都成功完成！")
        
        return True
        
    except Exception as e:
        logger.error(f"測試過程中發生錯誤: {e}")
        if 'conn' in locals():
            conn.rollback()
        return False
        
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()
            logger.info("資料庫連接已關閉")

if __name__ == "__main__":
    test_connection() 