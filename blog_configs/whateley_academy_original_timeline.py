import re
from bs4 import BeautifulSoup


# def rewrite_toc(toc):
#     print(toc)
# 
#     chapter_links = toc.select("a")
#     for link in chapter_links:
#         print(link.text)
#         if "Latest Chapter" in link.text:
#             link.parent.extract()
# 
#     return toc

def rewrite_post(post, config):
    for soup in post["body_soups"]:
        for element in soup.select("img[alt='linebreak shadow']"):
            element.name = "hr"
            element["alt"] = ""
            element["src"] = ""
            element["style"] = "width: 50%; margin: 0 auto;"
