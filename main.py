import datetime

import requests
from loguru import logger
import tomllib  # 确保导入tomllib以读取配置文件
import os  # 确保导入os模块

from WechatAPI import WechatAPIClient
from utils.decorators import *
from utils.plugin_base import PluginBase
import redis
import random

# Connect to Redis (default: localhost, port 6379)
r = redis.Redis(host='localhost', port=6379, db=0)

class DailyFortunePlugin(PluginBase):
    description = "今日运势插件"
    author = "Debin"
    version = "1.0.0"

    # 同步初始化
    def __init__(self):
        super().__init__()

        # 获取配置文件路径
        config_path = os.path.join(os.path.dirname(__file__), "config.toml")
        
        try:
            with open(config_path, "rb") as f:
                config = tomllib.load(f)
                
            # 读取基本配置
            basic_config = config.get("basic", {})
            self.enable = basic_config.get("enable", False)  # 读取插件开关

            self.fortune_command =  basic_config.get("command", ["今日运势", "每日运势"]) 

            luck_config = config.get("luck", {})
            self.luck_messages = luck_config.get("messages", [])
            self.luck_colors = luck_config.get("colors", [])

        except Exception as e:
            logger.error(f"加载ExamplePlugin配置文件失败: {str(e)}")
            self.enable = False  # 如果加载失败，禁用插件

    # 异步初始化
    async def async_init(self):
        return

    def get_random_luck_message(self):
        return random.choice(self.luck_messages)['messages']

    def get_random_luck_color(self):
        return random.choice(self.luck_colors)['colors']

    def get_stars(self, luck_number):
        stars = "★★"
        for i in range(7):
            if i < luck_number:
                stars += "★"
            else:
                stars += "☆"
        return stars

    def get_hitokoto(self):
        try:
            response = requests.get('https://v1.hitokoto.cn')
            response.raise_for_status()
            data = response.json()
            return f"{data.get('hitokoto', '')} - 【 {data.get('from', '')} 】"

        except Exception as e:
            logger.error(f"获取一言失败: {str(e)}")
            return ""
        
    @on_text_message(priority=99)
    async def handle_text(self, bot: WechatAPIClient, message: dict):
        if not self.enable:
            return  True # 如果插件未启用，直接返回
        
        content = str(message["Content"]).strip()
        command = content.split(" ")

        if not len(command) or command[0] not in self.fortune_command:
            return True

        wxid = message["FromWxid"]
        userexid = message["SenderWxid"]
        # 从 redis 获取运势数据
        ## 获取今天的年月日
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        fortune_data = r.get(f"fortunelucky:{userexid}:{today}")
        if fortune_data:
            fortune_data = fortune_data.decode("utf-8")
        else:
            ## 生成随机数 0-7 
            luck_level = random.randint(0, 7)
            luck_number = random.randint(0, 100)
            fortune_data = f"运势：{self.get_random_luck_message()[7 - luck_level]}\n星级：{self.get_stars(luck_level)}\n幸运数字：{luck_number}\n幸运颜色：{self.get_random_luck_color()}"
            r.set(f"fortunelucky:{userexid}:{today}", fortune_data, ex=86400)

        hitokoto = self.get_hitokoto()
        if hitokoto:
            fortune_data += f"\n\n{hitokoto}"
        await bot.send_text_message(wxid, fortune_data)
        return False
        
