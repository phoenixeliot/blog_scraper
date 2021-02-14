import time
import urllib.request
import urllib.error
import ssl
import requests
import uritools
import selenium.common.exceptions
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.common.by import By


def encode_url(url):
    parts = list(uritools.urisplit(url))
    for i in [2, 3, 4]:
        if parts[i]:
            parts[i] = urllib.parse.quote(parts[i])  # path
    return uritools.uriunsplit(parts)


class FetchScraper():
    def scrape(self, url, stream=False, **kwargs):
        # url = encode_url(url) # TODO: Figure out what needs this; it breaks WP width encoding
        print(f"Fetching with requests: {url}")
        try:
            response = requests.get(url, timeout=15, stream=stream)
            result = dict(
                final_url=response.url,  # TODO: test this on any site that has redirects
                response=response,
            )
            if not stream:
                result['html'] = response.content
            return result
        except (urllib.error.URLError, ssl.SSLError) as ex:
            print("Couldn't scrape URL " + url, ex)
            raise ex


class SeleniumScraper():
    def __init__(self, options={}):
        driver_options = webdriver.ChromeOptions()
        driver_options.headless = True

        prefs = {"profile.managed_default_content_settings.images": 2}
        driver_options.add_experimental_option("prefs", prefs)

        self.driver = webdriver.Chrome(options=driver_options)
        self.options = options

    def __del__(self):
        try:
            self.driver.quit()
        except Exception as e:
            print("Failed to quit Selenium:", e)
            pass

    def scrape(self, url, wait_for_selector=None, js=None):
        print(f"Fetching with Selenium: {url}")
        self.driver.get(url)
        # TODO: Modularize this; this is specific to Agenty Duck
        if wait_for_selector:
            try:
                WebDriverWait(self.driver, 5).until(
                    expected_conditions.presence_of_element_located((By.CSS_SELECTOR, wait_for_selector)))
            except selenium.common.exceptions.TimeoutException:
                pass
                print()
        if js:
            self.driver.execute_script(js)
            time.sleep(5)
        html = self.driver.page_source.encode('utf-8').strip()
        return dict(
            html=html,
            final_url=self.driver.current_url,
            response=None,  # Selenium basically can't scrape images, so we never need the content-type from it
        )
