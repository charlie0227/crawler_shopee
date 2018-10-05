import pickle 
import os 
import logging
import datetime
from env import *
from time import gmtime, strftime,sleep
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium import webdriver
from selenium.webdriver.chrome.options import Options


chrome_options = Options()
chrome_options.add_argument('--headless')
chrome_options.add_argument('--disable-gpu')
chrome_options.add_argument('--no-sandbox')
path = os.path.dirname(os.path.abspath(__file__))
driver = webdriver.Chrome(path+'/chromedriver',chrome_options=chrome_options)
driver.set_window_size(1200,800)
x_login_button = "//*[@id='main']/div/div[2]/div[1]/div/div[1]/div/ul/li[5]"
x_username = "//*[@id='main']/div/div[2]/div[1]/div[2]/div/div[1]/div/div[2]/div[1]/div/div/div[1]/div[2]/div[1]/input"
x_password = "//*[@id='main']/div/div[2]/div[1]/div[2]/div/div[1]/div/div[2]/div[1]/div/div/div[1]/div[3]/div[1]/input"
x_login_submit = "//*[@id='main']/div/div[2]/div[1]/div[2]/div/div[1]/div/div[2]/div[1]/div/div/div[2]/button[2]"
x_sms_text = "//*[@id='main']/div/div[2]/div[1]/div[2]/div/div[1]/div/div[2]/div[1]/div/div/div[3]/div[1]/div/div[1]/input"
x_sms_submit = "//*[@id='main']/div/div[2]/div[1]/div[2]/div/div[1]/div/div[2]/div[1]/div/div/div[5]/button[2]"
x_earn_submit = "//*[@id='__layout']/div/section/div/div[1]/div[1]/div[3]/div[2]/div/span"
x_earn_amount = "//*[@id='__layout']/div/section/div/div[1]/div[1]/div/div/div[2]"
x_money_new = "//*[@id='__layout']/div/section/div/div[1]/div[1]/div[3]/div[2]"
x_money_total = "//*[@id='__layout']/div/section/div/div[1]/div[1]/div[2]/span[1]/span"
logging.basicConfig(level=logging.INFO,
    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
    datefmt='%m-%d %H:%M:%S',
    filename=path+'/log/'+datetime.datetime.now().strftime("shopee.%Y-%m.log"))
try:
    if not os.path.exists(path+'/log'):
        os.makedirs(path+'/log')
except:
    pass

def save_cookie(driver, path):
    with open(path, 'wb') as filehandler:
        pickle.dump(driver.get_cookies(), filehandler)

def load_cookie(driver, path):
     with open(path, 'rb') as cookiesfile:
         cookies = pickle.load(cookiesfile)
         for cookie in cookies:
             driver.add_cookie(cookie)
try :#login by cookie
    logging.info('['+strftime("%Y-%m-%d %H:%M:%S", gmtime())+']')
    logging.info("start the program")
    driver.get("https://shopee.tw")
    try:
        pop = driver.find_element_by_css_selector(".shopee-popup__close-btn")
        pop.click()
    except Exception as e :
        pass
    load_cookie(driver,path+'/'+cookie_name)
    driver.get("https://shopee.tw")
    logging.info("login success : by cookie")
except Exception as e :
    try: # type password
        element = WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((By.CLASS_NAME, "navbar__link--account"))
        )
        menu = driver.find_element_by_xpath(x_login_button)
        login_button = driver.find_element_by_xpath(x_login_button).click()
        element = WebDriverWait(driver, 3).until( EC.presence_of_element_located((By.CLASS_NAME, "input-with-status__input")) )
        # login bar
        driver.find_element_by_xpath(x_username).send_keys(text_username)
        driver.find_element_by_xpath(x_password).send_keys(text_password)
        driver.find_element_by_xpath(x_login_submit).click()
    except Exception as e :
        logging.error("type password failed")
    try:# sms authenticate
        element = WebDriverWait(driver, 3).until( EC.presence_of_element_located((By.CLASS_NAME, "shopee-authen__outline-button")))
        text_sms = input("Please Enter SMS code in 60 seconds: ")
        driver.find_element_by_xpath(x_sms_text).send_keys(text_sms)
        driver.find_element_by_xpath(x_sms_submit).click()
        logging.info("login success : by sms")
    except Exception as e :
        logging.info("login success : by password")
try:
    #after login success
    WebDriverWait(driver, 3).until( EC.presence_of_element_located((By.CLASS_NAME, "shopee-avatar")))
    save_cookie(driver,path+'/'+cookie_name)
    logging.info("save cookie success")
    driver.get("https://shopee.tw/shopee-coins-internal/?scenario=1")
    WebDriverWait(driver, 3).until( EC.presence_of_element_located((By.CLASS_NAME, "check-box")))
    sleep(3)
    driver.find_element_by_xpath(x_earn_submit).click()
    earn = driver.find_element_by_xpath(x_earn_amount)
    logging.info("You get $"+earn.text+" this time")
except Exception as e :
    logging.info(repr(e))
    logging.info("You have already click")
try:
    money = driver.find_element_by_xpath(x_money_new)
    logging.info("Info : "+money.text)
    money_total = driver.find_element_by_xpath(x_money_total)
    logging.info("Total : $"+money_total.text)
except Exception as e :
    logging.error(repr(e))
driver.quit()

