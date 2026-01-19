import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.header import Header
import chardet

class EmailSender:
    def __init__(self, config):
        self.config = config
        self.server_email = config.config_read("server_id", "server_email")
        self.server_password = config.config_read("server_id", "server_password")
        self.email_receiver = config.config_read("server_id", "email_receiver")
        self.email_Bcc = config.config_read("server_id", "email_Bcc")
        self.SMTP_SERVER = 'tvowa.want-media.com'
        self.SMTP_PORT = 587
    
    def create_message(self, subject, msg, image_name=None, file_name=None):
        """創建電子郵件訊息，包含主體、圖片附件、文字檔案附件"""
        message = MIMEMultipart()
        message['From'] = self.server_email
        message['To'] = self.email_receiver
        message['Bcc'] = self.email_Bcc
        message['Subject'] = f'{subject}'
        
        body = msg
        message.attach(MIMEText(body, 'plain'))
        
        # 如果有圖片附件，則附加圖片
        if image_name:
            self.attach_image(message, image_name)
        
        # 如果有文字檔附件，則附加文字檔
        if file_name:
            self.attach_text_file(message, file_name)
        
        return message
    
    def attach_image(self, message, image_name):
        """將圖片附加到郵件訊息"""
        image_path = os.path.join(os.getcwd(), image_name)
        with open(image_path, 'rb') as img_file:
            img = MIMEImage(img_file.read(), name=os.path.basename(image_path))
            img.add_header(
                'Content-Disposition',
                f'attachment; filename="{Header(image_name, "utf-8").encode()}"'
            )
            message.attach(img)
    
    def attach_text_file(self, message, file_name):
        """將文字檔附加到郵件訊息"""
        file_path = os.path.join(os.getcwd(), file_name)
        with open(file_path, 'rb') as file:
            raw_data = file.read()
            encoding_info = chardet.detect(raw_data)
            file_encoding = encoding_info['encoding']
        
        with open(file_path, 'r', encoding=file_encoding) as file:
            file_content = file.read()
        
        text_part = MIMEText(file_content, 'plain', file_encoding)
        text_part.add_header(
            'Content-Disposition',
            f'attachment; filename="{Header(file_name, "utf-8").encode()}"'
        )
        message.attach(text_part)
    
    def send_email(self, message):
        """發送電子郵件"""
        try:
            with smtplib.SMTP(self.SMTP_SERVER, self.SMTP_PORT) as server:
                server.starttls()  # 加密
                server.login(self.server_email, self.server_password)
                server.send_message(message)
                print("郵件發送成功")
        except Exception as e:
    
            print(f'郵件發送失敗: {e}')

    def mail_message(self, subject, msg, image_name=None, file_name=None):
        """主函式，組合並發送郵件"""
        message = self.create_message(subject, msg, image_name, file_name)
        self.send_email(message)

