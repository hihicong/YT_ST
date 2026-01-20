#%%
from __future__ import annotations
import requests, os
from myfun.config_read import ConfigRead
from typing import Optional
from myfun.settings import get_discord_webhook_url


class Discord: 

    # def __init__(self, config):
    #     self.config = config
    #     self.url = config.config_read("discord_webhook", "url")

    def __init__(self, config=None, webhook_url: Optional[str] = None):
        self.config = config
        self.webhook_url = webhook_url  # 可外部傳入（例如測試）

    def discord_notify(self, msg_title, message_body, image_paths = None):

        url = self.webhook_url or get_discord_webhook_url(self.config)
        if not url:
            print("Discord webhook URL not found.")
            return

        # 默認沒有image path
        if image_paths is None:
            image_paths = []

        # 如果 message_body 是字符串且不是列表，將它包裝成列表
        if isinstance(message_body, str):
            message_body = [message_body]

        message_body_str = "\n".join([str(item) if isinstance(item, tuple) else str(item) for item in message_body])
        msg = msg_title + "\n" + message_body_str
        
        # 訊息內容
        data = {
            'content': msg  # 這是你想要發送的訊息
        }

        # 打開並上傳所有圖片
        files = {}
        if image_paths:
            for i, image_path in enumerate(image_paths):
                with open(image_path, 'rb') as image_file:
                    files[f'file{i}'] = (image_path, image_file.read())  # 使用不同的文件鍵名來發送多張圖片

        # 發送請求到 Discord Webhook
        if files:  # 只有在有圖片的情況下才加入 `files`
            response = requests.post(url, data=data, files=files)
        else:
            response = requests.post(url, data=data)

        if response.status_code == 204:
            print("訊息發送成功")
        else:
            print(f"錯誤: {response.status_code}, {response.text}")

if __name__ == '__main__':
    config = ConfigRead("id.config")
    discord = Discord(config)
    discord.discord_notify("測試", f"測試訊息")

