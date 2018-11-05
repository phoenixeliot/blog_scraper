import operator
from functools import reduce
from src.links import ContentLink


class BookAssembler():
    def __init__(self, toc_manager, posts):
        self.toc_manager = toc_manager
        self.posts = posts

    def to_html(self):
        toc_html = self.toc_manager.to_html()

        hashed_links_by_url = {}
        for hashed_link in self.toc_manager.toc_entries:
            hashed_links_by_url[hashed_link.link.href] = hashed_link

        for post in self.posts:
            # there will usually be 1 post_soup per post, but the post content *can* be split across multiple elements
            for post_soup in post.post_soups:
                # Replace links with hash_id links
                content_link_tags = post_soup.select('a[href]')

                content_links = map(
                    lambda tag: ContentLink(tag=tag, text=tag.text, href=tag.attrs['href'], source_url=post.url),
                    content_link_tags
                )
                for content_link in content_links:
                    if content_link.href not in hashed_links_by_url:
                        print(f"Content link is not internal: {content_link.href}")
                        continue
                    # TODO: The Link objects I use aren't actually that useful here. Refactor them to make sense for this.
                    content_link.tag.attrs['href'] = '#' + hashed_links_by_url[content_link.href].hash_id
                    print(f"Replacing link from {content_link.href} to {hashed_links_by_url[content_link.href].hash_id}")

                ## Update ids of sub-sections
                # Get all the tags with IDs, get full URL with hash that would point to that
                # Get all the links from that point to that full URL
                # Replace the links much like above
                # Replace the IDs with new, unique hash_ids (eg chap1_summary)
                # tags_with_ids = post_soup.select('[id]')

                # TODO next: The two things here need to be done together -- make full URLs for *every* link,
                # and assemble all pages + ID'd sections into one lookup table that maps to full URLs

            # Set first element of this chapter to have the right hash_id
            if 'id' in post.post_soups[0].attrs:
                print("huh, it has an ID...")
                pass

            post.title_soup.attrs['id'] = hashed_links_by_url[post.url].hash_id


        posts_html = reduce(operator.add, map(lambda p: p.to_html(), self.posts))
        body = toc_html + posts_html
        # return body
        # TODO: Do I need this for character encoding? Calibre seems to have accounted for it fine.
        return f"""
        <html lang="en-US">
            <head>
                <meta charset="UTF-8">
            </head>
            <body>
                {body}
            </body>
        </html>
        """
