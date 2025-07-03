#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import json
import time
import logging
import requests
import base64
import urllib.parse
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
    USERNAME = os.getenv('FN_USERNAME', '')  # 修改为你的用户名
    PASSWORD = os.getenv('FN_PASSWORD', '')  # 修改为你的密码
    
    # 网站URL
    BASE_URL = 'https://club.fnnas.com/'
    LOGIN_URL = BASE_URL + 'member.php?mod=logging&action=login'
    SIGN_URL = BASE_URL + 'plugin.php?id=zqlj_sign'
    
    # Cookie文件路径
    COOKIE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cookies.json')
    
    # 验证码识别API (百度OCR API)
    CAPTCHA_API_URL = "https://aip.baidubce.com/rest/2.0/ocr/v1/accurate_basic"
    API_KEY = os.getenv('FN_BD_API_KEY', '')  # 替换为你的百度OCR API Key
    SECRET_KEY = os.getenv('FN_BD_SECRET_KEY', '')  # 替换为你的百度OCR Secret Key
    
    # 重试设置
    MAX_RETRIES = 3  # 最大重试次数
    RETRY_DELAY = 2  # 重试间隔(秒)
    
    # Token缓存文件
    TOKEN_CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'token_cache.json')

    PUSH_KEY = os.getenv('FN_PUSH_KEY', '')

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

    def get_access_token(self):
        """获取百度API的access_token，带缓存功能"""
        try:
            # 检查是否有缓存的token
            if os.path.exists(Config.TOKEN_CACHE_FILE):
                try:
                    with open(Config.TOKEN_CACHE_FILE, 'r') as f:
                        token_data = json.load(f)
                        # 检查token是否过期（百度token有效期为30天）
                        if token_data.get('expires_time', 0) > time.time():
                            logger.info("使用缓存的access_token")
                            return token_data.get('access_token')
                        else:
                            logger.info("缓存的access_token已过期，重新获取")
                except Exception as e:
                    logger.warning(f"读取token缓存文件失败: {e}")
            
            # 获取新token
            url = "https://aip.baidubce.com/oauth/2.0/token"
            params = {
                "grant_type": "client_credentials", 
                "client_id": Config.API_KEY, 
                "client_secret": Config.SECRET_KEY
            }
            
            # 添加重试机制
            for retry in range(Config.MAX_RETRIES):
                try:
                    response = requests.post(url, params=params)
                    if response.status_code == 200:
                        result = response.json()
                        access_token = str(result.get("access_token"))
                        expires_in = result.get("expires_in", 2592000)  # 默认30天
                        
                        # 缓存token
                        token_cache = {
                            'access_token': access_token,
                            'expires_time': time.time() + expires_in - 86400  # 提前一天过期
                        }
                        try:
                            with open(Config.TOKEN_CACHE_FILE, 'w') as f:
                                json.dump(token_cache, f)
                            logger.info("access_token已缓存")
                        except Exception as e:
                            logger.warning(f"缓存access_token失败: {e}")
                        
                        return access_token
                    else:
                        logger.error(f"获取access_token失败，状态码: {response.status_code}，重试({retry+1}/{Config.MAX_RETRIES})")
                        if retry < Config.MAX_RETRIES - 1:
                            time.sleep(Config.RETRY_DELAY)
                except Exception as e:
                    logger.error(f"获取access_token请求异常: {e}，重试({retry+1}/{Config.MAX_RETRIES})")
                    if retry < Config.MAX_RETRIES - 1:
                        time.sleep(Config.RETRY_DELAY)
            
            logger.error(f"获取access_token失败，已达到最大重试次数({Config.MAX_RETRIES})")
            return None
        except Exception as e:
            logger.error(f"获取access_token过程发生错误: {e}")
            return None
    
    def recognize_captcha(self, captcha_url):
        """识别验证码，带重试机制"""
        for retry in range(Config.MAX_RETRIES):
            try:
                # 下载验证码图片
                captcha_response = self.session.get(captcha_url)
                if captcha_response.status_code != 200:
                    logger.error(f"下载验证码图片失败，状态码: {captcha_response.status_code}，重试({retry+1}/{Config.MAX_RETRIES})")
                    if retry < Config.MAX_RETRIES - 1:
                        time.sleep(Config.RETRY_DELAY)
                        continue
                    return None
                
                # 将图片转换为Base64编码
                captcha_base64 = base64.b64encode(captcha_response.content).decode('utf-8')
                
                # 获取access_token
                access_token = self.get_access_token()
                if not access_token:
                    logger.error(f"获取百度API access_token失败，重试({retry+1}/{Config.MAX_RETRIES})")
                    if retry < Config.MAX_RETRIES - 1:
                        time.sleep(Config.RETRY_DELAY)
                        continue
                    return None
                    
                # 构建API请求URL
                url = f"{Config.CAPTCHA_API_URL}?access_token={access_token}"
                
                # 构建请求参数
                payload = f'image={urllib.parse.quote_plus(captcha_base64)}&detect_direction=false&paragraph=false&probability=false'
                
                # 设置请求头
                headers = {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Accept': 'application/json'
                }
                
                # 发送请求
                api_response = requests.request("POST", url, headers=headers, data=payload.encode("utf-8"))
                
                if api_response.status_code != 200:
                    logger.error(f"验证码识别API请求失败，状态码: {api_response.status_code}，重试({retry+1}/{Config.MAX_RETRIES})")
                    if retry < Config.MAX_RETRIES - 1:
                        time.sleep(Config.RETRY_DELAY)
                        continue
                    return None
                
                # 解析API响应
                result = api_response.json()
                if 'words_result' in result and len(result['words_result']) > 0:
                    captcha_text = result['words_result'][0]['words']
                    # 清理验证码文本，移除空格和特殊字符
                    captcha_text = re.sub(r'[\s\W]+', '', captcha_text)
                    logger.info(f"验证码识别成功: {captcha_text}")
                    return captcha_text
                elif 'error_code' in result:
                    logger.error(f"验证码识别API返回错误: {result.get('error_code')}, {result.get('error_msg')}，重试({retry+1}/{Config.MAX_RETRIES})")
                    if retry < Config.MAX_RETRIES - 1:
                        time.sleep(Config.RETRY_DELAY)
                        continue
                    return None
                else:
                    logger.error(f"验证码识别API返回格式异常: {result}，重试({retry+1}/{Config.MAX_RETRIES})")
                    if retry < Config.MAX_RETRIES - 1:
                        time.sleep(Config.RETRY_DELAY)
                        continue
                    return None
            except Exception as e:
                logger.error(f"验证码识别过程发生错误: {e}，重试({retry+1}/{Config.MAX_RETRIES})")
                if retry < Config.MAX_RETRIES - 1:
                    time.sleep(Config.RETRY_DELAY)
                    continue
                return None
        
        logger.error(f"验证码识别失败，已达到最大重试次数({Config.MAX_RETRIES})")
        return None
    
    def login(self):
        """使用账号密码登录，带重试机制"""
        for retry in range(Config.MAX_RETRIES):
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
                    logger.error(f"未找到登录表单，重试({retry+1}/{Config.MAX_RETRIES})")
                    if retry < Config.MAX_RETRIES - 1:
                        time.sleep(Config.RETRY_DELAY)
                        continue
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
                    logger.error(f"未找到登录表单的formhash字段，重试({retry+1}/{Config.MAX_RETRIES})")
                    if retry < Config.MAX_RETRIES - 1:
                        time.sleep(Config.RETRY_DELAY)
                        continue
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
                        logger.error(f"未找到验证码图片，重试({retry+1}/{Config.MAX_RETRIES})")
                        if retry < Config.MAX_RETRIES - 1:
                            time.sleep(Config.RETRY_DELAY)
                            continue
                        return False
                    
                    captcha_url = Config.BASE_URL + captcha_img['src']
                    logger.info(f"验证码图片URL: {captcha_url}")
                    
                    # 识别验证码
                    captcha_text = self.recognize_captcha(captcha_url)
                    if not captcha_text:
                        logger.error(f"验证码识别失败，重试({retry+1}/{Config.MAX_RETRIES})")
                        if retry < Config.MAX_RETRIES - 1:
                            time.sleep(Config.RETRY_DELAY)
                            continue
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
                
                # 添加更多调试信息
                logger.debug(f"登录请求URL: {login_url}")
                logger.debug(f"登录请求数据: {login_data}")
                logger.debug(f"登录响应状态码: {login_response.status_code}")
                logger.debug(f"登录响应内容: {login_response.text[:500]}...")
                
                # 检查登录结果
                if '验证码' in login_response.text and '验证码错误' in login_response.text:
                    logger.error(f"验证码错误，登录失败，重试({retry+1}/{Config.MAX_RETRIES})")
                    if retry < Config.MAX_RETRIES - 1:
                        time.sleep(Config.RETRY_DELAY)
                        continue
                    return False
                
                # 检查登录是否成功
                if 'succeedhandle_' in login_response.text or self.check_login_status():
                    logger.info(f"账号 {Config.USERNAME} 登录成功")
                    self.save_cookies()
                    return True
                else:
                    logger.error(f"登录失败，请检查账号密码，重试({retry+1}/{Config.MAX_RETRIES})")
                    logger.debug(f"登录响应: {login_response.text[:200]}...")
                    if retry < Config.MAX_RETRIES - 1:
                        time.sleep(Config.RETRY_DELAY)
                        continue
                    return False
            except Exception as e:
                logger.error(f"登录过程发生错误: {e}，重试({retry+1}/{Config.MAX_RETRIES})")
                if retry < Config.MAX_RETRIES - 1:
                    time.sleep(Config.RETRY_DELAY)
                    continue
                return False
        
        logger.error(f"登录失败，已达到最大重试次数({Config.MAX_RETRIES})")
        return False
    
    def check_sign_status(self):
        """检查签到状态，带重试机制"""
        for retry in range(Config.MAX_RETRIES):
            try:
                response = self.session.get(Config.SIGN_URL)
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 查找签到按钮
                sign_btn = soup.select_one('.signbtn .btna')
                if not sign_btn:
                    logger.error(f"未找到签到按钮，重试({retry+1}/{Config.MAX_RETRIES})")
                    if retry < Config.MAX_RETRIES - 1:
                        time.sleep(Config.RETRY_DELAY)
                        continue
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
                logger.error(f"检查签到状态失败: {e}，重试({retry+1}/{Config.MAX_RETRIES})")
                if retry < Config.MAX_RETRIES - 1:
                    time.sleep(Config.RETRY_DELAY)
                    continue
                return None, None
    
    def do_sign(self, sign_param):
        """执行签到，带重试机制"""
        for retry in range(Config.MAX_RETRIES):
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
                        logger.error(f"签到请求已发送，但状态未更新，重试({retry+1}/{Config.MAX_RETRIES})")
                        if retry < Config.MAX_RETRIES - 1:
                            time.sleep(Config.RETRY_DELAY)
                            continue
                        return False
                else:
                    logger.error(f"签到请求失败，状态码: {response.status_code}，重试({retry+1}/{Config.MAX_RETRIES})")
                    if retry < Config.MAX_RETRIES - 1:
                        time.sleep(Config.RETRY_DELAY)
                        continue
                    return False
            except Exception as e:
                logger.error(f"签到过程发生错误: {e}，重试({retry+1}/{Config.MAX_RETRIES})")
                if retry < Config.MAX_RETRIES - 1:
                    time.sleep(Config.RETRY_DELAY)
                    continue
                return False
    
    def get_sign_info(self):
        """获取签到信息，带重试机制"""
        for retry in range(Config.MAX_RETRIES):
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
                    logger.error(f"未找到签到信息区域，重试({retry+1}/{Config.MAX_RETRIES})")
                    if retry < Config.MAX_RETRIES - 1:
                        time.sleep(Config.RETRY_DELAY)
                        continue
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
                logger.error(f"获取签到信息失败: {e}，重试({retry+1}/{Config.MAX_RETRIES})")
                if retry < Config.MAX_RETRIES - 1:
                    time.sleep(Config.RETRY_DELAY)
                    continue
                return {}
        
        logger.error(f"获取签到信息失败，已达到最大重试次数({Config.MAX_RETRIES})")
        return {}
    
    def run(self):
        """运行签到流程，带重试机制"""
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
                return True
            else:
                logger.error("签到失败")
                return False
        elif sign_text == "今日已打卡":
            logger.info("今日已签到，无需重复签到")
            return True
        else:
            logger.warning(f"未知的签到状态: {sign_text}，签到流程终止")
            return False

    def push_run(self):
        run_result = self.run()

        # 输出最终结果
        if run_result:
            message_arr = []
            # 获取并记录签到信息
            sign_info = sign.get_sign_info()
            if sign_info:
                logger.info("===== 签到信息 =====")
                for key, value in sign_info.items():
                    message_arr.append(f"{key}: {value}")
                    logger.info(f"{key}: {value}")
                self.push_message('飞牛签到成功', '\n'.join(message_arr))
        return run_result

    def push_message(self, title: str, content: str):
        """
        Server酱消息推送
        文档：https://sct.ftqq.com/
        """
        if not Config.PUSH_KEY:
            print('⚠️ 未配置Server酱密钥，跳过推送')
            return

        # 构建推送请求
        api_url = f'https://sctapi.ftqq.com/{Config.PUSH_KEY}.send'
        payload = {
            'title': title,
            'desp': content.replace('\n', '\n\n')  # Server酱要求空行用两个换行
        }

        try:
            resp = requests.post(api_url, data=payload)
            if resp.json().get('code') == 0:
                print('📤 推送成功')
            else:
                print(f'推送失败：{resp.text}')
        except Exception as e:
            print(f'🚨 推送异常：{str(e)}')


if __name__ == "__main__":
    try:
        # 设置更详细的日志级别，便于调试
        if os.environ.get('DEBUG') == '1':
            logger.setLevel(logging.DEBUG)
            logger.debug("调试模式已启用")

        print(Config.USERNAME)
        print(Config.PASSWORD)
        print(Config.API_KEY)
        print(Config.SECRET_KEY)
        print(Config.PUSH_KEY)
        # # 创建签到实例并运行
        sign = FNSignIn()
        result = sign.push_run()

        # 输出最终结果
        if result:
            logger.info("===== 签到脚本执行成功 =====")
        else:
            logger.error("===== 签到脚本执行失败 =====")
    except KeyboardInterrupt:
        logger.info("脚本被用户中断")
    except Exception as e:
        logger.error(f"脚本运行出错: {e}")
        # 输出详细的异常堆栈信息
        import traceback
        logger.error(traceback.format_exc())
