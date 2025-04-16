import logging
import sys
from datetime import datetime
import os

# 全局變量，用於存儲是否已經初始化過 logger
_logger_initialized = False

def setup_logger():
    global _logger_initialized
    
    # 創建 logs 目錄（如果不存在）
    if not os.path.exists("logs"):
        os.makedirs("logs")
    
    # 生成帶時間戳的日誌文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = f"logs/hsr_crawler_{timestamp}.log"
    
    # 配置日誌記錄器
    logger = logging.getLogger("hsr_crawler")
    
    # 如果已經初始化過，直接返回 logger
    if _logger_initialized:
        return logger
        
    # 設置日誌級別
    logger.setLevel(logging.INFO)
    
    # 創建格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 添加控制台處理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 添加文件處理器
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # 標記為已初始化
    _logger_initialized = True
    
    return logger 