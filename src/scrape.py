import urllib.request

class FetchScraper():
    def scrape(self, url, **kwargs):
        print("Scraping " + url)
        page = urllib.request.urlopen(url)
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


DEBUG=True

class TOCManager:
    def __init__(self, element, links, reverse_order=False, keep_original_formatting=True):
        self.keep_original_formatting = keep_original_formatting
        self.toc_element = element
        if reversed:
            links = reversed(links)
        if DEBUG:
            links = list(links)[0:4]
        self.links = list(links)
        self.toc_entries = []
        for (chapter_index, link) in enumerate(self.links):
            unique_hashid = 'chap' + str(chapter_index + 1)
            self.toc_entries.append(dict(
                unique_hashid=unique_hashid,
                link=link,
            ))

    @classmethod
    def from_html(self, html, source_url, reverse_order=False, keep_original_formatting=True):
        soup = BeautifulSoup(html, 'html.parser')
        element = soup.select(config['toc_selector'])[0]

        links = list(map(
            lambda tag: TOCLink(
                text=tag.text,
                href=tag.attrs['href'],
                source_url=source_url,
            ),
            # TODO: put is_post_link in the right place
            filter(is_post_link, element.find_all('a'))
        ))
        toc_manager = TOCManager(
            element=element,
            links=links,
            reverse_order=reverse_order,
            keep_original_formatting=keep_original_formatting
        )
        print('post_urls:', list(map(lambda l: l.href, links)))
        return toc_manager


    def to_html(self):
        if self.keep_original_formatting:
            # TODO: Replace the links in toc_element with hashid links
            return self.toc_element.prettify()
        else:
            # TODO: Get the hashid link versions (here or in TOCLink)
            link_htmls = map(lambda l: l.to_html(), self.links)
            toc_header = '<h1>Table of Contents</h1>'
            return toc_header + '<br>\n'.join(link_htmls)




from uritools import urijoin
class TOCLink:
    def __init__(self, text='', href='', source_url=''):
        self.text = text
        self.original_href = href
        self.source_url = source_url
        self.href = urijoin(source_url, href)

    def to_html(self):
        return f'<a href="{self.href}">{self.text}</a>'


from functools import reduce
import operator
class BlogPost:
    def __init__(self, url, html, post_title_selector, post_body_selector):
        self.url = url
        self.page_html = html
        self.page_soup = BeautifulSoup(self.page_html, 'html.parser')
        self.title_soup = self.page_soup.select(post_title_selector)[0]
        self.post_soups = self.page_soup.select(post_body_selector)

    def to_html(self):
        title = self.title_soup.prettify()
        post = reduce(operator.add, map(lambda soup: soup.prettify(), self.post_soups))
        return title + post



import yaml
import os
from collections import defaultdict
def read_config(filename):
    path = os.path.join(os.path.dirname(__file__), '../blog_configs', filename)
    config = defaultdict(lambda: None, yaml.load(open(path)))
    return config


## Parse command line arguments to fetch the config data
import argparse
argParser = argparse.ArgumentParser(description='Process CLI arguments')
argParser.add_argument('config_filename', metavar='config file name', type=str,
                       help="Name of the .yml config file for the blog you're scraping")
args = argParser.parse_args()
config = read_config(args.config_filename)


## Scrape and process the TOC
from bs4 import BeautifulSoup

# scrape it
if config['scraper_engine'] == 'selenium':
    scraper = SeleniumScraper()
else:
    scraper = FetchScraper()
expand_toc_js = config['toc_js']
toc_html = scraper.scrape(config['toc_url'], wait_for_selector=config['toc_selector'], js=expand_toc_js)

# specific to parsing agentyduck TOC (and maybe other blogspots?)
import re
def is_post_link(tag):
    if tag.attrs['href'] is None:
        return False
    if tag.attrs['href'].startswith('javascript:'):
        return False
    if config['post_url_pattern'] is None:  # Not filtering TOC links at all
        return True
    return re.match(config['post_url_pattern'], tag.attrs['href']) is not None

# Encapsulate the TOC links
# toc_links = list(map(lambda tag: TOCLink(text=tag.text, href=tag.attrs['href'], source_url=config['toc_url']), filter(is_post_link, toc_element.find_all('a'))))
# print('post_urls:', list(map(lambda l: l.href, toc_links)))

toc_manager = TOCManager.from_html(
    html=toc_html,
    source_url=config['toc_url'],
    reverse_order=bool(config['toc_reverse_order']),
    keep_original_formatting=bool(config['toc_keep_original_formatting']),
)


# Scrape the TOC links and encapsulate them as BlogPosts
posts = list(map(
    lambda link: BlogPost(
        url=link.href,
        html=scraper.scrape(link.href),
        post_title_selector=config['post_title_selector'],
        post_body_selector=config['post_body_selector'],
    ),
    toc_manager.links
))
print(posts)




class BookAssembler():
    def __init__(self, toc_manager, posts):
        self.toc_manager = toc_manager
        self.posts = posts

    def to_html(self):
        toc_html = self.toc_manager.to_html()
        posts_html = reduce(operator.add, map(lambda p: p.to_html(), self.posts))
        body = toc_html + posts_html
        # return body
        # TODO: Do I need this for character encoding? Calibre seems to have accounted for it fine.
        return f"""
        <html lang="en-US">
            <head>
                <meta charset="UTF-8">
            </head>
            <body>
                {body}
            </body>
        </html>
        """



from functools import reduce
import operator

## Assemble the TOC and BlogPosts into output html
book_assembler = BookAssembler(toc_manager=toc_manager, posts=posts)
book_html = book_assembler.to_html()
print(book_html)
book_file = open(os.path.join(os.path.dirname(__file__), '../output', 'book_output.html'), 'w')
book_file.write(book_html)


## Assemble the TOC object and start processing interlinks
# Start with list of TOC links
# Give each TOC link a unique hashid (#chap1, etc)
# Process each page for links they have, store them in the BlogPost I guess
# Process each page for hashids, store them in BlogPost
# Figure out which of the page links match up with TOC links
#   At some point, replace the hrefs in the page content with uniqued hashids




print('Done.')
