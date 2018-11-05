import yaml
import os
from collections import defaultdict

from src.blog_post import BlogPost
from src.book_assembler import BookAssembler
from src.scrapers import SeleniumScraper, FetchScraper
from src.toc_manager import TOCManager


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
# scrape it
if config['scraper_engine'] == 'selenium':
    scraper = SeleniumScraper()
else:
    scraper = FetchScraper()
expand_toc_js = config['toc_js']
toc_html = scraper.scrape(config['toc_url'], wait_for_selector=config['toc_selector'], js=expand_toc_js)

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
import multiprocessing


def multi_scrape_html(link):
    html = scraper.scrape(link.href)
    return dict(link=link, html=html)


with multiprocessing.Pool(min(len(toc_manager.links), 10)) as thread_pool:
    scraped_links = thread_pool.map(multi_scrape_html, toc_manager.links)

posts = list(map(
    lambda pair: BlogPost(
        url=pair['link'].href,
        html=pair['html'],
        post_title_selector=config['post_title_selector'],
        post_body_selector=config['post_body_selector'],
    ),
    scraped_links
))

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




print('Done.')
