# FN_AQ
飞牛NAS论坛自动签到

# FN论坛自动签到脚本-FN_AQ 签到脚本

这是一个用于FN论坛(club.fnnas.com)的自动签到脚本，可以实现自动登录、检查签到状态、执行签到并记录签到信息。

## 功能特点

- 自动登录FN论坛账号
- 检测当前签到状态
- 自动执行签到操作
- 获取并记录签到信息（最近签到时间、本月签到天数、连续签到天数等）
- 保存Cookie到本地，下次运行时优先使用Cookie登录
- 验证码自动识别功能，使用百度OCR API识别验证码
- 详细的日志记录
- 完善的错误处理和重试机制

## 依赖安装

脚本依赖以下Python库：

```bash
pip install requests beautifulsoup4
```

## 使用方法

1. 确保已安装所需依赖
2. 修改脚本中的账号密码（Config类中的USERNAME和PASSWORD）
3. 配置百度OCR API的API_KEY和SECRET_KEY（如需使用验证码识别功能）
4. 运行脚本

```bash
python auto_sign.py
```

## 配置说明

脚本中的`Config`类包含了可配置的参数：

```python
class Config:
    # 账号信息
    USERNAME = 'your_username'  # 修改为你的用户名
    PASSWORD = 'your_password'  # 修改为你的密码
    
    # 网站URL
    BASE_URL = 'https://club.fnnas.com/'
    LOGIN_URL = BASE_URL + 'member.php?mod=logging&action=login'
    SIGN_URL = BASE_URL + 'plugin.php?id=zqlj_sign'
    
    # Cookie文件路径
    COOKIE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cookies.json')
    
    # 验证码识别API (百度OCR API)
    CAPTCHA_API_URL = "https://aip.baidubce.com/rest/2.0/ocr/v1/accurate_basic"
    API_KEY = "your_api_key"  # 替换为你的百度OCR API Key
    SECRET_KEY = "your_secret_key"  # 替换为你的百度OCR Secret Key
    
    # 重试设置
    MAX_RETRIES = 3  # 最大重试次数
    RETRY_DELAY = 2  # 重试间隔(秒)
    
    # Token缓存文件
    TOKEN_CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'token_cache.json')
```

### 百度OCR API配置

1. 访问[百度AI开放平台](https://ai.baidu.com/)注册账号
2. 创建文字识别应用，获取API Key和Secret Key
3. 将获取到的API Key和Secret Key填入Config类中的对应位置

## 日志说明

脚本会在同目录下创建`logs`文件夹，并生成格式为`sign_YYYYMMDD.log`的日志文件，记录签到过程中的各种信息。

可以通过设置环境变量启用调试模式：

```bash
# Windows
set DEBUG=1
python auto_sign.py

# Linux/Mac
DEBUG=1 python auto_sign.py
```

## 自动化部署

可以通过Linux的crontab设置定时任务，实现每天自动签到：

```bash
# 编辑crontab
crontab -e

# 添加以下内容，设置每天上午8:30执行签到脚本
30 8 * * * cd /path/to/script && python auto_sign.py
```

对于Windows系统，可以使用计划任务：

1. 打开任务计划程序
2. 创建基本任务
3. 设置每天运行，并指定时间
4. 选择启动程序，并设置为python脚本路径

## 注意事项

1. 请勿频繁运行脚本，以免对网站造成不必要的压力
2. 首次运行时会创建Cookie文件，之后会优先使用Cookie登录
3. 如Cookie失效，脚本会自动尝试使用账号密码重新登录
4. 验证码识别功能需要配置有效的百度OCR API密钥才能使用
5. 脚本内置了重试机制，可以自动处理临时性错误

## 免责声明

本脚本仅供学习交流使用，请勿用于任何商业用途。使用本脚本产生的任何后果由使用者自行承担。

## 更新日志

### 2023.03.15 - 重试机制与验证码识别优化
- 添加了完善的重试机制，提高脚本稳定性
- 优化了百度OCR API的集成，实现验证码自动识别
- 添加了access_token缓存功能，减少API调用次数
- 改进了错误处理和日志记录
- 添加了调试模式支持

### 登录功能优化
- 优化了登录表单的查找逻辑，支持多种表单ID格式
- 调整了登录请求参数，确保正确提交用户名和密码
- 添加了登录状态的准确检测

### 签到信息获取改进
- 优化了签到信息区域的查找方式
- 正确解析并记录签到相关信息
- 添加了详细的日志记录

### Cookie管理完善
- 实现了Cookie的保存和加载功能
- 添加了Cookie有效性检查
- 在Cookie失效时自动使用账号密码重新登录

### 错误处理增强
- 添加了验证码检测功能
- 完善了错误日志记录
- 优化了异常情况的处理流程

### 验证码识别功能
- 在Config类中添加了百度OCR API相关配置
- 实现了recognize_captcha方法，用于下载验证码图片、转换为Base64编码并调用API识别
- 添加了验证码文本清理功能，提高识别准确率
- 该方法会返回识别出的验证码文本或在失败时返回None

### 登录流程优化
- 修改了login方法，增加了验证码检测和处理逻辑
- 当检测到需要验证码时，会自动获取验证码图片URL
- 调用recognize_captcha方法识别验证码
- 将识别结果添加到登录表单数据中
- 增加了验证码错误的检测和处理

### 登录状态检测改进
- 优化了check_login_status函数，使用多种方法综合判断登录状态
- 检查登录链接是否存在
- 检查页面中是否包含用户名
- 检查是否有个人中心链接

### Cookie管理优化
- 更新了save_cookies函数，保存完整的Cookie信息，包括域名、路径、过期时间等
- 优化了load_cookies函数，使其能够处理新旧两种格式的Cookie文件，确保向后兼容性

[![Star History Chart](https://api.star-history.com/svg?repos=kggzs/FN_AQ&type=Date)](https://www.star-history.com/#kggzs/FN_AQ&Date)
