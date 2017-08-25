# RedditBrowser

Scrape subreddits and slideshow through images or posts with a timer.  Images are cached to the temp directory, and removed on close. (Check the temp directory to make sure images are deleted.)

## Requirements
- BeautifulSoup4

## Install

Redwall is available on PyPi. Just run

`pip install redwall`

to get the latest version.

Use cases:

```bash
# For the screensaver version that iterates through images on a time schedule
redwall_screensaver [--subreddit SUBREDDIT] [--previd previd]
                    [--score score] [--nsfwo] [--nsfw] [--title title]
                    [-i INTERVAL] [-v]

# For manual control and more options, use this command
redwall_control [--subreddit SUBREDDIT] [--previd previd]
                [--score score] [--nsfwo] [--nsfw] [--title title] [-v]

```

Each entry point is utilizes the reddit_scraper.RedditScraper iterable class to step through posts and images on the subreddit of your choice.  To use the RedditScraper class in your own project, simply import it with some settings:
```python
from redwall.reddit_scraper import RedditScraper

# initialize the scraper with filters
scraper = RedditScraper(previd='', subreddit='wallpapers', title='', score=100, nsfw=False, sfw=True)

# prescrape posts for speed
scraper.getPosts(5)

# get the next post
post = scraper.next()

#update a filter and get the next post
scraper.update('subreddit', 'wallpaperdump')
post = scraper.next()

# set wallpaper to the first image in the post
from redwall.set_wallpaper import set_wallpaper
image = post.images[0]
image.download()
set_wallpaper(image.path)

# iterate through images
for image in scraper.imageIter():
  # returns None when no more images can be loaded
  if image == None:
    break
  print("Image at %s" % image.url)
```

#### Windowed Branch
The windowed branch is an older version of redwall that runs in a PyQt window.  It is buggy and crashes on occassion, but is useful if you don't want to change your actual wallpaper.  Checkout the branch and run `python main.py` to see it work.
