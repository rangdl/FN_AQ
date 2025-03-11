#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
from bs4 import BeautifulSoup
import re
import logging
import os
import time
from datetime import datetime

# 配置日志
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f'sign_{datetime.now().strftime("%Y%m%d")}.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class FNClubSigner:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.base_url = 'https://club.fnnas.com/'
        self.login_url = self.base_url + 'member.php?mod=logging&action=login'
        self.sign_url = self.base_url + 'plugin.php?id=zqlj_sign'
        
        # 设置请求头，模拟浏览器访问
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        self.session.headers.update(self.headers)
    
    def login(self):
        """登录网站"""
        logging.info(f"尝试使用账号 {self.username} 登录")
        
        try:
            # 获取登录页面，提取表单信息
            response = self.session.get(self.login_url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 提取formhash
            formhash_input = soup.find('input', {'name': 'formhash'})
            formhash = formhash_input['value'] if formhash_input else ''
            
            # 提取登录所需的其他参数
            login_data = {
                'formhash': formhash,
                'referer': self.base_url,
                'loginfield': 'username',
                'username': self.username,
                'password': self.password,
                'questionid': '0',
                'answer': '',
                'loginsubmit': 'true'
            }
            
            # 提交登录请求
            login_response = self.session.post(self.login_url + '&loginsubmit=yes&handlekey=login&loginhash=LuS9h', data=login_data)
            
            # 检查登录是否成功（修改检查逻辑）
            if '欢迎您回来' in login_response.text or '退出' in login_response.text:
                logging.info("登录成功")
                return True
            else:
                logging.error("登录失败，请检查账号密码")
                return False
                
        except Exception as e:
            logging.error(f"登录过程出错: {str(e)}")
            return False
    
    def check_sign_status(self):
        """检查签到状态，返回是否已签到和sign参数"""
        try:
            response = self.session.get(self.sign_url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 查找签到按钮
            sign_div = soup.find('div', {'class': 'bm signbtn cl'})
            if not sign_div:
                logging.error("未找到签到按钮")
                return None, None
            
            sign_link = sign_div.find('a')
            if not sign_link:
                logging.error("未找到签到链接")
                return None, None
            
            # 提取sign参数
            sign_href = sign_link.get('href', '')
            sign_match = re.search(r'sign=([0-9a-f]+)', sign_href)
            sign_param = sign_match.group(1) if sign_match else None
            
            # 判断是否已签到
            is_signed = '今日已打卡' in sign_link.text
            
            return is_signed, sign_param
            
        except Exception as e:
            logging.error(f"检查签到状态出错: {str(e)}")
            return None, None
    
    def do_sign(self, sign_param):
        """执行签到操作"""
        if not sign_param:
            logging.error("签到参数为空，无法签到")
            return False
        
        try:
            sign_url_with_param = f"{self.sign_url}&sign={sign_param}"
            response = self.session.get(sign_url_with_param)
            
            # 检查签到是否成功
            if '打卡成功' in response.text or '今日已打卡' in response.text:
                logging.info("签到成功")
                return True
            else:
                logging.error("签到失败")
                return False
                
        except Exception as e:
            logging.error(f"签到过程出错: {str(e)}")
            return False
    
    def get_sign_info(self):
        """获取签到信息"""
        try:
            response = self.session.get(self.sign_url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 查找签到信息区域
            info_divs = soup.find_all('div', {'class': 'bm'})
            info_div = None
            for div in info_divs:
                strong_tag = div.find('strong')
                if strong_tag and '我的打卡动态' in strong_tag.text:
                    info_div = div.find('div', {'class': 'bm_c'})
                    break
            
            if not info_div:
                logging.error("未找到签到信息区域")
                return {}
            
            # 提取签到信息
            info_items = info_div.find_all('li')
            sign_info = {}
            
            for item in info_items:
                if '：' in item.text:
                    key, value = item.text.split('：', 1)
                    sign_info[key] = value.strip()
            
            # 记录详细的签到信息
            if sign_info:
                logging.info("获取到的详细签到信息:")
                for key, value in sign_info.items():
                    logging.info(f"{key}：{value}")
            
            return sign_info
            
        except Exception as e:
            logging.error(f"获取签到信息出错: {str(e)}")
            return {}
    
    def run(self):
        """运行签到流程"""
        # 登录
        if not self.login():
            return False
        
        # 检查签到状态
        is_signed, sign_param = self.check_sign_status()
        
        if is_signed is None:
            logging.error("无法获取签到状态")
            return False
        
        # 如果未签到，则执行签到
        if not is_signed:
            logging.info("今日未签到，准备签到")
            if not self.do_sign(sign_param):
                return False
        else:
            logging.info("今日已签到，无需重复签到")
        
        # 获取并记录签到信息
        sign_info = self.get_sign_info()
        if sign_info:
            logging.info("签到信息获取成功:")
            for key, value in sign_info.items():
                logging.info(f"{key}: {value}")
        
        return True

def main():
    # 从环境变量或配置文件获取账号密码
    username = os.environ.get('FNCLUB_USERNAME', '账号')  # 默认账号
    password = os.environ.get('FNCLUB_PASSWORD', '密码')  # 默认密码
    
    # 创建签到器并运行
    signer = FNClubSigner(username, password)
    
    # 添加重试机制
    max_retries = 3
    for i in range(max_retries):
        logging.info(f"第 {i+1} 次尝试签到")
        if signer.run():
            break
        else:
            if i < max_retries - 1:
                wait_time = 5 * (i + 1)  # 递增等待时间
                logging.info(f"签到失败，{wait_time}秒后重试...")
                time.sleep(wait_time)
            else:
                logging.error("达到最大重试次数，签到失败")

if __name__ == '__main__':
    main()
