#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import json
import time
import logging
import requests
import base64
from bs4 import BeautifulSoup
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

logger = logging.getLogger(__name__)

# 配置信息
class Config:
    # 账号信息
    USERNAME = 'kggzs'
    PASSWORD = 'Wk1724464998'
    
    # 网站URL
    BASE_URL = 'https://club.fnnas.com/'
    LOGIN_URL = BASE_URL + 'member.php?mod=logging&action=login'
    SIGN_URL = BASE_URL + 'plugin.php?id=zqlj_sign'
    
    # Cookie文件路径
    COOKIE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cookies.json')
    
    # 验证码识别API
    CAPTCHA_API_URL = "https://api.acedata.cloud/captcha/recognition/image2text"
    CAPTCHA_API_KEY = "Bearer your_api_key"
    # API注册地址：https://share.acedata.cloud/r/1uKi7kVhwW

class FNSignIn:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
        })
        self.load_cookies()
    
    def load_cookies(self):
        """从文件加载Cookie"""
        if os.path.exists(Config.COOKIE_FILE):
            try:
                with open(Config.COOKIE_FILE, 'r') as f:
                    cookies_list = json.load(f)
                    
                    # 检查是否为新格式的Cookie列表
                    if isinstance(cookies_list, list) and len(cookies_list) > 0 and 'name' in cookies_list[0]:
                        # 新格式：包含完整Cookie属性的列表
                        for cookie_dict in cookies_list:
                            self.session.cookies.set(
                                cookie_dict['name'],
                                cookie_dict['value'],
                                domain=cookie_dict.get('domain'),
                                path=cookie_dict.get('path')
                            )
                    else:
                        # 旧格式：简单的名称-值字典
                        self.session.cookies.update(cookies_list)
                        
                logger.info("已从文件加载Cookie")
                return True
            except Exception as e:
                logger.error(f"加载Cookie失败: {e}")
        return False
    
    def save_cookies(self):
        """保存Cookie到文件"""
        try:
            # 保存完整的Cookie信息，包括域名、路径等属性
            cookies_list = []
            for cookie in self.session.cookies:
                cookie_dict = {
                    'name': cookie.name,
                    'value': cookie.value,
                    'domain': cookie.domain,
                    'path': cookie.path,
                    'expires': cookie.expires,
                    'secure': cookie.secure
                }
                cookies_list.append(cookie_dict)
            
            with open(Config.COOKIE_FILE, 'w') as f:
                json.dump(cookies_list, f)
            logger.info("Cookie已保存到文件")
            return True
        except Exception as e:
            logger.error(f"保存Cookie失败: {e}")
            return False
    
    def check_login_status(self):
        """检查登录状态"""
        try:
            response = self.session.get(Config.BASE_URL)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 检查是否存在登录链接，如果存在则表示未登录
            login_links = soup.select('a[href*="member.php?mod=logging&action=login"]')
            
            # 检查页面内容是否包含用户名
            username_in_page = Config.USERNAME in response.text
            
            # 检查是否有个人中心链接
            user_center_links = soup.select('a[href*="home.php?mod=space"]')
            
            # 输出详细的登录状态检测信息
            logger.debug(f"登录状态检测: 登录链接数量={len(login_links)}, 用户名在页面中={username_in_page}, 个人中心链接数量={len(user_center_links)}")
            
            # 如果没有登录链接或者页面中包含用户名，则认为已登录
            if (len(login_links) == 0 or username_in_page) and len(user_center_links) > 0:
                logger.info("Cookie有效，已登录状态")
                return True
            else:
                logger.info("Cookie无效或已过期，需要重新登录")
                return False
        except Exception as e:
            logger.error(f"检查登录状态失败: {e}")
            return False
    
    def recognize_captcha(self, captcha_url):
        """识别验证码"""
        try:
            # 下载验证码图片
            captcha_response = self.session.get(captcha_url)
            if captcha_response.status_code != 200:
                logger.error(f"下载验证码图片失败，状态码: {captcha_response.status_code}")
                return None
            
            # 将图片转换为Base64编码
            captcha_base64 = base64.b64encode(captcha_response.content).decode('utf-8')
            
            # 调用验证码识别API
            headers = {
                "accept": "application/json",
                "authorization": Config.CAPTCHA_API_KEY,
                "content-type": "application/json"
            }
            
            payload = {
                "image": captcha_base64
            }
            
            api_response = requests.post(Config.CAPTCHA_API_URL, json=payload, headers=headers)
            
            if api_response.status_code != 200:
                logger.error(f"验证码识别API请求失败，状态码: {api_response.status_code}")
                return None
            
            # 解析API响应
            result = api_response.json()
            if 'text' in result:
                logger.info(f"验证码识别成功: {result['text']}")
                return result['text']
            else:
                logger.error(f"验证码识别API返回格式异常: {result}")
                return None
        except Exception as e:
            logger.error(f"验证码识别过程发生错误: {e}")
            return None
    
    def login(self):
        """使用账号密码登录"""
        try:
            # 获取登录页面
            response = self.session.get(Config.LOGIN_URL)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 获取登录表单信息
            login_form = None
            for form in soup.find_all('form'):
                form_id = form.get('id', '')
                if form_id and ('loginform' in form_id or 'lsform' in form_id):
                    login_form = form
                    break
                elif form.get('name') == 'login':
                    login_form = form
                    break
                elif form.get('action') and 'logging' in form.get('action'):
                    login_form = form
                    break
            
            if not login_form:
                # 尝试查找任何表单，可能是登录表单
                all_forms = soup.find_all('form')
                if all_forms:
                    login_form = all_forms[0]  # 使用第一个表单
                    logger.info(f"使用备选表单: ID={login_form.get('id')}, Action={login_form.get('action')}")
            
            if not login_form:
                logger.error("未找到登录表单")
                return False
                
            # 提取登录表单ID中的随机部分
            form_id = login_form.get('id', '')
            login_hash = form_id.split('_')[-1] if '_' in form_id else ''
            
            # 获取登录表单的action属性
            form_action = login_form.get('action', '')
            logger.info(f"找到登录表单: ID={form_id}, Action={form_action}")
            
            # 获取表单字段
            formhash = soup.find('input', {'name': 'formhash'})
            if not formhash:
                logger.error("未找到登录表单的formhash字段")
                return False
            
            # 获取表单字段
            formhash = formhash['value']
            
            # 获取用户名输入框ID
            username_input = soup.find('input', {'name': 'username'})
            username_id = username_input.get('id', '') if username_input else ''
            
            # 获取密码输入框ID
            password_input = soup.find('input', {'name': 'password'})
            password_id = password_input.get('id', '') if password_input else ''
            
            logger.info(f"找到用户名输入框ID: {username_id}")
            logger.info(f"找到密码输入框ID: {password_id}")
            
            # 构建登录数据
            login_data = {
                'formhash': formhash,
                'referer': Config.BASE_URL,
                'loginfield': 'username',
                'username': Config.USERNAME,
                'password': Config.PASSWORD,
                'questionid': '0',
                'answer': '',
                'cookietime': '2592000',  # 保持登录状态30天
                'loginsubmit': 'true'
            }
            
            # 添加特定的表单字段
            if username_id:
                login_data[username_id] = Config.USERNAME
            if password_id:
                login_data[password_id] = Config.PASSWORD
            
            # 检查是否需要验证码
            seccodeverify = soup.find('input', {'name': 'seccodeverify'})
            if seccodeverify:
                logger.info("检测到需要验证码，尝试自动识别验证码")
                
                # 获取验证码ID
                seccode_id = seccodeverify.get('id', '').replace('seccodeverify_', '')
                
                # 获取验证码图片URL
                captcha_img = soup.find('img', {'src': re.compile(r'misc\.php\?mod=seccode')})
                if not captcha_img:
                    logger.error("未找到验证码图片")
                    return False
                
                captcha_url = Config.BASE_URL + captcha_img['src']
                logger.info(f"验证码图片URL: {captcha_url}")
                
                # 识别验证码
                captcha_text = self.recognize_captcha(captcha_url)
                if not captcha_text:
                    logger.error("验证码识别失败")
                    return False
                
                # 添加验证码到登录数据
                login_data['seccodeverify'] = captcha_text
                login_data['seccodehash'] = seccode_id
            
            # 更新请求头，模拟真实浏览器
            self.session.headers.update({
                'Origin': Config.BASE_URL.rstrip('/'),
                'Referer': Config.LOGIN_URL,
                'Content-Type': 'application/x-www-form-urlencoded',
                'Upgrade-Insecure-Requests': '1'
            })
            
            # 构建登录URL
            login_url = f"{Config.LOGIN_URL}&loginsubmit=yes&inajax=1"
            
            # 发送登录请求
            login_response = self.session.post(login_url, data=login_data, allow_redirects=True)
            
            # 检查登录结果
            if '验证码' in login_response.text and '验证码错误' in login_response.text:
                logger.error("验证码错误，登录失败")
                return False
            
            # 检查登录是否成功
            if 'succeedhandle_' in login_response.text or self.check_login_status():
                logger.info(f"账号 {Config.USERNAME} 登录成功")
                self.save_cookies()
                return True
            else:
                logger.error("登录失败，请检查账号密码")
                logger.debug(f"登录响应: {login_response.text}")
                return False
        except Exception as e:
            logger.error(f"登录过程发生错误: {e}")
            return False
    
    def check_sign_status(self):
        """检查签到状态"""
        try:
            response = self.session.get(Config.SIGN_URL)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 查找签到按钮
            sign_btn = soup.select_one('.signbtn .btna')
            if not sign_btn:
                logger.error("未找到签到按钮")
                return None, None
            
            # 获取签到链接和状态
            sign_text = sign_btn.text.strip()
            sign_link = sign_btn.get('href')
            
            # 提取sign参数
            sign_param = None
            if sign_link:
                match = re.search(r'sign=([^&]+)', sign_link)
                if match:
                    sign_param = match.group(1)
            
            return sign_text, sign_param
        except Exception as e:
            logger.error(f"检查签到状态失败: {e}")
            return None, None
    
    def do_sign(self, sign_param):
        """执行签到"""
        try:
            sign_url = f"{Config.SIGN_URL}&sign={sign_param}"
            response = self.session.get(sign_url)
            
            # 检查签到结果
            if response.status_code == 200:
                # 再次检查签到状态
                sign_text, _ = self.check_sign_status()
                if sign_text == "今日已打卡":
                    logger.info("签到成功")
                    return True
                else:
                    logger.error("签到请求已发送，但状态未更新")
                    return False
            else:
                logger.error(f"签到请求失败，状态码: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"签到过程发生错误: {e}")
            return False
    
    def get_sign_info(self):
        """获取签到信息"""
        try:
            response = self.session.get(Config.SIGN_URL)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 查找签到信息区域
            sign_info_divs = soup.find_all('div', class_='bm')
            sign_info_div = None
            for div in sign_info_divs:
                header = div.find('div', class_='bm_h')
                if header and '我的打卡动态' in header.get_text():
                    sign_info_div = div
                    break
            
            if not sign_info_div:
                logger.error("未找到签到信息区域")
                return {}
            
            # 查找签到信息列表
            info_list = sign_info_div.find('div', class_='bm_c').find_all('li')
            
            # 解析签到信息
            sign_info = {}
            for item in info_list:
                text = item.get_text(strip=True)
                if '：' in text:
                    key, value = text.split('：', 1)
                    sign_info[key] = value
            
            return sign_info
        except Exception as e:
            logger.error(f"获取签到信息失败: {e}")
            return {}
    
    def run(self):
        """运行签到流程"""
        logger.info("===== 开始运行签到脚本 =====")
        
        # 检查登录状态
        if not self.check_login_status():
            # 如果未登录，尝试登录
            if not self.login():
                logger.error("登录失败，签到流程终止")
                return False
        
        # 检查签到状态
        sign_text, sign_param = self.check_sign_status()
        if sign_text is None or sign_param is None:
            logger.error("获取签到状态失败，签到流程终止")
            return False
        
        logger.info(f"当前签到状态: {sign_text}")
        
        # 如果未签到，执行签到
        if sign_text == "点击打卡":
            logger.info("开始执行签到...")
            if self.do_sign(sign_param):
                # 获取并记录签到信息
                sign_info = self.get_sign_info()
                if sign_info:
                    logger.info("===== 签到信息 =====")
                    for key, value in sign_info.items():
                        logger.info(f"{key}: {value}")
                return True
            else:
                logger.error("签到失败")
                return False
        elif sign_text == "今日已打卡":
            logger.info("今日已签到，无需重复签到")
            # 获取并记录签到信息
            sign_info = self.get_sign_info()
            if sign_info:
                logger.info("===== 签到信息 =====")
                for key, value in sign_info.items():
                    logger.info(f"{key}: {value}")
            return True
        else:
            logger.warning(f"未知的签到状态: {sign_text}，签到流程终止")
            return False


if __name__ == "__main__":
    try:
        sign = FNSignIn()
        sign.run()
    except Exception as e:
        logger.error(f"脚本运行出错: {e}")
