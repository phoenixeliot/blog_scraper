# Generalized blog / web serial scraper

This converts blogs into ebooks, by scraping them with Selenium.

# Author credits (incomplete)
Wildbow: [Please support the author!](http://parahumans.wordpress.com/donate/)

## Download

Download the ebook from the `books` folder, or run the scraper yourself.

## How to run:

1. Clone this project
2. Install dependencies

```command
python3.6 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

3. Run the script with whichever config file you want (and you can write your own config)

```command
python ./src/scrape.py pale.yml --format=epub,mobi
```

The resulting scraped book will appear in `./books`.

The yml config files may get out of date when websites change their layout. Feel free to file issues or pull requests for fixes or new sites to scrape, but I only check this occasionally.

## Misc notes

worm_editor.rb is a script I wrote to go with worm_scraper.rb which I took from [here](https://github.com/TheBrain0110/worm_scraper). I intend to clean this repo up and remove that old code, but haven't yet.

worm_edited and ward_edited have some automatic copyediting applied that fix some common annoyances, like not using em-dashes, incorrect spacing, or incorrect direction quote marks.
