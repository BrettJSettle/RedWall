"""module to parse deviantart page."""
try:  # py2
    from urllib2 import urlopen
except ImportError:  # py3
    from urllib.request import urlopen

from bs4 import BeautifulSoup
import re

def process_deviant_url(url):
    """
    process deviantart url.

    Given a DeviantArt URL, determine if it's a direct link to an image, or
    a standard DeviantArt Page. If the latter, attempt to acquire Direct link.

    Returns:
        deviantart image url
    """
    # We have it! Dont worry
    if url.endswith('.jpg'):
        return [url]
    else:
        text = urlopen(url).read().decode('utf-8')
        soup_imgs = re.findall(r'img[^>]* src="([^"]*filters:no_upscale\(\):origin\(\)/[^"]*)"', text)
        imgs = []
        #html_soup = BeautifulSoup(text, 'lxml')
        marker = 'filters:no_upscale():origin()/'
        #soup_imgs = [xx.get('src') for xx in html_soup.select('img')
        #             if marker in xx.get('src')]
        for ori_img in soup_imgs:
            img_parts = ori_img.split(marker)[1].split('/', 1)
            img_server = img_parts[0]
            img_sub = img_parts[1]
            imgs.append('http://{}.deviantart.net/{}'.format(img_server, img_sub))
        return imgs
    return [url]
