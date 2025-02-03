import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
import requests
import time
import random
import datetime
import ntplib
import json
import smtplib
from email.mime.text import MIMEText

# 读取配置
with open("config.json", "r", encoding="utf-8") as f:
    CONFIG = json.load(f)

# NTP 服务器同步时间
def get_ntp_time():
    try:
        client = ntplib.NTPClient()
        response = client.request('pool.ntp.org', version=3)
        return datetime.datetime.fromtimestamp(response.tx_time)
    except:
        return datetime.datetime.now()

# 备用：淘宝 API 获取时间
def get_taobao_time():
    try:
        response = requests.get("http://api.m.taobao.com/rest/api3.do?api=mtop.common.getTimestamp", timeout=5)
        timestamp = int(response.json()["data"]["t"]) / 1000
        return datetime.datetime.fromtimestamp(timestamp)
    except:
        return datetime.datetime.now()

# 时间校准
def calibrate_time():
    ntp_time = get_ntp_time()
    taobao_time = get_taobao_time()
    local_time = datetime.datetime.now()
    diff = (max(ntp_time, taobao_time) - local_time).total_seconds()
    print(f"时间误差校准：{diff:.3f} 秒")
    return diff

# 反检测浏览器设置
def get_chrome_driver():
    options = Options()
    options.add_argument(f"user-agent={random.choice(CONFIG['user_agents'])}")  
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-popup-blocking")
    
    # 代理支持
    if CONFIG["proxy"]:
        proxy = random.choice(CONFIG["proxy"])
        options.add_argument(f"--proxy-server={proxy}")

    # 无头模式
    if CONFIG["headless"]:
        options.add_argument("--headless")

    driver = uc.Chrome(options=options)
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })
    return driver

# 动态查找按钮
def find_buy_button(driver):
    selectors = ["btn-buy", "btn-reserve", "J-addCart"]
    for selector in selectors:
        try:
            button = driver.find_element(By.CLASS_NAME, selector)
            if button.is_displayed():
                return button
        except:
            continue
    return None

# 模拟点击
def human_like_click(driver, element):
    ActionChains(driver).move_to_element(element).pause(random.uniform(0.1, 0.3)).click().perform()

# 发送通知
def send_notification(message):
    if CONFIG["email"]["enable"]:
        send_email(message)
    if CONFIG["wechat"]["enable"]:
        send_wechat(message)

# 发送邮件
def send_email(message):
    try:
        msg = MIMEText(message, "plain", "utf-8")
        msg["Subject"] = "京东抢购通知"
        msg["From"] = CONFIG["email"]["sender"]
        msg["To"] = CONFIG["email"]["receiver"]

        server = smtplib.SMTP_SSL(CONFIG["email"]["smtp_server"], CONFIG["email"]["port"])
        server.login(CONFIG["email"]["sender"], CONFIG["email"]["password"])
        server.sendmail(CONFIG["email"]["sender"], [CONFIG["email"]["receiver"]], msg.as_string())
        server.quit()
    except Exception as e:
        print("邮件发送失败:", e)

# 发送微信通知
def send_wechat(message):
    try:
        url = f"https://sc.ftqq.com/{CONFIG['wechat']['key']}.send?text={message}"
        requests.get(url)
    except Exception as e:
        print("微信通知发送失败:", e)

# 进入商品页面
def open_product_page(driver, url):
    driver.get(url)
    print("已打开商品页面")
    time.sleep(random.uniform(1, 3))

# 登录
def login(driver):
    driver.get("https://passport.jd.com/new/login.aspx")
    print("请手动扫码登录...")
    time.sleep(15)
    while True:
        time.sleep(30)
        driver.get("https://order.jd.com/center/list.action")  # 保持会话

# 抢购逻辑
def buy(driver):
    attempts = 0
    retry_limit = CONFIG["retry_limit"]

    while attempts < retry_limit:
        attempts += 1
        try:
            driver.refresh()
            print(f"第 {attempts} 次尝试抢购...")
            time.sleep(random.uniform(0.2, 0.5))

            buy_button = find_buy_button(driver)
            if buy_button:
                human_like_click(driver, buy_button)
                time.sleep(random.uniform(1, 2))

                submit_button = driver.find_element(By.CLASS_NAME, "checkout-submit")
                if submit_button:
                    human_like_click(driver, submit_button)
                    send_notification("抢购成功！请尽快支付订单")
                    break
        except Exception as e:
            print("抢购失败，重试中...", e)
            time.sleep(random.uniform(0.5, 1))

# 主函数
if __name__ == "__main__":
    driver = get_chrome_driver()
    time_offset = calibrate_time()
    login(driver)
    open_product_page(driver, CONFIG["product_url"])
    buy(driver)
