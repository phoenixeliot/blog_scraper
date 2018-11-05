import re
from bs4 import BeautifulSoup
from src.links import TOCHashedLink, TOCLink

def is_post_link(tag, post_url_pattern=None):
    if tag.attrs['href'] is None:
        return False
    if tag.attrs['href'].startswith('javascript:'):
        return False
    if post_url_pattern is None:  # Not filtering TOC links at all
        return True
    return re.match(post_url_pattern, tag.attrs['href']) is not None

DEBUG=False

class TOCManager:
    def __init__(self, element, links, reverse_order=False, keep_original_formatting=True):
        self.keep_original_formatting = keep_original_formatting
        self.toc_element = element
        if reverse_order:
            links = reversed(links)
        self.links = list(links)
        if DEBUG:
            self.links = self.links[0:5]
        self.toc_entries = []
        self.url_link_map = {}
        for (chapter_index, link) in enumerate(self.links):
            unique_hash_id = 'chap' + str(chapter_index + 1)
            hashed_link = TOCHashedLink(link=link, hash_id=unique_hash_id)
            self.toc_entries.append(hashed_link)
            self.url_link_map[link.href] = hashed_link

    # TODO: Is this the right place to abstract this to? Or should parsing be separate from management?
    @classmethod
    def from_html(self, html, source_url, toc_selector=None, post_url_pattern=None, reverse_order=False, keep_original_formatting=True):
        soup = BeautifulSoup(html, 'html.parser')
        element = soup.select(toc_selector)[0]

        links = list(map(
            lambda tag: TOCLink(
                text=tag.text,
                href=tag.attrs['href'],
                source_url=source_url,
            ),
            # TODO: put is_post_link in the right place
            filter(lambda l: is_post_link(l, post_url_pattern), element.select('a[href]'))
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
            # TODO: Replace the links in toc_element with hash_id links
            for tag in self.toc_element.select('a[href]'):
                if tag.attrs['href'] not in self.url_link_map:
                    print("Couldn't localize original TOC link:", tag.attrs['href'])
                    continue
                link = self.url_link_map[tag.attrs['href']]
                tag.attrs['href'] = '#' + link.hash_id  # TODO: code smell, assembling link stuff outside of links
            return str(self.toc_element)
        else:
            link_htmls = map(lambda l: l.to_html(), self.toc_entries)
            toc_header = '<h1>Table of Contents</h1>'
            return toc_header + '<br>\n'.join(link_htmls)
