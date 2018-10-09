from .set_wallpaper import set_wallpaper
from .reddit_scraper import RedditScraper
from .getch import getch

import time, sys, os, shutil
from argparse import ArgumentParser

if sys.version.startswith('2'):
	input = raw_input

def screensaver(scrapeSettings={}, interval=8):
	verbose = scrapeSettings.pop('verbose')
	scraper = RedditScraper(**scrapeSettings)
	lastImage = None
	s = -1
	for image in scraper.imageIter():
		path = image.download()
		if not image.path:
			continue
		
		if verbose:
			print("Downloaded to %s" % image.path)
		# sleep extra time
		if s > 0 and time.time() - s < interval:
			time.sleep(interval - (time.time() - s))
		
		set_wallpaper(image.path)
		if (lastImage == None or image.id != lastImage.id):
			print("Post ID: %s" % image.id)

		if lastImage != None:
			lastImage.removeLocal()
		lastImage = image
		s = time.time()



def control(scrapeSettings={}):
	verbose = scrapeSettings.pop('verbose')
	scraper = RedditScraper(**scrapeSettings)
	history = {}
	image_id = 0
	post_id = 0
	print("Scraping some posts to start...")
	scraper.getPosts(5)
	print("Press 'h' to see the help menu. Enjoy!")
	post = None

	save_dir = os.path.expanduser('~/Downloads')

	while True:
		ch = getch()
		if (ord(ch) == 27):
			getch()
			ch = getch()
			if ch == 'C':
				if scraper._started:
					image_id += 1
			elif ch == 'D':
				image_id -= 1
		elif ch == 'n':
			if post != None:
				image_id = len(post)
		elif ch == 'p':
			image_id = -1
		elif ch == 'q' or ord(ch) in (3, 4):
			break
		elif ch == 'i':
			print(str(post))
			continue
		elif ch == 's':
			sub = input('Subreddit: ')
			scraper.update('subreddit', sub)
			post = None
			history = {}
			post_id = 0
			image_id = 0
		elif ch == 'd':
			path = input("Download the file to (%s): " % save_dir)
			if not os.path.isdir(os.path.dirname(path)):
				path = os.path.join(save_dir, path)
			else:
				save_dir = os.path.dirname(path)
			shutil.copy(image.path, path)
			print("Successfully saved to %s" % path)
			continue
		elif ch == 'h':
			print('''
Use the left and right arrow to iterate through images.
Other keys:
	i - Get info on current post
	n - next post
	p - previous post (until none are cached)
	s - change subreddits
	d - download the image locally
	h - display this help screen
	q - Quit
''')
			continue
		else:
			print(ord(ch))

		if post:
			if image_id >= len(post):
				image_id = 0
				post_id += 1
				if post_id in history:
					post = history[post_id]
				else:
					post = scraper.next()
					history[post_id] = post
					if len(history) > 10:
						history.pop(min(history.keys()))
			if image_id < 0:
				if (history):
					atEnd = post_id != 0
					post_id = max(0, post_id - 1)
					post = history[post_id]
					if atEnd:
						image_id = max(0, len(post) - 1)
					else:
						image_id = 0
				else:
					image_id = 0
		else:
			post = scraper.next()
			history[post_id] = post

		while len(post) == 0:
			post = scraper.next()
			history[post_id] = post

		print("POST %d with ID: %s\n\t Image %d/%d. (%d posts cached)" % 
				(post_id+1, post.id, image_id + 1, len(post), len(history)))
		image = post[image_id]
		post.next_index = image_id
		path = image.download()
		if not image.path:
			continue
		if verbose:
			print("Downloaded to %s" % image.path)
		set_wallpaper(image.path)

	for post in history.values():
		for image in post:
			image.removeLocal()

def parse_args(args):
	PARSER = ArgumentParser(description='Downloads files with specified extension'
			'from the specified subreddit.')
	PARSER.add_argument('--subreddit', default='wallpapers', help='Subreddit name.', required=False)

	PARSER.add_argument('--previd', metavar='previd', default='', required=False,
			help='ID of the last downloaded file.')
	
	PARSER.add_argument('--score', metavar='score', default=0, type=int, required=False,
			help='Minimum score of images to download.')
	
	PARSER.add_argument('--nsfwo', action="store_true", required=False,
			help='Nsfw only results')
	
	PARSER.add_argument('--nsfw', action="store_true", required=False,
			help='show nsfw results')
	
	PARSER.add_argument('--title', metavar='title', required=False,
			help='Download only if title contain text (case insensitive)')
	PARSER.add_argument('-i', '--interval', type=int, default=8, required=False, help="Interval time in seconds.")

	PARSER.add_argument('-c', '--control', action='store_true', required=False, help='Enter a console with controls to iterate through images')
	PARSER.add_argument('-v', '--verbose', action='store_true', required=False, help='Display file location when downloaded')
	parsed_argument = PARSER.parse_args(args)

	if parsed_argument.nsfwo is True and parsed_argument.nsfw is True:
		# negate both argument if both argument exist
		parsed_argument.nsfwo = parsed_argument.nsfw = False

	return parsed_argument

def screensaver_endpoint():
	main()

def control_endpoint():
	main(sys.argv[1:] + ['-c'])

def main(argv=sys.argv[1:]):
	args = parse_args(argv)
	
	args = args.__dict__

	args['sfw'] = not args.pop('nsfwo')
	if args.pop('control'):
		args.pop('interval')
		control(args)
	else:
		i = args.pop('interval')
		screensaver(args, interval=i)
	

if __name__ == '__main__':
	main()
