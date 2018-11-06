import multiprocessing
import os
import re
import urllib.error

import uritools
from bs4 import BeautifulSoup

# from src.blog_post import BlogPost
from src.book_assembler import BookAssembler
from src.read_config import read_config
from src.scraper_engines import SeleniumScraper, FetchScraper
from src.toc_manager import TOCManager
import argparse

import timeit


## Parse command line arguments to fetch the config data
argParser = argparse.ArgumentParser(description='Process CLI arguments')
argParser.add_argument('config_filename', metavar='config file name', type=str,
                       help="Name of the .yml config file for the blog you're scraping")
args = argParser.parse_args()

config = read_config(args.config_filename)


# scrape the TOC
# for each page in the TOC, scrape that link too

"""
things that need mapping for link replacement:
- partial href to full URL (accomplished using uritools.urijoin(source_url, href)
- source link's href to the post-redirect URL of the scraped page
- non-hashed URLs to #chap1 ids (or maybe to the element they'll point at?)
- hashed URLs to #chap1_subsection ids (or to the element they'll point at)
  - requires looking up [URL (without hash) -> #chap1]. Can use that to generate #chap1_subsection

when actually replacing stuff
- iterable list of elements with ids to replace
- iterable list of links with hrefs to (maybe) replace

from the element POV, what do we need to give it the correct hash id?
- chapter number (source of truth: table of contents list)
  - TOC needs to have updated URLs from following redirects
- element's original hash id

from the link POV, what do we need to give it the correct href?
- map the href to its proper full URL with uritools.urijoin(source_url, href)
- map the full href to #chap1 (and possibly #subsection) and combine those

When storing a link, what do we need to store about it?
- URL of the page it's on
- its original href
- (later) the href it *actually* ends up pointing to
  - stored after you scrape the page it linked
"""

"""
Set up the link piles
"""
# map from href to scraped page's final URL
# NOTE: Implicit in this is the notion that if we've scraped a URL, it WILL be a key in this object. TODO: Perhaps make an explicit object for that instead.
redirects = {}

def get_redirect(url):
    url = absolute_from_relative_url(url)
    if url in redirects:
        return redirects[url]
    url_parts = uritools.urisplit(url)
    toc_url_parts = uritools.urisplit(redirects[config['toc_url']])
    fixed_scheme_url = uritools.uriunsplit(list(toc_url_parts)[:1] + list(url_parts)[1:])
    if fixed_scheme_url in redirects:
        return redirects[fixed_scheme_url]
    # TODO: Or maybe we can just scrape the URL and get the definitive redirect value!
    if url_parts.host == toc_url_parts.host:
        try:
            scraper_result = scraper.scrape(url)
            redirects[url] = scraper_result['final_url']
            return redirects[url]  # TODO: Make store this scraped result in the book as well?
        except urllib.error.HTTPError as e:
            return url  # TODO: Could return '' or something but for now leaving it seems fine
    # if same domain, try scraping it
    # else, couldn't find it, so leave it alone.
    return url

# list of link tags in the TOC
# eg dict(source_url=..., href=...)
toc_links = []  # actually just overwritten later

# list of link tags in post content
# eg dict(source_url=..., href=...)
post_links = []

# list of all elements with ids
elements_with_ids = []

def absolute_from_relative_url(url):
    return uritools.urijoin(config['toc_url'], url)

"""
Set up the scraper engine
"""
if config['scraper_engine'] == 'selenium':
    scraper = SeleniumScraper()
else:
    scraper = FetchScraper()

"""
Scrape the TOC
Extract its links and put them in the Pile O' Links
"""

expand_toc_js = config['toc_js']
toc_scrape_result = scraper.scrape(config['toc_url'], wait_for_selector=config['toc_selector'], js=expand_toc_js)

redirects[config['toc_url']] = toc_scrape_result['final_url']
soup = BeautifulSoup(toc_scrape_result['html'], 'html.parser')
toc_element = soup.select(config['toc_selector'])[0]

def is_post_link(tag, post_url_pattern=None):
    if tag.attrs['href'] is None:
        return False
    if tag.attrs['href'].startswith('javascript:'):
        return False
    if post_url_pattern is None:  # Not filtering TOC links at all
        return True
    return re.match(post_url_pattern, tag.attrs['href']) is not None

toc_links = list(map(
    lambda tag: dict(
        tag=tag,
        source_url=config['toc_url'],
    ),
    filter(lambda l: is_post_link(l, config['post_url_pattern']), toc_element.select('a[href]'))
))

if config['reverse_order']:
    toc_links = reversed(toc_links)

DEBUG = False
DEBUG_POST_LIMIT = 5
if DEBUG:
    toc_links = toc_links[:DEBUG_POST_LIMIT]

"""
Give an ID to the TOC itself
"""
toc_element['id'] = 'toc'

"""
Scrape all the pages that the TOC links to (using multithreading, yay!)
"""

if config['scraper_engine'] == 'selenium':
    max_threads = 1
else:
    max_threads = 10

def multi_scrape_html(href):
    scraper_results = scraper.scrape(href)
    return dict(
        href=href,
        html=scraper_results['html'],
        final_url=scraper_results['final_url'],
    )
with multiprocessing.Pool(min(len(toc_links), max_threads)) as thread_pool:
    scraped_toc_links = thread_pool.map(multi_scrape_html, map(lambda l: absolute_from_relative_url(l['tag']['href']), toc_links))


"""
for each scraped_link, add [href -> final_url] to the pile o' redirects
"""
for link in scraped_toc_links:
    if link['href'] != link['final_url']:
        print(f"Redirected from {link['href']} to {link['final_url']}")
    redirects[link['href']] = link['final_url']

"""
map the final urls to chapter numbers
"""
final_url_to_chapter_number = {}
for (chapter_index, link) in enumerate(scraped_toc_links):
    final_url_to_chapter_number[link['final_url']] = chapter_index + 1

# TODO: Flesh this out to handle all the cases
def final_url_to_hash_id(url):
    if url == config['toc_url']:
        return toc_element['id']
    return # TODO chapter ids, subsection ids

"""
assemble the posts (with metadata)
eg dict(final_url=..., title_soup=..., body_soups=)

for each scraped link, parse its content and extract the title/body
"""
posts = []
for link in scraped_toc_links:
    page_soup = BeautifulSoup(link['html'], 'html.parser')
    title_soup = page_soup.select(config['post_title_selector'])[0]
    body_soups = page_soup.select(config['post_body_selector'])
    posts.append(dict(
        final_url=link['final_url'],
        title_soup=title_soup,
        body_soups=body_soups,
    ))

"""
filter title/body/blacklisted things/etc
"""
for post in posts:
    for body_soup in post['body_soups']:
        if config['blacklist_selector']:
            for tag in body_soup.select(config['blacklist_selector']):
                tag.decompose()
        if config['blacklist_texts']:
            # TODO: Clean up this hack for Ward/Worm. Assumes we only care about <a>'s.
            for tag in body_soup.select('a[href]'):
                if tag.text in config['blacklist_texts']:
                    tag.decompose()

"""
grant ids to each post via their title element
"""
for post in posts:
    print(post['title_soup'])
    post['title_soup']['id'] = 'chap' + str(final_url_to_chapter_number[post['final_url']])
    print(post['title_soup'])

# """
# get all the elements in posts (or TOC) with ids
# """
# toc_elements_with_ids = toc_element.select('[id]')
# title_elements = map(lambda p: p['title_soup'], posts)
# subsection_elements_with_ids = []
# for post in posts:
#     for body_soup in post['body_soups']:
#         subsection_elements_with_ids += body_soup.select('[id]')
# TODO oh wait no we need to keep the source_url associated with it to do stuff

"""
replace post subsection ids to new unique ids
"""

for post in posts:
    for body_soup in post['body_soups']:
        for element in body_soup.select('[id]'):
            chap_id = '#chap' + str(final_url_to_chapter_number[post['final_url']])
            element['id'] = chap_id + '_' + element['id']
# TODO: This doesn't create a mapping and instead just changes it in place. Could this be cleaner?

"""
replace hrefs in TOC to use new ids
"""

for link in toc_links:
    tag = link['tag']
    tag['href'] = '#chap' + str(final_url_to_chapter_number[get_redirect(tag['href'])])

"""
replace hrefs from links in posts to use new ids
"""

for post in posts:
    for body_soup in post['body_soups']:
        for element in body_soup.select('[href]'):
            full_href = uritools.urijoin(post['final_url'], element['href'])
            defragged_href = uritools.uridefrag(full_href).uri
            subsection_id = uritools.urisplit(full_href).fragment
            final_defrag_url = get_redirect(defragged_href)
            if final_defrag_url in final_url_to_chapter_number:
                chap_id = '#chap' + str(final_url_to_chapter_number[final_defrag_url])
                if subsection_id:
                    final_href = chap_id + '_' + subsection_id
                else:
                    final_href = chap_id
                element['href'] = final_href

"""
Assemble the output html
"""

book_html = ""
if config['keep_original_formatting']:
    toc_result_html = str(toc_element)
else:
    toc_result_html = '<h1 id="toc">Table of Contents</h1>' + '<br>'.join(map(lambda link: str(link['tag']), toc_links))
book_html += toc_result_html
for post in posts:
    book_html += str(post['title_soup'])
    for body_soup in post['body_soups']:
        book_html += str(body_soup)

"""
Write out the file
"""

book_file = open(os.path.join(os.path.dirname(__file__), '../tmp', 'book_output.html'), 'w')
book_file.write(book_html)

### old code below for picking out bits and pieces

exit()
## Scrape and process the TOC
# scrape it

# Encapsulate the TOC links
# toc_links = list(map(lambda tag: TOCLink(text=tag.text, href=tag.attrs['href'], source_url=config['toc_url']), filter(is_post_link, toc_element.find_all('a'))))
# print('post_urls:', list(map(lambda l: l.href, toc_links)))

toc_manager = TOCManager.from_html(
    html=toc_html,
    source_url=config['toc_url'],
    toc_selector=config['toc_selector'],
    post_url_pattern=config['post_url_pattern'],
    reverse_order=bool(config['toc_reverse_order']),
    keep_original_formatting=bool(config['toc_keep_original_formatting']),
)


# Scrape the TOC links and encapsulate them as BlogPosts




## Assemble the TOC and BlogPosts into output html
book_assembler = BookAssembler(toc_manager=toc_manager, posts=posts)
book_html = book_assembler.to_html()
book_file = open(os.path.join(os.path.dirname(__file__), '../tmp', 'book_output.html'), 'w')
book_file.write(book_html)


## Assemble the TOC object and start processing interlinks
# Start with list of TOC links
# Give each TOC link a unique hash_id (#chap1, etc)
# Process each page for links they have, store them in the BlogPost I guess
# Process each page for hash_ids, store them in BlogPost
# Figure out which of the page links match up with TOC links
#   At some point, replace the hrefs in the page content with uniqued hash_ids



elapsed = timeit.default_timer() - start_time
print('Done in %0.1f seconds' % (elapsed))
