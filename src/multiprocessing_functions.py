"""
All of these are broken right now; need to figure out what Multiprocessing needs to be able to run properly.
"""
import multiprocessing
import urllib.error
import ssl


def scrape_html(href, config, scraper):
    try:
        print(f"Scraping post: {href}")
        scraper_results = scraper.scrape(
            href, wait_for_selector=config["post_body_selector"]
        )
        return dict(
            href=href,
            html=scraper_results["html"],
            final_url=scraper_results["final_url"],
        )
    # TODO: Do something analogous for Selenium. Probably in several places.
    except (urllib.error.URLError, ssl.SSLError):
        return None


def multi_scrape_extra_pages(posts, max_threads, config, scraper, extra_page_urls):
    return list(
        map(multi_scrape_html, map(lambda url: (url, config, scraper), extra_page_urls))
    )
    with multiprocessing.Pool(max(1, min(len(posts), max_threads))) as thread_pool:
        scraped_extra_pages = list(
            filter(
                lambda x: x is not None,
                thread_pool.starmap(
                    multi_scrape_html,
                    map(lambda url: (url, config, scraper), extra_page_urls),
                ),
            )
        )
        return scraped_extra_pages


def multi_scrape_toc_links(
    toc_links, max_threads, absolute_from_relative_url, config, scraper
):
    with multiprocessing.Pool(max(1, min(len(toc_links), max_threads))) as thread_pool:
        scraped_toc_links = list(
            filter(
                lambda x: x is not None,
                thread_pool.starmap(
                    multi_scrape_html,
                    map(
                        lambda l: (
                            absolute_from_relative_url(l["tag"]["href"]),
                            config,
                            scraper,
                        ),
                        toc_links,
                    ),
                ),
            )
        )
        return scraped_toc_links
