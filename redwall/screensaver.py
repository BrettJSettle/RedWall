from set_wallpaper import set_wallpaper
from reddit_scraper import RedditScraper
import time, sys
from argparse import ArgumentParser
from getch import getch

def screensaver(scrapeSettings={}, interval=8):
	scraper = RedditScraper(**scrapeSettings)
	lastImage = None
	s = -1
	for image in scraper.imageIter():
		path = image.download()
		if not image.path:
			continue
		
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
	scraper = RedditScraper(**scrapeSettings)
	history = {}
	image_id = 0
	post_id = 0
	print("PREPPING")
	scraper.getPosts(5)
	print("READY")
	post = None

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
			image_id = len(post)
		elif ch == 'p':
			image_id = -1
		elif ch == 'q':
			break
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
		path = image.download()
		if not image.path:
			continue
		set_wallpaper(image.path)

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
		control(args)
	else:
		i = args.pop('interval')
		screensaver(args, interval=i)
	

if __name__ == '__main__':
	main()
