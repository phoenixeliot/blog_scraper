import urllib.request

class FetchScraper():
    def scrape(self, url, **kwargs):
        print("Scraping " + url)
        page = urllib.request.urlopen(url).read()
        return page

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.common.by import By
import time
# TODO: Make a class to encapsulate this scraper, which can reuse the same selenium driver instance and quit after everything is done
class SeleniumScraper():
    def __init__(self, options={}):
        self.driver = webdriver.Chrome()
        self.options = options

    def __del__(self):
        self.driver.quit()

    def scrape(self, url, wait_for_selector=None, js=None):
        print("Scraping " + url)
        self.driver.get(url)
        # TODO: Modularize this; this is specific to Agenty Duck
        if wait_for_selector:
            WebDriverWait(self.driver, 5).until(expected_conditions.presence_of_element_located((By.CSS_SELECTOR, wait_for_selector)))
        if js:
            self.driver.execute_script(js)
        time.sleep(1)
        page = self.driver.page_source.encode('utf-8').strip()
        return page
