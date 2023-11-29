import socket
import time
import traceback
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
import urllib3


def encode_url(url):
    parts = list(uritools.urisplit(url))
    for i in [2, 3, 4]:
        if parts[i]:
            parts[i] = urllib.parse.quote(parts[i])  # path
    return uritools.uriunsplit(parts)


class FetchScraper:
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
                result["html"] = response.content
            return result
        except Exception as ex:
            print("Couldn't scrape URL " + url)
            traceback.print_exc()
            raise ex


class SeleniumScraper:
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
            print("Failed to quit Selenium:")
            traceback.print_exc()

    def scrape(self, url, wait_for_selector=None, js=None):
        print(f"Fetching with Selenium: {url}")
        max_attempts = 100
        attempt = 0
        while attempt < max_attempts:
            try:
                attempt += 1
                self.driver.get(url)
                if ("The requested page can't be found." in self.driver.page_source.strip()):
                    return dict(
                        html='',
                        final_url=self.driver.current_url,
                        response=None
                    )
                # TODO: Modularize this; this is specific to Agenty Duck
                if wait_for_selector:
                    try:
                        WebDriverWait(self.driver, 30).until(
                            expected_conditions.presence_of_element_located(
                                (By.CSS_SELECTOR, wait_for_selector)
                            )
                        )
                    except selenium.common.exceptions.TimeoutException as e:
                        print(
                            f"WARNING: TimeoutException while trying to load URL: {url}. Selector was never found: {wait_for_selector}"
                        )
                        raise e
                if js:
                    self.driver.execute_script(js)
                    time.sleep(5)
                html = self.driver.page_source.encode("utf-8").strip()
                return dict(
                    html=html,
                    final_url=self.driver.current_url,
                    response=None,  # Selenium basically can't scrape images, so we never need the content-type from it
                )
            except Exception as e:
                if (attempt < max_attempts):
                    print(f"Exception while scraping, attempt #{attempt}")
                    traceback.print_exc()
                    time.sleep(attempt)
                else:
                    print("Exception while scraping, final attempt: ", e)
                    raise e
                
