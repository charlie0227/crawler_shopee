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
        if not os.path.exists(path+'/log'):
            os.makedirs(path+'/log')
        logging.basicConfig(level=logging.INFO,
            format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
            datefmt='%m-%d %H:%M:%S',
            filename=path+'/log/'+filename)
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
        self.logging = Logger(self.path, datetime.datetime.now().strftime("shopee.%Y-%m.log"))
        print("Init driver done.")
    def saveCookie(self, cookieName):
        with open(self.path + '/' + cookieName, 'wb') as filehandler:
            pickle.dump(self.driver.get_cookies(), filehandler)
        self.logging.info("Save cookie to {}".format(cookieName))
    def loadCookie(self, cookieName):
        with open(self.path + '/' + cookieName, 'rb') as cookiesfile:
            for cookie in pickle.load(cookiesfile):
                self.driver.add_cookie(cookie)
    def getRequest(self, url):
        self.driver.get(url)
class Crawler(Driver):
    def __init__(self, hide = True):
        super().__init__(1200,800,hide)
    def checkPopModal(self):
        try:
            WebDriverWait(self.driver, 5).until( EC.presence_of_element_located((By.CSS_SELECTOR, ".shopee-popup__close-btn")))
            pop = self.driver.find_element_by_css_selector(".shopee-popup__close-btn")
            pop.click()
            self.logging.info("pop modal close")
        except Exception as e:
            self.logging.info("pop modal not found:"+repr(e))
            pass
    def checkLogin(self):
        try:
            element = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.CLASS_NAME, "shopee-avatar"))
            )
            self.logging.info("Login Success")
            return True
        except Exception as e:
            self.logging.info("Login Failed")
            return False
    def loginByCookie(self, cookieName):
        try:
            self.loadCookie(cookieName)
            self.driver.refresh()
            self.logging.info("Use {} to login".format(cookieName))
        except Exception as e:
            self.logging.info("{} not found".format(cookieName))
    def loginByPass(self):
        try:
            # click to show login modal
            login_button = self.driver.find_elements_by_css_selector(".navbar__link--account")[1].click()
            WebDriverWait(self.driver, 5).until( EC.presence_of_element_located((By.CSS_SELECTOR, ".shopee-modal__content")) )
        except Exception as e:
            self.logging.error("Login Modal not showing"+repr(e))
            self.close()
            sys.exit(0)
        try:
            # Enter Account & Password
            WebDriverWait(self.driver, 5).until( EC.presence_of_element_located((By.CSS_SELECTOR, ".shopee-modal__content input")))
            modal = self.driver.find_element_by_css_selector(".shopee-modal__content")
            [accountText, passwordText] = modal.find_elements_by_tag_name("input")
            submitButtom = modal.find_elements_by_tag_name("button")[4]
            accountText.send_keys(text_username)
            passwordText.send_keys(text_password)
            print(submitButtom.text)
            sleep(1)
            submitButtom.click()
            sleep(3)
            self.logging.info("Use password to login")
        except Exception as e:
            self.logging.error("Wrong account and password"+repr(e))
            self.close()
            sys.exit(0)
    def checkSMS(self):
        try:
            # Check SMS textbox exists
            modal = self.driver.find_element_by_css_selector(".shopee-modal__content")
            # Catch text & submit buttom
            smsText = modal.find_element_by_tag_name("input")
            smsSubmit = modal.find_elements_by_tag_name("button")[3]
            print(smsSubmit.text)
            text_sms = input("Please Enter SMS code in 60 seconds: ")
            smsText.clear()
            smsText.send_keys(text_sms)
            sleep(1)
            smsSubmit.click()
            sleep(3)
        except Exception as e:
            self.logging.info("No need SMS authenticate"+repr(e))
    def clickCoin(self):
        try:
            # wait for page loading
            self.getRequest("https://shopee.tw/shopee-coins-internal/?scenario=1")
            sleep(5)
            WebDriverWait(self.driver, 5).until( EC.presence_of_element_located((By.CSS_SELECTOR, ".check-box")))
            # get information
            check_box = self.driver.find_element_by_css_selector(".check-box")
            coinNow = check_box.find_element_by_css_selector(".total-coins") 
            coinGet = check_box.find_elements_by_css_selector(".capitalize")
            if len(coinGet) is 0:
                # Already click
                self.logging.info("Already archeive shopee coin today")
            else:
                #show before information
                self.logging.info("Current shopee coin：" + coinNow.text + " $，" + coinGet[0].text)
                #click to get shopee coin
                coinGet[0].click()
            #wait for already information display login-check-btni
            sleep(3)
            #show after information
            coinNow = self.driver.find_element_by_css_selector(".check-box .total-coins") 
            coinAlready = self.driver.find_element_by_css_selector(".check-box .top-btn.Regular")
            self.logging.info("Current shopee coin：" + coinNow.text + " $，" + coinAlready.text)
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
    a.clickCoin()
    a.close()
