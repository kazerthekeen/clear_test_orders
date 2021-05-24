import json
from selenium.webdriver.common.by import By
from time import sleep
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    NoAlertPresentException,
    UnexpectedAlertPresentException,
    TimeoutException,
)
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.select import Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

ARROW_DOWN = u"\ue015"
TOKEN_ID = ""
BASE_URL = ""


class driver_manager:
    def __init__(self, config, delay=30):
        if config["browser_type"] == "Firefox":
            self.set_firefox_driver(config)
        elif config["browser_type"] == "Chrome":
            self.set_chrome_driver(config)
        else:
            self.driver = None
        self.delay = delay

    def set_chrome_driver(self, config):
        self.driver = webdriver.Chrome(executable_path=config["chrome_executable_path"])

    def set_firefox_driver(self, config):
        binary = FirefoxBinary(config["firefox_browser_bin"])
        self.driver = webdriver.Firefox(firefox_binary=binary, executable_path=config["firefox_executable_path"])

    def submit_by(self, ref, value):
        elem = self.driver.find_element(*ref)
        elem.clear()
        elem.send_keys(value)
        self.wait()

    def get_all_matching(self, xpath):
        orders = []
        try:
            elems = self.driver.find_elements_by_xpath("//tbody/tr/td[2]/a")
            for e in elems:
                orders.append(e.text)
        finally:
            return orders

    def get_text(self, ref, timeout=5):
        e = self.wait(timeout, EC.element_to_be_clickable(ref))
        return e.text

    def wait(self, timeout=-1, condition=None):
        if condition is not None:
            return WebDriverWait(self.driver, timeout).until(condition)
        else:
            if timeout < 0:
                timeout = self.delay
            self.driver.implicitly_wait(timeout)

    def click_by(self, by_Ref, timeout=5):
        elem = self.wait(timeout, EC.element_to_be_clickable(by_Ref))
        elem.click()
        self.wait()

    def select_value_by(self, ref, value, tries=0):
        try:
            elem = self.driver.find_element(*ref)
            for option in elem.find_elements_by_tag_name("option"):
                if option.text == value:
                    break
                else:
                    elem.send_keys(Keys.UP)
        except StaleElementReferenceException as e:
            if tries > 3:
                raise e
            self.sleep(1)
            self.select_value_by_id(ref, value, tries + 1)

    def get(self, value, timeout=5):
        self.driver.get(value)
        sleep(1)
        try:
            alert = self.driver.switch_to_alert()
            alert.accept()
        except NoAlertPresentException:
            pass
        finally:
            self.wait(timeout, EC.url_contains(value))

    def value_in_source(self, value):
        return value in self.driver.page_source

    def get_route(self):
        return self.driver.current_url

    def sleep(self, t):
        sleep(t)

    def quit(self):
        self.driver.quit()

    def scroll_bottom(self):
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

    def maximize(self):
        self.driver.maximize_window()

    def confirm_alert(self, func, *args, **kwargs):
        try:
            func(*args)
        except UnexpectedAlertPresentException:
            self.wait(8, EC.alert_is_present())
            alert = self.driver.switch_to_alert()
            alert.accept()
            dm.sleep(1)
            if kwargs.get("retry", True):
                func(*args)

    def get_cookies(self):
        return self.driver.get_cookies()


def load_settings(file_name="/home/kazer/Programs/clear-test-orders/config.json"):
    with open(file_name, "r") as file:
        s = file.read()
    settings = json.loads(s)
    return settings


def parse_tokenID(url):
    vars = url.split("?", 1)[-1]  # Get the args portion of the url
    args = vars.split("&")  # Split into individual args
    for a in args:
        # if args has "token" in the name get the value of it.
        if "token" in a:
            token = a.split("=")[-1]
            return token


def get_credentials(dm, config):
    global TOKEN_ID
    dm.get(BASE_URL)
    dm.submit_by((By.ID, "input-username"), config["username"])
    dm.submit_by((By.ID, "input-password"), config["password"])
    dm.click_by((By.XPATH, "//button"))
    dm.sleep(5)
    url = dm.get_route()
    TOKEN_ID = parse_tokenID(url)


def pull_next_order(dm):
    url = "{}?route=sale/order&token={}&filter_order_status=2&filter_total=0.0&filter_customer=test".format(
        BASE_URL, TOKEN_ID
    )
    dm.get(url)

    # This will pull "" if the order has a return.
    order = dm.get_text((By.XPATH, "//tbody/tr/td[2]/a"))
    if order == "":
        order = dm.get_text((By.XPATH, "//tbody/tr/td[2]/a[2]"))

    # This raises a ValueException if order is not a number
    int(order)
    return order


def cancel_order(dm, order):
    url = "{base}?route=sale/order/edit&token={id}&order_id={order}#tab-history".format(
        base=BASE_URL, id=TOKEN_ID, order=order
    )
    dm.get(url)
    dm.select_value_by((By.ID, "input-order-status"), "cancel")
    dm.submit_by((By.ID, "input-comment"), config["comment"])
    dm.click_by((By.ID, "button-history"))
    print("Order Canceled:", order)
    dm.sleep(5)


def clear_test_orders(dm, config):
    while True:
        try:
            order = pull_next_order(dm)
            cancel_order(dm, order)
        except TimeoutException:
            print("No orders remaining.")
            return


if __name__ == "__main__":
    config = load_settings()
    BASE_URL = config["base_url"]
    dm = driver_manager(config)
    get_credentials(dm, config)
    clear_test_orders(dm, config)
    dm.quit()
