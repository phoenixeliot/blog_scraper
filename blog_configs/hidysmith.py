import re

from bs4 import BeautifulSoup


def rewrite_post(post):
    for soup in post['body_soups']:
        for element in soup.select('.image-block-wrapper'):
            element['style'] = ''
        for element in soup.select('.image-block-wrapper img'):
            element['style'] = ''

def rewrite_toc(toc):
    return toc  # I think something in this is breaking BeautifulSoup's find stuff
    years = toc.select('p')
    lines_by_year = list(map(lambda year: re.findall(re.compile('<br */?>.*?</ *a>', flags=re.DOTALL), str(year)), years))
    lines = [line for lines in lines_by_year for line in lines]
    sorted_lines = sorted(lines, key=lambda line: int(re.search('\\d+', line)[0]))

    combined_tag = BeautifulSoup(''.join(sorted_lines), 'html.parser')

    toc.clear()
    toc.append(combined_tag)

    return toc
