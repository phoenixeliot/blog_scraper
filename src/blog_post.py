from functools import reduce
import operator
from bs4 import BeautifulSoup


class BlogPost:
    def __init__(self, url, html, post_title_selector, post_body_selector, blacklist_selector):
        self.url = url
        self.page_html = html
        self.page_soup = BeautifulSoup(self.page_html, 'html.parser')
        self.title_soup = self.page_soup.select(post_title_selector)[0]
        self.post_soups = self.page_soup.select(post_body_selector)
        for post_soup in self.post_soups:
            for tag in post_soup.select(blacklist_selector):
                tag.decompose()

    def to_html(self):
        title = self.title_soup.prettify()
        post = reduce(operator.add, map(lambda soup: soup.prettify(), self.post_soups))
        return title + post
