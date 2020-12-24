from bs4 import BeautifulSoup, NavigableString

def rewrite_post(post, config):
    first_p = post['body_soups'][0].find('p')
    if len(first_p.text.strip()) == 0:
        first_p.decompose()
    for soup in post['body_soups']:
        for element in soup.select('.emoji'):
            element['style'] = 'width: 1em'
    for soup in post['body_soups']:
        for link in soup.select('a[href]'):
            if link['href'].startswith('palewebserial.wordpress'):
                link['href'] = 'https://' + link['href']
        # Remove the <hr> if there's nothing above it but the title, for aesthetics
        for item in soup.select('h1'):
            next_sibling = item.next_sibling
            def get_text(node):
                if isinstance(node, NavigableString):
                    return str(node)
                else:
                    return node.get_text()
            while get_text(next_sibling).strip() in config['blacklist_texts']:
                next_sibling = next_sibling.next_sibling
            if next_sibling.name == 'hr':
                next_sibling.decompose()
        # Prevent multiple h1's per chapter; use h2 instead.
        h1s = soup.select('h1')
        for h1 in h1s[1:]:
            h1.name = 'h2'


def rewrite_toc(toc):
    for link in toc.select('a[href]'):
        if link['href'].startswith('palewebserial.wordpress'):
            link['href'] = 'https://' + link['href']
