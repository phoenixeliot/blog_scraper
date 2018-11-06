import base64
import multiprocessing
import os
import re
import urllib.error
from collections import defaultdict

import uritools
from bs4 import BeautifulSoup

from src.read_config import read_config
from src.scraper_engines import SeleniumScraper, FetchScraper
import argparse


"""
Parse command line arguments to fetch the config data
"""
argParser = argparse.ArgumentParser(description='Process CLI arguments')
argParser.add_argument('config_filename', metavar='config file name', type=str,
                       help="Name (without path) of the .yml config file for the blog you're scraping")
args = argParser.parse_args()

config = read_config(args.config_filename)

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
    # simple case: it's already in the dict
    url = absolute_from_relative_url(url)
    if url in redirects:
        return redirects[url]

    # Try looking it up without the fragment
    defrag_url = uritools.uridefrag(url).uri
    fragment = uritools.uridefrag(url).uri
    if fragment:
        if defrag_url in redirects:
            return uritools.urijoin(redirects[defrag_url], '#'+fragment)

    # Try fixing http/https to match the TOC
    url_parts = uritools.urisplit(url)
    toc_url_parts = uritools.urisplit(redirects[config['toc_url']])
    fixed_scheme_url = uritools.uriunsplit(list(toc_url_parts)[:1] + list(url_parts)[1:])
    if fixed_scheme_url in redirects:
        return redirects[fixed_scheme_url]

    # if same domain, try scraping it
    if url_parts.host == toc_url_parts.host:
        try:
            scraper_result = scraper.scrape(url, wait_for_selector=config['post_body_selector'])
            redirects[url] = scraper_result['final_url']
            return redirects[url]  # TODO: Make store this scraped result in the book as well?
        except urllib.error.HTTPError as e:
            return url  # TODO: Could return '' or something but for now leaving it seems fine
    # else, couldn't find it, so leave it alone.

    return url

# list of URLs that have been scraped and will be included in the resulting book (always defragmented)
included_scraped_urls = set([])

def url_is_included(url):
    return uritools.uridefrag(url).uri in included_scraped_urls

def mark_url_included(url):
    included_scraped_urls.add(get_redirect(uritools.uridefrag(url).uri))

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
Helper functions for iterating over all posts or css-selections from posts
"""

def post_body_soups_iter():
    for post in posts:
        for body_soup in post['body_soups']:
            yield body_soup

def post_select_iter(selector):
    for body_soup in post_body_soups_iter():
        for element in body_soup.select(selector):
            yield (post, element)

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

# Record the scrape results in included_scraped_urls and redirects
included_scraped_urls.add(uritools.uridefrag(toc_scrape_result['final_url']).uri)
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
    scraper_results = scraper.scrape(href, wait_for_selector=config['post_body_selector'])
    return dict(
        href=href,
        html=scraper_results['html'],
        final_url=scraper_results['final_url'],
    )
with multiprocessing.Pool(min(len(toc_links), max_threads)) as thread_pool:
    scraped_toc_links = thread_pool.map(multi_scrape_html, map(lambda l: absolute_from_relative_url(l['tag']['href']), toc_links))

# Record the TOC pages into included_scraped_urls
for link in scraped_toc_links:
    mark_url_included(link['final_url'])

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
final_url_to_id = {}
for (chapter_index, link) in enumerate(scraped_toc_links):
    final_url_to_chapter_number[link['final_url']] = chapter_index + 1
    final_url_to_id[link['final_url']] = 'chap' + str(chapter_index + 1)

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
def parse_post(html):
    page_soup = BeautifulSoup(html, 'html.parser')
    title_soup = page_soup.select(config['post_title_selector'])[0]
    body_soups = page_soup.select(config['post_body_selector'])
    return dict(
        title_soup=title_soup,
        body_soups=body_soups,
    )

posts = []
for link in scraped_toc_links:
    parsed_post = parse_post(link['html'])
    parsed_post['final_url'] = link['final_url']
    posts.append(parsed_post)

"""
filter title/body/blacklisted things/etc
"""
def filter_post(post):
    for body_soup in post['body_soups']:
        if config['blacklist_selector']:
            for tag in body_soup.select(config['blacklist_selector']):
                tag.decompose()
        if config['blacklist_texts']:
            # TODO: Clean up this hack for Ward/Worm. Assumes we only care about <a>'s.
            for tag in body_soup.select('a[href]'):
                if tag.text in config['blacklist_texts']:
                    tag.decompose()

for post in posts:
    filter_post(post)

"""
Scrape pages not found in the TOC but linked by other pages (if they're on the same domain)
"""

extra_count = 0
if config['scraped_linked_local_pages']:
    for (post, element) in post_select_iter('[href]'):
        full_href = uritools.urijoin(post['final_url'], element['href'])
        defragged_href = uritools.uridefrag(full_href).uri
        subsection_id = uritools.urisplit(full_href).fragment

        if not url_is_included(defragged_href):
            href_parts = uritools.urisplit(full_href)
            toc_url_parts = uritools.urisplit(redirects[config['toc_url']])
            if href_parts.host == toc_url_parts.host:  # Never try to include linked pages from other domains
                try:
                    print("Scraping extra:")
                    scrape_result = scraper.scrape(full_href, wait_for_selector=config['post_body_selector'])
                    redirects[full_href] = scrape_result['final_url']
                    mark_url_included(full_href)

                    extra_page = parse_post(scrape_result['html'])
                    extra_page['final_url'] = scrape_result['final_url']

                    extra_count += 1
                    final_url_to_id[extra_page['final_url']] = 'extra' + str(extra_count)
                    posts.append(extra_page)
                except urllib.error.HTTPError as e:
                    pass

"""
grant ids to each post via their title element
"""
# TODO: Maybe grant differently named ids to extra linked posts?
for post in posts:
    print(post['title_soup'])
    post['title_soup']['id'] = final_url_to_id[post['final_url']]
    print(post['title_soup'])

"""
replace post subsection ids to new unique ids
"""

for (post, element) in post_select_iter('[id]'):
    chap_id = final_url_to_id[post['final_url']]
    element['id'] = chap_id + '_' + element['id']
# TODO: This doesn't create a mapping and instead just changes it in place. Could this be cleaner?

"""
replace hrefs in TOC to use new ids
"""

for link in toc_links:
    tag = link['tag']
    tag['href'] = '#' + final_url_to_id[get_redirect(tag['href'])]

"""
replace hrefs from links in posts to use new ids
"""

for (post, element) in post_select_iter('[href]'):
    full_href = uritools.urijoin(post['final_url'], element['href'])
    defragged_href = uritools.uridefrag(full_href).uri
    subsection_id = uritools.urisplit(full_href).fragment
    final_defrag_url = get_redirect(defragged_href)

    if final_defrag_url in final_url_to_id:
        chap_id = '#' + final_url_to_id[final_defrag_url]
        # TODO: Display a warning if subsection ID can't be found. We're currently assuming they line up. Should point to just the chapter if broken.
        if subsection_id:
            final_href = chap_id + '_' + subsection_id
            print(f"Replacing an internal subsection link: {post['final_url']} {final_href}")
        else:
            final_href = chap_id
            print(f"Replacing an internal chapter link: {post['final_url']} {final_href}")
        element['href'] = final_href

"""
Add icon to external links, so I know not to click them on my kindle
"""

if config['external_link_symbol']:
    for (post, element) in post_select_iter('[href]'):
        full_href = uritools.urijoin(post['final_url'], element['href'])
        final_url = get_redirect(full_href)
        if not url_is_included(final_url):
            print(f"Marking link as external: {final_url}")
            element.string += config['external_link_symbol']


if config['scrape_images']:
    """
    Scrape external images and replace their src's with base64 encoded versions
    """
    images_by_src = defaultdict(lambda: [])
    for (post, element) in post_select_iter('[src]'):
        full_src = uritools.urijoin(post['final_url'], element['src'])
        images_by_src[full_src].append(element)

    def multi_scrape_image(src):
        scraper_results = scraper.scrape(src, wait_for_selector=config['post_body_selector'])
        return dict(
            src=src,
            data=scraper_results['html'],
            response=scraper_results['response'],
        )

    # with multiprocessing.Pool(min(len(toc_links), max_threads)) as thread_pool:
    #     scraped_toc_links = thread_pool.map(
    #         multi_scrape_image,
    #         map(lambda l: absolute_from_relative_url(l['tag']['href']), toc_links)
    #     )

    scraped_images = list(map(
        multi_scrape_image,
        images_by_src.keys()
    ))

    # Record the TOC pages into included_scraped_urls
    for scraped_image in scraped_images:
        for image_tag in images_by_src[scraped_image['src']]:
            content_type = dict(scraped_image['response'].headers._headers)['Content-Type']
            base64_image = base64.b64encode(scraped_image['data']).decode('ascii')
            print(f"Inlining an image as base64: {image_tag['src']}")
            image_tag['src'] = f"data:{content_type};base64,{base64_image}"

else:
    """
    Update image src's to be full URLs
    """
    for (post, element) in post_select_iter('[src]'):
        full_src = uritools.urijoin(post['final_url'], element['src'])
        if element['src'] != full_src:
            print(f"Updating image src from {element['src']} to {full_src}")
            element['src'] = full_src

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

book_html = f"""
<html lang="en-US">
    <head>
        <meta charset="UTF-8">
    </head>
    <body>
        {book_html}
    </body>
</html>
"""

"""
Write out the file
"""

book_file = open(os.path.join(os.path.dirname(__file__), '../tmp', os.path.splitext(args.config_filename)[0] + '.html'), 'w')
book_file.write(book_html)

print("Done.")
