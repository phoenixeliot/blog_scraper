import re
from bs4 import BeautifulSoup


def rewrite_toc(toc):
    print(toc)

    chapter_links = toc.select('a')
    for link in chapter_links:
        print(link.text)
        if 'Latest Chapter' in link.text:
            link.parent.extract()

    return toc
