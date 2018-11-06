import re


def rewrite_post(post):
    for soup in post['body_soups']:
        for element in soup.select('[href]'):
            if re.match('\w+\.(com|org)', element['href']):
                new_href = 'http://' + element['href']
                print(f"Fixing invalid link href {element['href']} to {new_href}")
                element['href'] = new_href
