def rewrite_post(post):
    for soup in post['body_soups']:
        for element in soup.select('img[src]'):
            if element['src'] == 'http://www.wallpaper77.com/upload/DesktopWallpapers/cache/Kodama-ipad-3-wallpaper-ipad-wallpaper-retina-display-wallpaper-the-new-ipad-wallpaper--1600x1200.jpg'
                element['src'] = 'https://web.archive.org/web/20170818074822if_/'
