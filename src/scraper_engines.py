import time
import urllib.request
import urllib.error
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
    def scrape(self, url, **kwargs):
        url = encode_url(url)
        try:
            # TODO: Rewrite to match the other's rewrite
            request = urllib.request.Request(
                url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64)'})
            response = urllib.request.urlopen(request)
            html = response.read()
            return dict(
                html=html,
                final_url=response.url,  # TODO: test this on any site that has redirects
                response=response,
            )
        except urllib.error.HTTPError as e:
            print("Couldn't scrape URL " + url, e)
            raise e
        except urllib.error.URLError as e:
            print("Couldn't scrape URL " + url, e)
            raise e


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
            # print("Failed to quit Selenium:", e)
            pass

    def scrape(self, url, wait_for_selector=None, js=None):
        # print("Scraping " + url)
        self.driver.get(url)
        # TODO: Modularize this; this is specific to Agenty Duck
        if wait_for_selector:
            try:
                WebDriverWait(self.driver, 5).until(
                    expected_conditions.presence_of_element_located((By.CSS_SELECTOR, wait_for_selector)))
            except selenium.common.exceptions.TimeoutException as e:
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
