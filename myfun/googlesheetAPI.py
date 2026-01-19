#%%

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pandas as pd


class GoogleSheetWriter:

    def __init__(self, service_account_file, spreadsheet_id):
        """ 初始化 Google Sheets API 客戶端 """
        self.spreadsheet_id = spreadsheet_id
        self.creds = Credentials.from_service_account_file(
            service_account_file, 
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        self.service = build('sheets', 'v4', credentials=self.creds)

    def get_sheet_id(self, sheet_name):
        """ 根據工作表名稱獲取 sheetId """
        try:

            result = self.service.spreadsheets().get(
                spreadsheetId=self.spreadsheet_id
            ).execute()

            sheets = result.get('sheets', [])
            for sheet in sheets:
                if sheet['properties']['title'] == sheet_name:
                    return sheet['properties']['sheetId']
            return None  # 如果沒有找到工作表，返回 None
        except HttpError as err:
            print(f"Error in get_sheet_id: {err}")
            return None

    def clear_data(self, sheet_name, range_string):
        try:
            # 构建要清除的范围，例如 'Sheet1!A1:C3'
            range_to_clear = f'{sheet_name}!{range_string}'

            # 清除该范围的数据
            result = self.service.spreadsheets().values().clear(
                spreadsheetId=self.spreadsheet_id,
                range=range_to_clear
            ).execute()

            print(f"Range {range_string} successfully cleared in {sheet_name}")
        except Exception as e:
            print(f"Error occurred while clearing range {range_string}: {e}")

    def update_data(self, data_list, sheet_name, range_string, insert_to_next_empty_cell=False):
        try:
            # 如果传入的是 pandas DataFrame，转换为二维列表
            if isinstance(data_list, pd.DataFrame):
                data_list = data_list.values.tolist()

            range_to_update = f'{sheet_name}!{range_string}'

            # 如果指定了插入到下一个空白单元格
            if insert_to_next_empty_cell: 

                column = ''.join([char for char in range_string if char.isalpha()])

                # 获取现有的数据
                result = self.service.spreadsheets().values().get(
                    spreadsheetId=self.spreadsheet_id,
                    range=f'{sheet_name}!{column}:{column}'
                ).execute()

                values = result.get('values', [])

                # 找到第一个空白的行
                next_empty_row = len(values) + 1  # 如果没有空白格，会加到最后一行

                range_to_update = f'{sheet_name}!{column}{next_empty_row}'

            new_data = data_list

            # 构建要发送的请求体
            body = {
                'values': new_data
            }

            # 更新指定范围的资料
            result = self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=range_to_update,  # 这里使用了插入的range
                valueInputOption='USER_ENTERED',  # 使用 'USER_ENTERED' 格式，表示写入原始数据
                body=body
            ).execute()

            print(f"Data successfully written to {sheet_name} at {range_to_update}")
        
        except Exception as e:
            print(f"Error occurred while updating data: {e}")

        except HttpError as err:
            print(f"An error occurred: {err}")
            print(f"error content: {err.content}")
            # message_list.append((f"An error occurred: {err}"))

if __name__ == '__main__':
    googlesheetID = 'GSID'
    API = GoogleSheetWriter('trusty-charmer-417507-76409546304f.json', googlesheetID)
    GoogleSheetWriter.clear_data(API,'GS Sheet','CELL:CELL')
    GoogleSheetWriter.update_data(API, df,'Sheet', 'CELL')
    GoogleSheetWriter.update_data(API, df, 'Sheet','CELL', True)