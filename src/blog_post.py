from functools import reduce
import operator
from bs4 import BeautifulSoup, SoupStrainer


class BlogPost:
    def __init__(self, url, html, post_title_selector, post_body_selector, blacklist_selector=None, blacklist_texts=None, parse_only=None):
        self.url = url
        self.page_html = html
        print("Parsing " + url)
        self.page_soup = BeautifulSoup(self.page_html, 'lxml')  # default is 'html.parser' but it's slow
        self.title_soup = self.page_soup.select(post_title_selector)[0]
        self.post_soups = self.page_soup.select(post_body_selector)
        for post_soup in self.post_soups:
            if blacklist_selector:
                for tag in post_soup.select(blacklist_selector):
                    tag.decompose()
            if blacklist_texts:
                # TODO: Clean up this hack for Ward/Worm. Assumes we only care about <a>'s.
                for tag in post_soup.select('a[href]'):
                    if tag.text in blacklist_texts:
                        tag.decompose()

    def to_html(self):
        title = str(self.title_soup)

        for post_soup in self.post_soups:
            # TODO: Clean up this hack for Ward ch0.4. Maybe add an option for adding a custom CSS blob at the start?
            for tag in post_soup.select('.emoji'):
                tag.attrs['style'] = 'width: 1em'
        post = reduce(operator.add, map(lambda soup: str(soup), self.post_soups))
        return title + post
