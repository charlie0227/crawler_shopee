import unittest
from main import *
class TestStringMethods(unittest.TestCase):
    def setUp(self):
        self.a = Crawler()
        self.a.getRequest("https://shopee.tw")
    def tearDown(self):
        self.a.close()
    def test_login_button(self):
        WebDriverWait(self.a.driver, 3).until( EC.presence_of_element_located((By.CSS_SELECTOR, ".navbar__link--account")) )
        result = self.a.driver.find_elements_by_css_selector(".navbar__link--account")
        self.assertEqual(len(result), 2)
    def test_login_textbox(self):
        WebDriverWait(self.a.driver, 3).until( EC.presence_of_element_located((By.CSS_SELECTOR, ".navbar__link--account")) )
        self.a.driver.find_elements_by_css_selector(".navbar__link--account")[1].click()
        WebDriverWait(self.a.driver, 3).until( EC.presence_of_element_located((By.CLASS_NAME, "input-with-status__input")) )
        result = self.a.driver.find_elements_by_css_selector(".shopee-authen--login .input-with-status__input")
        buttom = self.a.driver.find_elements_by_css_selector(".shopee-authen--login .btn-solid-primary")
        self.assertEqual(len(result), 2)
        self.assertEqual(len(buttom), 1)
    def test_sms_textbox(self):
        self.a.loginByPass()
        WebDriverWait(self.a.driver, 3).until( EC.presence_of_element_located((By.CLASS_NAME, "shopee-authen__outline-button")))
        smsText = self.a.driver.find_elements_by_css_selector(".shopee-authen .input-with-status__input")
        smsSubmit = self.a.driver.find_elements_by_css_selector(".shopee-authen .btn-solid-primary")
        self.assertEqual(len(smsText), 1)
        self.assertEqual(len(smsSubmit), 1)
    def test_login(self):
        self.a.checkPopModal()
        #Use cookie to login
        self.a.loginByCookie(cookie_name)
        if not self.a.checkLogin():
            #Use pass to login
            self.a.loginByPass()
            self.a.checkSMS()
            if not self.a.checkLogin():
                #Login failed
                self.a.exit()
    def test_getCoin(self):
        self.a.checkPopModal()
        #Use cookie to login
        self.a.loginByCookie(cookie_name)
        if not self.a.checkLogin():
            #Use pass to login
            self.a.loginByPass()
            self.a.checkSMS()
            if not self.a.checkLogin():
                #Login failed
                self.a.close()
                sys.exit(0)
        #After login, Go to coin page 
        self.a.saveCookie(cookie_name)
        self.clickCoin()
if __name__ == '__main__':
    unittest.main()