def rewrite_post(post, config):
    first_p = post["body_soups"][0].find("p")
    if len(first_p.text.strip()) == 0:
        first_p.decompose()
    for soup in post["body_soups"]:
        for element in soup.select(".emoji"):
            element["style"] = "width: 1em"
