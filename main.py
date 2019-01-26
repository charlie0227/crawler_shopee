import os 
import sys
import pickle 
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
class Logger:
    def __init__(self, path, filename):
        logging.basicConfig(level=logging.INFO,
            format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
            datefmt='%m-%d %H:%M:%S',
            filename=path+'/'+filename)
        if not os.path.exists(path):
            os.makedirs(path)
    def info(self, string):
        print("[INFO] "+string)
        logging.info(string)
    def error(self, string):
        print("[ERROR] "+string)
        logging.error(string)
class Driver:
    path = os.path.dirname(os.path.abspath(__file__))
    def __init__(self, width, height, hide = True):
        chrome_options = Options()
        if hide:
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--start-maximized') 
            chrome_options.add_argument('disable-infobars')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
        self.driver = webdriver.Chrome('chromedriver',options=chrome_options)
        self.driver.set_window_size(width, height)
        self.logging = Logger(self.path+'/log',datetime.datetime.now().strftime("shopee.%Y-%m.log"))
        print("Init driver done.")
    def saveCookie(self, cookieName):
        with open(self.path + '/' + cookieName, 'wb') as filehandler:
            pickle.dump(self.driver.get_cookies(), filehandler)
        self.logging.info("Save cookie to {}".format(cookieName))
    def getRequest(self, url):
        self.driver.get(url)
class Crawler(Driver):
    def __init__(self, hide = True):
        super().__init__(1200,800,hide)
        self.logging = Logger(self.path+'/log',datetime.datetime.now().strftime("shopee.%Y-%m.log"))
    def checkPopModal(self):
        try:
            pop = driver.find_element_by_css_selector(".shopee-popup__close-btn")
            pop.click()
            self.logging.info("pop modal close")
        except :
            self.logging.info("pop modal not found")
            pass
    def checkLogin(self):
        try:
            element = WebDriverWait(self.driver, 3).until(
                EC.presence_of_element_located((By.CLASS_NAME, "shopee-avatar"))
            )
            self.logging.info("Login Success")
            return True
        except Exception as e:
            self.logging.info("Login Failed")
            return False
    def loginByCookie(self, cookieName):
        try:
            with open(self.path + '/' + cookieName, 'rb') as cookiesfile:
                for cookie in pickle.load(cookiesfile):
                    self.driver.add_cookie(cookie)
            self.driver.refresh()
            self.logging.info("Use {} to login".format(cookieName))
        except Exception as e:
            self.logging.info("{} not found".format(cookieName))
    def loginByPass(self):
        try:
            # click to show login modal
            login_button = self.driver.find_elements_by_css_selector(".navbar__link--account")[1].click()
            WebDriverWait(self.driver, 3).until( EC.presence_of_element_located((By.CSS_SELECTOR, ".shopee-authen--login .input-with-status__input")) )
        except Exception as e:
            self.logging.error("Login Modal not showing"+repr(e))
            self.exit()
        try:
            # Enter Account & Password
            [accountText, passwordText] = self.driver.find_elements_by_css_selector(".shopee-authen--login .input-with-status__input")
            submitButtom = self.driver.find_elements_by_css_selector(".shopee-authen--login .btn-solid-primary")[0]
            accountText.send_keys(text_username)
            passwordText.send_keys(text_password)
            submitButtom.click()
            self.logging.info("Use password to login")
        except Exception as e:
            self.logging.error("Wrong account and password"+repr(e))
            self.close()
            sys.exit(0)
    def checkSMS(self):
        try:
            # Check SMS textbox exists
            WebDriverWait(self.driver, 3).until( EC.presence_of_element_located((By.CLASS_NAME, "shopee-authen__outline-button")))
            # Catch text & submit buttom
            smsText = self.driver.find_element_by_css_selector(".shopee-authen .input-with-status__input")
            smsSubmit = self.driver.find_element_by_css_selector(".shopee-authen .btn-solid-primary")
            
            text_sms = input("Please Enter SMS code in 60 seconds: ")
            smsText.clear()
            smsText.send_keys(text_sms)
            smsSubmit.click()
            # handle sms error  
            try:
                # wait to check if login success
                WebDriverWait(self.driver, 3).until( EC.presence_of_element_located((By.CSS_SELECTOR, ".shopee-avatar")))
            except:
                #login failed
                smsError = self.driver.find_elements_by_css_selector(".shopee-authen .shopee-authen__error")
                if len(smsError) > 0:
                    self.logging.error("Sending SMS code "+smsError[0].text)
                else:
                    self.logging.error("Sending SMS code Run time out.")
                self.close()
                sys.exit(0)
        except Exception as e:
            self.logging.info("No need SMS authenticate"+repr(e))
    def clickCoin(self):
        try:
            # wait for page loading
            WebDriverWait(self.driver, 5).until( EC.presence_of_element_located((By.CSS_SELECTOR, ".check-box")))
            # get information
            coinNow = self.driver.find_element_by_css_selector(".check-box .total-coins") 
            coinGet = self.driver.find_elements_by_css_selector(".check-box .check-in-tip")
            if len(coinGet) is 0:
                # Already click
                self.logging.info("今天已經獲取過蝦幣")
            else:
                #show before information
                self.logging.info("目前有：" + coinNow.text + " 蝦幣，" + coinGet[0].text)
                #click to get shopee coin
                coinGet[0].click()
            #wait for already information display login-check-btn
            WebDriverWait(self.driver, 3).until( EC.presence_of_element_located((By.CSS_SELECTOR, ".check-box .top-btn.Regular")))
            #show after information
            coinNow = self.driver.find_element_by_css_selector(".check-box .total-coins") 
            coinAlready = self.driver.find_element_by_css_selector(".check-box .top-btn.Regular")
            self.logging.info("目前有：" + coinNow.text + " 蝦幣，" + coinAlready.text)
        except Exception as e:
            self.logging.error(repr(e))
            self.close()
    def close(self):
        self.driver.close()
        self.logging.info("Program exit")
if __name__ == "__main__":
    a = Crawler()
    a.getRequest("https://shopee.tw")
    a.checkPopModal()
    #Use cookie to login
    a.loginByCookie(cookie_name)
    if not a.checkLogin():
        #Use pass to login
        a.loginByPass()
        a.checkSMS()
        if not a.checkLogin():
            #Login failed
            a.close()
            sys.exit(0)
    #After login, Go to coin page 
    a.saveCookie(cookie_name)
    a.getRequest("https://shopee.tw/shopee-coins-internal/?scenario=1")
    a.clickCoin()
    a.close()