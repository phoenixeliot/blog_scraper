from bs4 import BeautifulSoup, NavigableString

def rewrite_post(post, config):
    first_p = post['body_soups'][0].find('p')
    if len(first_p.text.strip()) == 0 and first_p.find('img') is None:
        first_p.decompose()
    for soup in post['body_soups']:
        for element in soup.select('.emoji'):
            element['style'] = 'width: 1em'
    for soup in post['body_soups']:
        for el in list(soup.strings):
            if isinstance(el, NavigableString):
                if "🟂" in str(el):
                    # el.replace_with(str(el).replace('🟂', '⏅'))
                    if 'style' not in el.parent.attrs:
                        el.parent.attrs['style'] = ''
                    el.parent.attrs['style'] += ';font-family: "Noto Sans Symbols 2", serif;'

        for link in soup.select('a[href]'):
            if link['href'].startswith('palewebserial.wordpress'):
                link['href'] = 'https://' + link['href']

        # Remove the <hr> if there's nothing above it but the title, for aesthetics
        item = soup.find_all()[0]
        next_sibling = item.next_sibling
        def get_text(node):
            if node is None:
                return ''
            if isinstance(node, NavigableString):
                return str(node)
            else:
                return node.get_text()
        while (next_sibling is not None
               and (get_text(next_sibling).strip() in config['blacklist_texts']
                    or get_text(next_sibling).strip() == '')
        ):
            if isinstance(next_sibling, NavigableString) and get_text(next_sibling).strip() == '':
                string = next_sibling
                next_sibling = next_sibling.next_sibling
                string.extract()
                continue
            if next_sibling.name == 'hr':
                next_sibling.decompose()
                break
            next_sibling = next_sibling.next_sibling
            print()

        # # Remove spaces between lead image and the rest
        # next_sibling = soup.find('img').next_sibling
        # while isinstance(next_sibling, NavigableString) and get_text(next_sibling).strip() == '':
        #     string = next_sibling
        #     next_sibling

        # Prevent h1s within the post (for POV character name); use <b> instead.
        h1s = soup.select('h1')
        for h1 in h1s:
            h1.name = 'b'

        last_element = soup.find_all()[-1]
        while last_element.name == 'hr' or (
            isinstance(last_element, NavigableString) and get_text(last_element).strip() == ''
        ):
            to_del = last_element
            last_element = last_element.previous_element
            to_del.extract()


def rewrite_toc(toc):
    for link in toc.select('a[href]'):
        if link['href'].startswith('palewebserial.wordpress'):
            link['href'] = 'https://' + link['href']
