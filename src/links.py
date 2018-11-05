from uritools import urijoin


# TODO: Merge/generalize with TOCLink
class ContentLink:
    def __init__(self, tag=None, text='', href='', source_url=''):
        self.tag = tag
        self.text = text
        self.original_href = href
        self.source_url = source_url
        self.href = urijoin(source_url, href)

    def to_html(self):
        return f'<a href="{self.href}">{self.text}</a>'


class TOCLink:
    def __init__(self, text='', href='', source_url=''):
        self.text = text
        self.original_href = href
        self.source_url = source_url
        self.href = urijoin(source_url, href)

    def to_html(self):
        return f'<a href="{self.href}">{self.text}</a>'


# TODO maybe rename to TOCLocalizedLink or TOCInternalLink or TOCUniqueLink or sth
class TOCHashedLink:
    def __init__(self, link, hash_id):
        self.link = link
        self.hash_id = hash_id

    def to_html(self):
        return f'<a href="#{self.hash_id}">{self.link.text}</a>'
