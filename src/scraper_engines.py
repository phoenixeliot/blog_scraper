import urllib.request
import urllib.error
import uritools


def encode_url(url):
    parts = list(uritools.urisplit(url))
    for i in [2,3,4]:
        if parts[i]:
            parts[i] = urllib.parse.quote(parts[i])  # path
    return uritools.uriunsplit(parts)

class FetchScraper():
    def scrape(self, url, **kwargs):
        print("Scraping " + url)
        url = encode_url(url)
        try:
            # TODO: Rewrite to match the other's rewrite
            response = urllib.request.urlopen(url)
            html = response.read()
            return dict(
                html=html,
                final_url=response.url,  # TODO: test this on any site that has redirects
                response=response,
            )
        except urllib.error.HTTPError as e:
            print("Couldn't scrape URL " + url, e)
            raise e

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
        html = self.driver.page_source.encode('utf-8').strip()
        return dict(
            html=html,
            final_url=self.driver.current_url,
            # response=response,  # TODO: Figure out how to implement content-type stuff for images with Selenium below
        )
