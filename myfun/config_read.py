#%%
import os
from configobj import ConfigObj

class ConfigRead:

    def __init__(self, config_file):
        self.config_file = config_file
        self.config_path = os.getcwd() + f'/{config_file}'

    def config_read(self, function_section, function_key):
        if not os.path.exists(self.config_path):
            print(f'文件 {self.config_path} 不存在')
            return ""
    
        config = ConfigObj(self.config_path, write_empty_values=True, encoding='ANSI')
    
        # 檔案存在，進行 section 和 key 的檢查
        if function_section in config:
            if function_key in config[function_section]:
                value = config[function_section][function_key]
                if value:
                    return value
                else:
                    print(f"取config資料, config_read, key 存在但無值, key name: {function_key}")
                    return ""
            else:
                print(f"取config資料, config_read, key不存在, key name: {function_key}, section name: {function_section}")
                return ""
        else:
            print(f"取config資料, config_read, section 不存在, section name: {function_section}")
            return ""

if __name__ == '__main__':
    config = ConfigRead("id.config")

