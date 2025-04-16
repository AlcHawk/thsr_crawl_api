   -- 創建資料庫
   -- CREATE DATABASE hsr_data;
   
	-- 創建專用用戶（可選，但建議）
	CREATE USER hsr_user WITH PASSWORD '33taoTHSR';

	-- 創建表格
	CREATE TABLE IF NOT EXISTS hsr_vis_data (
		id SERIAL PRIMARY KEY,
		"year_month" VARCHAR(20),
		"station_sequence" INTEGER,
		"station" VARCHAR(100),
		"visitor_number" INTEGER,
		"entry_exit" VARCHAR(10),
		"created_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
	);
	
	-- 授予權限
	GRANT ALL PRIVILEGES ON DATABASE hsr_data TO hsr_user;
	
	-- 授予 schema 權限
	GRANT USAGE ON SCHEMA public TO hsr_user;

	-- 授予表格創建權限
	GRANT CREATE ON SCHEMA public TO hsr_user;
	
	-- 授予所有現有表格的權限
	GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO hsr_user;
	
	-- 授予序列的權限
	GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO hsr_user;
	
	-- 授予未來創建的表格的權限
	ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO hsr_user;
