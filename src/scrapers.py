import urllib.request
import urllib.error

class FetchScraper():
    def scrape(self, url, **kwargs):
        print("Scraping " + url)
        try:
            page = urllib.request.urlopen(url).read()
            return page
        except urllib.error.HTTPError as e:
            print("Couldn't fetch URL " + url, e)
            exit()

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.common.by import By
import time
# TODO: Make a class to encapsulate this scraper, which can reuse the same selenium driver instance and quit after everything is done
class SeleniumScraper():
    def __init__(self, options={}):
        driver_options = webdriver.ChromeOptions()
        driver_options.headless = True
        self.driver = webdriver.Chrome(options=driver_options)
        self.options = options

    def __del__(self):
        try:
            self.driver.quit()
        except Exception as e:
            # print("Failed to quit Selenium:", e)
            pass

    def scrape(self, url, wait_for_selector=None, js=None):
        print("Scraping " + url)
        self.driver.get(url)
        # TODO: Modularize this; this is specific to Agenty Duck
        if wait_for_selector:
            WebDriverWait(self.driver, 5).until(expected_conditions.presence_of_element_located((By.CSS_SELECTOR, wait_for_selector)))
        if js:
            self.driver.execute_script(js)
        page = self.driver.page_source.encode('utf-8').strip()
        return page
