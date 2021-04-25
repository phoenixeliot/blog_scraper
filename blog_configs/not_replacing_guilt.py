import re


replacing_guilt_links = [
    "http://mindingourway.com/half-assing-it-with-everything-youve-got/",
    "http://mindingourway.com/failing-with-abandon/",
    "http://mindingourway.com/replacing-guilt/",
    "http://mindingourway.com/the-stamp-collector/",
    "http://mindingourway.com/youre-allowed-to-fight-for-something/",
    "http://mindingourway.com/caring-about-some/",
    "http://mindingourway.com/you-dont-get-t/",
    "http://mindingourway.com/should-considered-harmful/",
    "http://mindingourway.com/not-because-you-should/",
    "http://mindingourway.com/shoulds-are-not-a-duty/",
    "http://mindingourway.com/stop-before-you-drop/",
    "http://mindingourway.com/rest-in-motion/",
    "http://mindingourway.com/shifting-guilt/",
    "http://mindingourway.com/dont-steer-with-guilt/",
    "http://mindingourway.com/update-from-the-suckerpunch/",
    "http://mindingourway.com/be-a-new-homunculus/",
    "http://mindingourway.com/not-yet-gods/",
    "http://mindingourway.com/where-coulds-go/",
    "http://mindingourway.com/self-compassion/",
    "http://mindingourway.com/there-are-no/",
    "http://mindingourway.com/residing-in-the-mortal-realm/",
    "http://mindingourway.com/being-unable-to-despair/",
    "http://mindingourway.com/see-the-dark-world/",
    "http://mindingourway.com/choose-without-suffering/",
    "http://mindingourway.com/detach-the-grim-o-meter/",
    "http://mindingourway.com/simply-locate-yourself/",
    "http://mindingourway.com/have-no-excuses/",
    "http://mindingourway.com/come-to-your-terms/",
    "http://mindingourway.com/transmute-guilt-i/",
    "http://mindingourway.com/best-you-can/",
    "http://mindingourway.com/dark-not-colorless/",
    "http://mindingourway.com/stop-trying-to-try-and-try/",
    "http://mindingourway.com/there-is-no-try/",
    "http://mindingourway.com/obvious-advice/",
    "http://mindingourway.com/the-art-of-response/",
    "http://mindingourway.com/confidence-all-the-way-up/",
    "http://mindingourway.com/desperation/",
    "http://mindingourway.com/recklessness/",
    "http://mindingourway.com/defiance/",
    "http://mindingourway.com/how-we-will-be-measured/",
    "http://mindingourway.com/on-caring/",
    "http://mindingourway.com/the-value-of-a-life/",
    "http://mindingourway.com/moving-towards-the-goal/",
    "http://mindingourway.com/self-signaling-the-ability-to-do-what-you-want/",
    "http://mindingourway.com/productivity-through-self-loyalty/",
    "http://mindingourway.com/guilt-conclusion",
]


def rewrite_post(post, config):
    for soup in post["body_soups"]:
        for element in soup.select("[href]"):
            if re.match("\w+\.(com|org)", element["href"]):
                new_href = "http://" + element["href"]
                print(f"Fixing invalid link href {element['href']} to {new_href}")
                element["href"] = new_href


def post_filter(post, config):
    return post['final_url'] not in replacing_guilt_links
