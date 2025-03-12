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
- 验证码检测功能，当需要验证码时会提示用户手动登录
- 详细的日志记录

## 依赖安装

脚本依赖以下Python库：

```bash
pip install requests beautifulsoup4
```

## 使用方法

1. 确保已安装所需依赖
2. 修改脚本中的账号密码（如需要）
3. 运行脚本

```bash
python fnclub_signer.py
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
```

## 日志说明

脚本会在同目录下创建`logs`文件夹，并生成格式为`sign_YYYYMMDD.log`的日志文件，记录签到过程中的各种信息。

## 自动化部署

可以通过Linux的crontab设置定时任务，实现每天自动签到：

```bash
# 编辑crontab
crontab -e

# 添加以下内容，设置每天上午8:30执行签到脚本
30 8 * * * cd /path/to/script && python fnclub_signer.py
```

## 注意事项

1. 请勿频繁运行脚本，以免对网站造成不必要的压力
2. 如遇到验证码，脚本会提示需要手动登录，此时请手动登录网站一次
3. 首次运行时会创建Cookie文件，之后会优先使用Cookie登录
4. 如Cookie失效，脚本会自动尝试使用账号密码重新登录

## 免责声明

本脚本仅供学习交流使用，请勿用于任何商业用途。使用本脚本产生的任何后果由使用者自行承担。

## 更新日志

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
