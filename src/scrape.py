"""
This does the majority of the scraping work.
It's a bit monolithic atm; splitting it up more will be good.

Run it like so:
python src/scrape.py worm.yml --format=epub,mobi
"""
import base64
import multiprocessing
import shutil
import sys
import os
import re
import urllib.error
import ssl
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse

import uritools
from bs4 import BeautifulSoup

# Hack to fix relative imports, per https://stackoverflow.com/a/16985066/8869677
PACKAGE_PARENT = '..'
SCRIPT_DIR = os.path.dirname(os.path.realpath(os.path.join(os.getcwd(), os.path.expanduser(__file__))))
sys.path.append(os.path.normpath(os.path.join(SCRIPT_DIR, PACKAGE_PARENT)))

from src.convert_ebook import convert_ebook
from src.read_config import read_config
from src.scraper_engines import SeleniumScraper, FetchScraper
import argparse

DEBUG = False
DEBUG_POST_LIMIT = 15

"""
Parse command line arguments to fetch the config data
"""
argParser = argparse.ArgumentParser(description='Process CLI arguments')
argParser.add_argument('config_filename', metavar='config', type=str,
                       help="Name (without path) of the .yml config file for the blog you're scraping")
argParser.add_argument('-f', '--format', metavar="format", type=str,
                       help="output format (eg, epub or mobi; anything calibre's ebook-convert supports)")
args = argParser.parse_known_args()[0]

config = read_config(args.config_filename)

if config['disabled']:
    print(f"{args.config_filename} is disabled. Skipping.")
    sys.exit(os.EX_OK)

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

image_folder = args.config_filename.replace('.yml', '')

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
    base_url_parts = uritools.urisplit(redirects[base_url])
    fixed_scheme_url = uritools.uriunsplit(
        list(base_url_parts)[:1] + list(url_parts)[1:])
    if fixed_scheme_url in redirects:
        return redirects[fixed_scheme_url]

    # if same domain, try scraping it
    if url_parts.host == base_url_parts.host:
        try:
            print(f"Scraping url for get_redirect: {url}")
            scraper_result = scraper.scrape(
                url, wait_for_selector=config['post_body_selector'])
            redirects[url] = scraper_result['final_url']
            # TODO: Make store this scraped result in the book as well?
            return redirects[url]
        except (urllib.error.URLError, ssl.SSLError):
            return url  # TODO: Could return '' or something but for now leaving it seems fine
    # else, couldn't find it, so leave it alone.

    return url


# list of URLs that have been scraped and will be included in the resulting book (always defragmented)
included_scraped_urls = set([])


def url_is_included(url):
    return uritools.uridefrag(url).uri in included_scraped_urls


def mark_url_included(url):
    included_scraped_urls.add(uritools.uridefrag(url).uri)


# list of link tags in the TOC
# eg dict(source_url=..., href=...)
toc_links = []  # actually just overwritten later

# list of link tags in post content
# eg dict(source_url=..., href=...)
post_links = []

# list of all elements with ids
elements_with_ids = []


def absolute_from_relative_url(url):
    return uritools.urijoin(base_url, url)


def parse_post(html):
    page_soup = BeautifulSoup(html, 'html.parser')
    title_soup = page_soup.select(config['post_title_selector'])[0]
    body_soups = page_soup.select(config['post_body_selector'])
    return dict(
        page_soup=page_soup,
        title_soup=title_soup,
        body_soups=body_soups,
    )


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

def multi_scrape_html(href):
    try:
        print(f"Scraping post: {href}")
        scraper_results = scraper.scrape(
            href, wait_for_selector=config['post_body_selector'])
        return dict(
            href=href,
            html=scraper_results['html'],
            final_url=scraper_results['final_url'],
        )
    # TODO: Do something analogous for Selenium. Probably in several places.
    except (urllib.error.URLError, ssl.SSLError):
        return None

def remove_blacklisted_selectors(body_soup):
    if config['blacklist_selector']:
        for tag in body_soup.select(config['blacklist_selector']):
            print(f"Removing blacklisted item by selector ({config['blacklist_selector']}): \"{tag.text.strip()}\"")
            tag.decompose()

"""
Set up the scraper engine
"""
if config['scraper_engine'] == 'selenium':
    scraper = SeleniumScraper()
    image_scraper = FetchScraper()  # Selenium fails on a bunch of images
    max_threads = 1
else:
    scraper = FetchScraper()
    image_scraper = FetchScraper()
    # max_threads = 10
    max_threads = 1


if config['crawl_mode'] == 'toc':
    base_url = config['toc_url']
    """
    Scrape the TOC
    Extract its links and put them in the Pile O' Links
    """

    expand_toc_js = config['toc_js']
    print(f"Scraping table of contents: {config['toc_url']}")
    toc_scrape_result = scraper.scrape(
        config['toc_url'], wait_for_selector=config['toc_selector'], js=expand_toc_js)

    # Record the scrape results in included_scraped_urls and redirects
    mark_url_included(toc_scrape_result['final_url'])
    redirects[config['toc_url']] = toc_scrape_result['final_url']

    soup = BeautifulSoup(toc_scrape_result['html'], 'html.parser')
    toc_element = soup.select(config['toc_selector'])[0]

    remove_blacklisted_selectors(toc_element)

    if config['rewrite_toc']:
        toc_element = config['rewrite_toc'](toc_element)

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
        filter(lambda l: is_post_link(
            l, config['post_url_pattern']), toc_element.select('a[href]'))
    ))

    if config['toc_reverse_order']:
        toc_links = list(reversed(toc_links))

    if DEBUG:
        toc_links = toc_links[:DEBUG_POST_LIMIT]

    """
    Give an ID to the TOC itself
    """
    toc_element['id'] = 'toc'

    """
    Scrape all the pages that the TOC links to (using multithreading, yay!)
    """


    with multiprocessing.Pool(max(1, min(len(toc_links), max_threads))) as thread_pool:
        scraped_toc_links = list(filter(
            lambda x: x is not None,
            thread_pool.map(multi_scrape_html, map(
                lambda l: absolute_from_relative_url(l['tag']['href']), toc_links))
        ))

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
    final_url_to_id = {}
    for (chapter_index, link) in enumerate(scraped_toc_links):
        final_url_to_id[link['final_url']] = 'chap' + str(chapter_index + 1)

    # TODO: Flesh this out to handle all the cases
    # def final_url_to_hash_id(url):
    #     if url == config['toc_url']:
    #         return toc_element['id']
    #     return # TODO chapter ids, subsection ids

    """
    assemble the posts (with metadata)
    eg dict(final_url=..., title_soup=..., body_soups=)
    
    for each scraped link, parse its content and extract the title/body
    """
    posts = []
    for link in scraped_toc_links:
        try:
            print(f"Parsing post: {link['final_url']}")
            parsed_post = parse_post(link['html'])
            parsed_post['final_url'] = link['final_url']
            posts.append(parsed_post)
        except Exception as e:
            print("Error scraping link:", link['final_url'])
            print(e)
            pass
        # TODO: Maybe catch exception for trying to read off-site pages
        #   Also why is it scraping off-site pages anyway?

elif config['crawl_mode'] == 'nested_archive':
    base_url = config['toc_url']
    """
    Scrape the TOC
    Extract its links and put them in the Pile O' Links
    """

    expand_toc_js = config['toc_js']
    print(f"Scraping archive chunks: {config['toc_url']}")
    toc_scrape_result = scraper.scrape(
        config['toc_url'], wait_for_selector=config['toc_selector'], js=expand_toc_js)

    # Record the scrape results in included_scraped_urls and redirects
    mark_url_included(toc_scrape_result['final_url'])
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
        filter(lambda l: is_post_link(
            l, config['post_url_pattern']), toc_element.select('a[href]'))
    ))

    if config['reverse_order']:
        toc_links = reversed(toc_links)

    if DEBUG:
        toc_links = toc_links[:DEBUG_POST_LIMIT]

    """
    Give an ID to the TOC itself
    """
    toc_element['id'] = 'toc'

    """
    Scrape all the pages that the TOC links to (using multithreading, yay!)
    """
    with multiprocessing.Pool(max(1, min(len(toc_links), max_threads))) as thread_pool:
        scraped_toc_links = list(filter(
            lambda x: x is not None,
            thread_pool.map(multi_scrape_html, map(
                lambda l: absolute_from_relative_url(l['tag']['href']), toc_links))
        ))

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
    final_url_to_id = {}
    for (chapter_index, link) in enumerate(scraped_toc_links):
        final_url_to_id[link['final_url']] = 'chap' + str(chapter_index + 1)

    # TODO: Flesh this out to handle all the cases
    # def final_url_to_hash_id(url):
    #     if url == config['toc_url']:
    #         return toc_element['id']
    #     return # TODO chapter ids, subsection ids

    """
    assemble the posts (with metadata)
    eg dict(final_url=..., title_soup=..., body_soups=)

    for each scraped link, parse its content and extract the title/body
    """
    posts = []
    for link in scraped_toc_links:
        print(f"Parsing post: {link['final_url']}")
        parsed_post = parse_post(link['html'])
        parsed_post['final_url'] = link['final_url']
        posts.append(parsed_post)


elif config['crawl_mode'] == 'incremental':
    # base_url is used for joining relative urls and comparisons in many places
    base_url = config['first_post_url']
    posts = []
    next_post_url = config['first_post_url']

    """
    Scrape and process a post before continuing on to the next one, in a loop
    """
    while next_post_url:
        if DEBUG and len(posts) > DEBUG_POST_LIMIT:
            break
        """
        Scrape the post
        """
        post_url = next_post_url
        next_post_url = None
        print(f"Scraping post: {post_url}")
        scrape_result = scraper.scrape(
            post_url, wait_for_selector=config['post_selector'], js=config['post_js'])

        # Record the scrape results in included_scraped_urls and redirects
        mark_url_included(scrape_result['final_url'])
        redirects[post_url] = scrape_result['final_url']

        """
        Parse the post and save it to the list
        """
        post = parse_post(scrape_result['html'])
        if config['rewrite_post']:
            config['rewrite_post'](post, config)
        post['final_url'] = scrape_result['final_url']

        posts.append(post)

        """
        Find the link to the next post for the next iteration
        NOTE: Depends on this happening *before* filter_post (so the link is still there)
        """
        if config['next_link_selector']:
            link_selection = post['page_soup'].select(config['next_link_selector'])
            if len(link_selection) == 0:
                next_post_url = None
                break
            link_tag = link_selection[0]
            next_post_url = absolute_from_relative_url(link_tag['href'])
        else:
            link_tags = post['body_soups'][0].select('a')
            for link_tag in link_tags:
                if 'Next' in link_tag.text:
                    next_post_url = absolute_from_relative_url(link_tag['href'])
                    break

    """
    map the final urls to chapter numbers
    """
    # TODO: DRY this out with the similar code for toc-mode
    final_url_to_id = {}
    for (chapter_index, post) in enumerate(posts):
        final_url_to_id[post['final_url']] = 'chap' + str(chapter_index + 1)

else:
    raise Exception("Crawl mode must be either 'toc' or 'incremental'")

"""
filter title/body/blacklisted things/etc
"""


def filter_post(post):
    for body_soup in post['body_soups']:
        remove_blacklisted_selectors(body_soup)
        if config['blacklist_texts']:
            # TODO: Clean up this hack for Ward/Worm. Assumes we only care about <a>'s.
            for tag in body_soup.find_all():
                if tag.text.strip() in config['blacklist_texts']:
                    print(f"Removing blacklisted text: \"{tag.text.strip()}\"")
                    parent = tag.parent
                    tag.decompose()
                    while parent.text.strip() == '':
                        current = parent
                        parent = current.parent
                        current.decompose()


for post in posts:
    print(f"Filtering post: {post['final_url']}")
    filter_post(post)

"""
If a custom rewrite_post is provided, run it now
"""
if config['rewrite_post']: # TODO: Try to make this not run twice? Though running it twice might be necessary for some current hacks...
    for post in posts:
        print(f"Running config.rewrite_post: {post['final_url']}")
        config['rewrite_post'](post, config)

"""
Scrape pages not found in the TOC but linked by other pages (if they're on the same domain)
"""

if config['scraped_linked_local_pages']:
    def find_linked_extras(posts):
        extra_page_urls = []
        for post in posts:
            for body_soup in post['body_soups']:
                for element in body_soup.select('[href]'):
                    full_href = uritools.urijoin(
                        post['final_url'], element['href'])
                    defragged_href = uritools.uridefrag(full_href).uri

                    if not url_is_included(defragged_href):
                        href_parts = uritools.urisplit(full_href)
                        base_url_parts = uritools.urisplit(redirects[base_url])
                        if href_parts.host == base_url_parts.host:  # Never try to include linked pages from other domains
                            if defragged_href not in extra_page_urls:
                                # TODO: defragged, or full? Uniqueness or is the fragment important?
                                extra_page_urls.append(defragged_href)
        return extra_page_urls

    extra_page_urls = find_linked_extras(posts)
    extra_pages = []
    extra_count = 1
    while len(extra_page_urls) > 0:
        print("Scraping a batch of extras:")
        print('\n'.join(extra_page_urls))
        with multiprocessing.Pool(max(1, min(len(posts), max_threads))) as thread_pool:
            scraped_extra_pages = list(filter(
                lambda x: x is not None, thread_pool.map(multi_scrape_html, extra_page_urls)))

        extra_pages = []
        # extra_pages = list(map(lambda scraped: parse_post(scraped['html']), scraped_extra_pages))
        for scrape_result in scraped_extra_pages:
            try:
                extra_page = parse_post(scrape_result['html'])
                # TODO: Encapsulate all the stuff we do with new pages into one function (it's copied above as well for non-extras)
                filter_post(extra_page)
                if config['rewrite_post']:
                    config['rewrite_post'](extra_page, config)
                extra_page['final_url'] = scrape_result['final_url']
                extra_pages.append(extra_page)

                redirects[scrape_result['href']] = scrape_result['final_url']
                mark_url_included(scrape_result['final_url'])
                # TODO: Fragment might matter here (see above TODO)
                final_url_to_id[scrape_result['final_url']
                                ] = 'extra' + str(extra_count)
                extra_count += 1
            except Exception as e:
                # TODO: Handle if a page links to an image for some reason (Meaningness does this somewhere)
                print("Error scraping and formatting extra page")
                print(e)
                pass

        posts += extra_pages  # TODO: Consider cleanup by keeping these separate
        extra_page_urls = find_linked_extras(extra_pages)

"""
grant ids to each post via their title element
"""
for post in posts:
    print(
        f"Adding id to chapter: {post['final_url']} id={final_url_to_id[post['final_url']]}")
    post['title_soup']['id'] = final_url_to_id[post['final_url']]

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
            print(
                f"Replacing an internal subsection link: {full_href} {final_href}")
        else:
            final_href = chap_id
            print(
                f"Replacing an internal chapter link: {full_href} {final_href}")
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
            element.string = (element.string or '') + \
                config['external_link_symbol']

"""
Scrape external images and replace their src's with base64 encoded versions
"""
if config['scrape_images']:
    images_by_src = defaultdict(lambda: [])
    for (post, element) in post_select_iter('img[src]'):
        full_src = uritools.urijoin(post['final_url'], element['src'])
        images_by_src[full_src].append(element)

    # Multi-scraping images currently disabled because of a python segfault (??)
    def multi_scrape_image(image_scraper, src):
        try:
            image_filename = urlparse(src).path.split('/')[-1]
            image_path = f'{image_folder}/{image_filename}'
            absolute_image_path = os.path.join(os.path.dirname(__file__), '..', 'books', image_path)

            if os.path.exists(absolute_image_path):
                print("Image already downloaded, skipping:", image_path)
                return dict(
                    src=src,
                    response=None,
                )

            print(f"Scraping image: {src}")
            scraper_results = image_scraper.scrape(src, stream=True)
            return dict(
                src=src,
                response=scraper_results['response'],
            )
        except (urllib.error.URLError, ssl.SSLError):
            print(f"Network error on {src}")
            return None
    #
    # with multiprocessing.Pool(max(1, min(len(images_by_src), max_threads))) as thread_pool:
    #     scraped_images = list(filter(lambda x: x is not None, map(
    #         multi_scrape_image,
    #         [(image_scraper, key) for key in images_by_src.keys()],
    #     )))

    scraped_images = list(filter(lambda x: x is not None, map(
        lambda pair: multi_scrape_image(*pair),
        [(image_scraper, key) for key in images_by_src.keys()],
    )))

    print("Processing images")

    # Record the TOC pages into included_scraped_urls
    for scraped_image in scraped_images:
        image_filename = urlparse(scraped_image['src']).path.split('/')[-1]
        image_path = f'{image_folder}/{image_filename}'
        absolute_folder_path = os.path.join(os.path.dirname(__file__), '..', 'books', image_folder)
        absolute_image_path = os.path.join(os.path.dirname(__file__), '..', 'books', image_path)

        if scraped_image['response'] is not None:  # It's not cached # TODO: Distinguish from Selenium requests here that don't have a response object
            if scraped_image['response'].status_code != 200:
                print()
            Path(absolute_folder_path).mkdir(exist_ok=True)
            with open(absolute_image_path, 'wb') as image_file:
                scraped_image['response'].raw.decode_content = True
                shutil.copyfileobj(scraped_image['response'].raw, image_file)

        for image_tag in images_by_src[scraped_image['src']]:
            print(f"Processing image: {image_tag['src']}")
            # TODO: Don't redundantly re-encode images used multiple times in the book
            if scraped_image['response']:
                content_type = scraped_image['response'].headers['Content-Type']
            else:
                # TODO: For selenium, maybe just grab the images out of the page instead of navigating to them directly
                content_types = {
                    '.svg': 'image/svg+xml',
                    '.gif': 'image/gif',
                    '.jpg': 'image/jpeg',
                    '.jpeg': 'image/jpeg',
                    '.png': 'image/png',
                }
                for extension, content_type_candidate in content_types.items():
                    if extension in scraped_image['src'].lower():
                        content_type = content_type_candidate
                        break
                else:
                    print(
                        f"Skipped image with unknown content type: {scraped_image['src']}")
                    continue  # Skip this image if we don't know its encoding
            if False and content_type == 'image/svg+xml':  # TODO: Verify this still works after the below changes; or, save it as a file too.
                print(f"Inlining an image as svg: {image_tag['src']}")
                encoded_image = scraped_image['response'].content.decode('ascii')
                image_tag['src'] = f"data:{content_type};utf8,{encoded_image}"
                # svg_tag = BeautifulSoup(encoded_image, 'html.parser')
                # svg_tag.attrs = image_tag.attrs
                # image_tag.replace_with(svg_tag)
            else:
                # Massage tall images to fit into one page correctly
                image_tag['src'] = image_path
                image_tag['style'] = "max-height: 700px; max-width: 500px; object-fit: contain; margin: 0; padding: 0;"
                if int(image_tag.get('height', 0)) > 200:
                    soup = BeautifulSoup()
                    wrap_div = soup.new_tag('div')
                    wrap_div['style'] = "page-break-inside: avoid; page-break-before: always; margin: 0; padding: 0;"
                    image_tag.wrap(wrap_div)

                if 'srcset' in image_tag:
                    del image_tag['srcset']
                if 'width' in image_tag:
                    del image_tag['width']
                if 'height' in image_tag:
                    del image_tag['height']
                # print(f"Inlining an image as base64: {image_tag['src']}")
                # encoded_image = base64.b64encode(
                #     scraped_image['data']).decode('ascii')
                # image_tag['src'] = f"data:{content_type};base64,{encoded_image}"

# """
# Update image src's to be full URLs
# """
else:
    for (post, element) in post_select_iter('[src]'):
        full_src = uritools.urijoin(post['final_url'], element['src'])
        if element['src'] != full_src:
            print(f"Updating image src from {element['src']} to {full_src}")
            element['src'] = full_src

"""
Assemble the output html
"""

book_html = ""
if config['toc_keep_original_formatting']:
    toc_result_html = str(toc_element)
else:
    if config['crawl_mode'] == 'toc':
        toc_result_html = '<h1 id="toc">Table of Contents</h1>' + \
            '<br>'.join(map(lambda link: str(link['tag']), toc_links))
    elif config['crawl_mode'] == 'incremental':
        def toc_link_from_post(
            post): return f"<a href=\"#{final_url_to_id[post['final_url']]}\">{post['title_soup'].text}</a>"
        toc_result_html = '<h1 id="toc">Table of Contents</h1>' + \
            '<br>'.join(map(toc_link_from_post, posts))
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
    <style>
    @font-face {{
        font-family: "Noto Sans Symbols 2";
        src: url("fonts/NotoSansSymbols2-Regular.ttf") format("truetype");
    }}
    </style>
    <body>
        {book_html}
    </body>
</html>
"""

book_html = BeautifulSoup(book_html, 'html.parser')

print(f"{len(posts)} posts scraped and assembled.")
"""
Write out the file
"""

print("Writing file")


def ensure_dir(file_path):
    directory = os.path.dirname(file_path)
    if not os.path.exists(directory):
        os.makedirs(directory)


book_base_name = os.path.splitext(args.config_filename)[0]
books_folder = os.path.join(os.path.dirname(__file__), '../books')
ensure_dir(books_folder)
book_file = open(os.path.join(books_folder, book_base_name + '.html'), 'wb')
book_file.write(book_html.encode('utf-8'))

print("Done.")

if args.format:
    for format in args.format.split(','):
        convert_ebook(config, book_base_name, format)
