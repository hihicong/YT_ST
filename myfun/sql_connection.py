#%%
from __future__ import annotations
from sqlalchemy import create_engine
import pymysql
import os, sys, time
import inspect
import __main__
from myfun.config_read import ConfigRead
from myfun.discord import Discord
import pandas as pd
import streamlit as st
from myfun.settings import get_sql_db_url
from typing import Optional


class SQL_connection:

    # def __init__(self, config, Discord):
    #     self.config = config
    #     self.url = config.config_read("SQL_DB", "DB_URL")
    #     self.discord = Discord

    def __init__(self, config, Discord):
        self.config = config
        self.discord = Discord
        self.db_url = None   # 先不讀

    def _get_db_url(self):
        try:
            import streamlit as st
            db_url = st.secrets.get("SQL_DB", {}).get("DB_URL")
            if db_url:
                return db_url
        except Exception:
            pass  # 本機沒有 secrets，正常

        # fallback：本機 config
        try:
            return self.config.config_read("SQL_DB", "DB_URL")
        except Exception:
            return None


    def _get_main_script_name(self):
        try:
            return os.path.splitext(os.path.basename(__main__.__file__))[0]
        except AttributeError:
            return "unknown"  # 遇到像 Jupyter 沒有 __file__ 的情況
        
        # # 修改
        # try:
        #     if hasattr(__main__, '__file__'):
        #         return os.path.splitext(os.path.basename(__main__.__file__))[0]
        #     else:
        #         # 針對 Jupyter 或沒有 __file__ 的情況，使用當前檔案名稱
        #         return os.path.splitext(os.path.basename(__file__))[0]
        # except AttributeError:
        #     return "unknown"  # 遇到像 Jupyter 沒有 __file__ 的情況
    
    def insert_data(self, df, db, stored_procedure, discord = True):
        """
        將 DataFrame 中的數據插入 MySQL 資料庫中。
        """
        function_name = self._get_main_script_name()
        # print(function_name)

        db_url = self._get_db_url()
        if not db_url:
            raise RuntimeError("DB_URL not configured")
        
        try:
            full_url = db_url+db
            # 創建資料庫連接
            engine = create_engine(full_url)
            
            # 嘗試創建資料庫連接並執行 SQL 操作
            try:
                conn = engine.raw_connection()
                cursor = conn.cursor()
            except Exception as e:
                # 資料庫連接失敗，記錄錯誤信息
                self.discord.discord_notify(f"{function_name}異常", f"資料庫連接錯誤: {e}")
                return  # 直接返回，不繼續執行下去

            # 動態生成佔位符
            columns_count = len(df.columns)
            placeholders = ', '.join(['%s'] * columns_count)

            # 存儲過程的 SQL 語句
            insert_query = f"""
                CALL `{stored_procedure}`({placeholders})
            """
            
            # 將 DataFrame 轉換為數據列表
            data_to_insert = df.values.tolist()

            # 批量執行存儲過程
            cursor.executemany(insert_query, data_to_insert)

            # 提交更改
            conn.commit()
            if discord:
                self.discord.discord_notify(f"{function_name}通知", f"數據批量插入成功，共插入 {len(data_to_insert)} 條數據")
            
        except pymysql.MySQLError as e:
            # 捕獲 MySQL 錯誤
            self.discord.discord_notify(f"{function_name}異常", f"MySQL 錯誤: {e}")
            self.discord.discord_notify(f"{function_name}異常", f"SQL 查詢: {insert_query}")
            self.discord.discord_notify(f"{function_name}異常", f"插入數據: {data_to_insert}")
            sys.exit(1)

        except Exception as e:
            # 捕獲其他錯誤
            self.discord.discord_notify(function_name, f"未知錯誤: {e}")
            self.discord.discord_notify(function_name, f"SQL 查詢: {insert_query}")
            self.discord.discord_notify(function_name, f"插入數據: {data_to_insert}")
            sys.exit(1)

        finally:
            # 關閉連接
            cursor.close()
            conn.close()

    def query_data(self, db, query, params=None):
        function_name = self._get_main_script_name()
        max_retries = 3       # 連接最大重試
        empty_retry_limit = 3 # 查詢結果空的最大重試

        db_url = self._get_db_url()
        if not db_url:
            raise RuntimeError("DB_URL not configured")

        for attempt in range(max_retries):
            try:
                full_url = db_url + db
                engine = create_engine(full_url)
                conn = engine.raw_connection()
                cursor = conn.cursor()

                for empty_attempt in range(empty_retry_limit):
                    
                    if params is not None:
                        cursor.execute(query, params)
                    else:
                        cursor.execute(query)
                    columns = [desc[0] for desc in cursor.description]
                    results = cursor.fetchall()
                    df = pd.DataFrame(results, columns=columns)

                    if not df.empty:
                        return df

                    # 結果為空，等待再重試
                    time.sleep(2)

                # 超過空結果重試次數
                self.discord.discord_notify(f"{function_name}通知", "無查詢結果。")
                return pd.DataFrame()

            except Exception as e:
                
                if attempt + 1 < max_retries:
                    time.sleep(2)
                    continue
                else:
                    self.discord.discord_notify(f"{function_name}異常", f"連接或查詢錯誤: {e}")
                    sys.exit(1)

            finally:
                if 'cursor' in locals():
                    cursor.close()
                if 'conn' in locals():
                    conn.close()

if __name__ == '__main__':
    config = ConfigRead("id.config")
    discord = Discord(config)
    SQL = SQL_connection(config, discord)
    # SQL.insert_data(df, 'database_name', 'sp_function_name')
    query = f"""
    SELECT * FROM  `yt_channel_statistics`.`views_and_subscribers` WHERE `channel_id` = 'UCSKidXchLNg_H96bGB-_aCA' AND `date` BETWEEN '2025-12-01' AND '2025-09-31';
    """
    SQL.query_data('yt_channel_statistics',query)



