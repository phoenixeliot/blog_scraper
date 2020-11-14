# Generalized blog / web serial scraper

I couldn't find a good ebook/kindle version of worm, the fantastic web serial by wildbow (John McCrae), so I decided to make one. You can now enjoy worm without all of the eye strain! Until wildbow gets this thing published, this is the next best option.

[Please support the author!](http://parahumans.wordpress.com/donate/)

![Worm Header](http://parahumans.files.wordpress.com/2011/06/cityscape2.jpg)

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
