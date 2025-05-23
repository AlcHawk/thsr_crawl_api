# THSR Crawler

這是一個用於爬取高鐵網站數據的 API 服務，可以獲取各站點的進出站旅客人數數據。

## Function

- 自動爬取高鐵網站數據
- 支持進站和出站數據的獲取
- 數據存儲到 PostgreSQL 數據庫
- 提供 RESTful API 接口
- 自動生成 Excel 報表

## Require

- Python 3.8+
- FastAPI
- PostgreSQL
- SQLAlchemy
- PyQuery
- Pandas

## Installation and Execution

1. Clone Repository：
```bash
git clone https://github.com/您的用戶名/倉庫名.git
cd 倉庫名
```

2. Install Dependency：
```bash
pip install -r requirements.txt
```

3. Set Enviromental Variables：
```bash
DB_NAME=hsr_data
DB_USER=hsr_user
DB_PASSWORD=您的密碼
DB_HOST=localhost
DB_PORT=5432
```

4. Run Service：
```bash
python -m app.main
```

## API 接口

- `GET /`：獲取服務狀態
- `GET /data`：獲取數據
- `POST /crawl`：觸發爬蟲任務

## 部署

服務已配置為可在 Render 平台上部署。部署時需要設置相應的環境變數。

## 日誌

日誌文件保存在 `logs` 目錄下，文件名格式為 `hsr_crawler_YYYYMMDD_HHMMSS.log`。
若是在 Render 上，則會是透過 Render Log 去呈現。

## 輸出文件

生成的 Excel 文件保存在 `output` 目錄下，文件名格式為 `passenger_table_YYYYMMDD_HHMMSS.xlsx`。 