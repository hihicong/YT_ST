#%%
import zipfile
import pandas as pd
import os
import re

class ReadCSV:

    def __init__(self, zip_folder_path):
        self.zip_folder_path = zip_folder_path

    def extract_info(self, file_name):

        base_name = os.path.splitext(file_name)[0]  # 去掉 .zip

        info = {
        "type": None,
        "date_start": None,
        "date_end": None,
        "name": None
        }

        # 共用的 regex（匹配 type + 日期範圍）
        match_common = re.match(r'^(\S+)\s+(\d{4}-\d{2}-\d{2})_(\d{4}-\d{2}-\d{2})\s+(.+)$', base_name)
        if match_common:
            info["type"] = match_common.group(1)
            info["date_start"] = match_common.group(2)
            info["date_end"] = match_common.group(3)
            name_part = match_common.group(4)

            # 格式 3：數據中心-績效報表_
            if name_part.startswith("數據中心-績效報表_"):
                name_match = re.match(r'數據中心-績效報表_(.+)', name_part)
                if name_match:
                    info["name"] = name_match.group(1)
                    return info

            # 格式 2：數據中心-xxx
            elif name_part.startswith("數據中心-"):
                name_match = re.match(r'數據中心-(.+)', name_part)
                if name_match:
                    info["name"] = name_match.group(1)
                    return info

             # 格式 1：channel 用
            info["name"] = name_part
            return info
        
        # 無法識別格式時，回傳原始檔名
        info["name"] = base_name
        return info
    
    def read_csvs_from_zips(self, type = False, date_start=False, date_end=False, name=True):

        all_data_temp= []

        zip_files = [f for f in os.listdir(self.zip_folder_path) if f.endswith('.zip')]

        # 遍歷每一個 ZIP 檔案
        for zip_file_name in zip_files:
            zip_file_path = os.path.join(self.zip_folder_path, zip_file_name)

            info = self.extract_info(zip_file_name)
    
            # 打開 ZIP 檔案
            with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
                
                csv_files = zip_ref.namelist()
                if not csv_files:
                    print(f"{zip_file_name}内沒有csv檔")
                    continue

                # 讀取 CSV 檔案
                csv_file_name = next((f for f in csv_files if f == "Table data.csv"), None)
                if not csv_file_name:
                    print(f"⚠️ 找不到 Table data.csv in {zip_file_name}，跳過")
                    continue
                with zip_ref.open(csv_file_name) as file:
                    df = pd.read_csv(file)
                    df = df.fillna(0)

                    # 根據輸入參數來動態新增欄位
                    if name:
                        df['series_name'] = info['name']
                    if type:
                        df['type'] = info['type']
                    if date_start:
                        df['date_start'] = info['date_start']
                    if date_end:
                        df['date_end'] = info['date_end']

                    all_data_temp.append(df)  

        if all_data_temp:
            final_df = pd.concat(all_data_temp, ignore_index=True)
            first_column = final_df.columns[0]
            if final_df[first_column].isin(["Total", "Showing top 500 results","總計"]).any():
                final_df = final_df[~final_df[first_column].isin(["Total", "Showing top 500 results","總計"])]

            return final_df
        else:
            return pd.DataFrame()
        
if __name__ == '__main__':
    zip_folder_path_download = r'C:\Users\cti113138\Downloads'
    Read = ReadCSV(zip_folder_path_download)
    df = ReadCSV.read_csvs_from_zips(Read)