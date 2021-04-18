import os
from bs4 import BeautifulSoup, NavigableString

with open(os.path.join(os.path.dirname(__file__), "pale", "🟂.svg")) as f:
    threePointedStarSVG = f.read()


def rewrite_post(post, config):
    first_p = post["body_soups"][0].find("p")
    if len(first_p.text.strip()) == 0 and first_p.find("img") is None:
        first_p.decompose()  # TODO: probably remove, not used anymore I think
    for soup in post["body_soups"]:
        for element in soup.select(".emoji"):
            element["style"] = "width: 1em"
    for soup in post["body_soups"]:
        for el in list(soup.strings):
            if isinstance(el, NavigableString):
                if "🟂" in str(el):
                    star = BeautifulSoup(threePointedStarSVG, "html.parser")
                    el.replaceWith(star)

        for link in soup.select("a[href]"):
            if link["href"].startswith("palewebserial.wordpress"):
                link["href"] = "https://" + link["href"]

        # Remove the <hr> if there's nothing above it but the title, for aesthetics
        item = soup.find_all()[0]
        next_sibling = item.next_sibling

        def get_text(node):
            if node is None:
                return ""
            if isinstance(node, NavigableString):
                return str(node)
            else:
                return node.get_text()

        while next_sibling is not None and (
            get_text(next_sibling).strip() in config["blacklist_texts"]
            or get_text(next_sibling).strip() == ""
        ):
            if (
                isinstance(next_sibling, NavigableString)
                and get_text(next_sibling).strip() == ""
            ):
                string = next_sibling
                next_sibling = next_sibling.next_sibling
                string.extract()
                continue
            if next_sibling.name == "hr":
                next_sibling.decompose()
                break
            next_sibling = next_sibling.next_sibling

        # # Remove spaces between lead image and the rest
        # next_sibling = soup.find('img').next_sibling
        # while isinstance(next_sibling, NavigableString) and get_text(next_sibling).strip() == '':
        #     string = next_sibling
        #     next_sibling

        # Prevent h1s within the post (for POV character name); use <b> instead.
        h1s = soup.select("h1")
        for h1 in h1s:
            h1.name = "b"

        # If the chapter ends in an <hr> or blank strings, remove them
        last_element = soup.find_all()[-1]
        while last_element.name == "hr" or (
            isinstance(last_element, NavigableString)
            and get_text(last_element).strip() == ""
        ):
            to_del = last_element
            last_element = last_element.previous_element
            to_del.extract()

        # TODO: Disabled, not sure why. Might need fixing?
        # If there's multiple images in a row, delete any blank paragraphs between them to prevent blank pages on kindle
        # images = soup.select('img')
        # for image in images:
        #     nodes_to_remove = []
        #     next_sibling = image.next_sibling
        #     while next_sibling is not None and next_sibling.name != 'img':
        #         nodes_to_remove.append(next_sibling)
        #         next_sibling = next_sibling.next_sibling
        #     if all(map(lambda n: n.encode_contents().strip() == ''), nodes_to_remove):
        #         for node in nodes_to_remove:
        #             node.extract()


def rewrite_toc(toc):
    for link in toc.select("a[href]"):
        if link["href"].startswith("palewebserial.wordpress"):
            link["href"] = "https://" + link["href"]
