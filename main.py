from set_wallpaper import set_wallpaper
from reddit_download import next_post, download_from_url
import sys, os, time, threading
from configparser import SafeConfigParser
from argparse import ArgumentParser
from reddit_download import next_post

updateWallpaperThread = None

def init_config():
	config = SafeConfigParser()
	config.read('config.ini')
	if 'main' not in config.sections():
		config.add_section('main')
		config.set('main', 'reddit', 'wallpapers')
		config.set('main', 'sfw', '0')
		config.set('main', 'last', '')
		config.set('main', 'score', '0')
		config.set('main', 'title', '')
		config.set('main', 'currentUrl', '')
		config.set('main', 'currentLocal', '')
		with open('config.ini', 'w') as f:
			config.write(f)
	return config

def export_config():
	with open('config.ini', 'w') as f:
		config.write(f)

config = init_config()

def parse_args(args):
    PARSER = ArgumentParser(description='Downloads files with specified extension'
                            'from the specified subreddit.')
    PARSER.add_argument('-r', '--reddit', default=None, help='Subreddit name.', required=False)
   
    PARSER.add_argument('--last', metavar='l', default='', required=False,
                        help='ID of the last downloaded file.')
    PARSER.add_argument('--score', metavar='s', default='0', type=int, required=False,
                        help='Minimum score of images to download.')
    PARSER.add_argument('--sfw', default=0, required=False,
                        help='SFW level: 0=no preference, 1=sfw, 2=nsfw')
    PARSER.add_argument('--title-contain', metavar='TEXT', required=False,
                        help='Download only if title contain text (case insensitive)')

    parsed_argument = PARSER.parse_args(args)

    if parsed_argument.sfw is True and parsed_argument.nsfw is True:
        # negate both argument if both argument exist
        parsed_argument.sfw = parsed_argument.nsfw = False

    return parsed_argument
	
def update(args):
	for k, v in args._get_kwargs():
		if k != 'last' and k in config['main'] and v:
			config['main'][k] = str(v).lower()
			config['main']['last'] = ''


	if args.last:
		config['main']['last'] = args.last
	
def wait_for_download(url):
	url.download()
	start = time.clock()
	while url.localUrl == '':
		if time.clock() - start > 10000:
			return
		continue
	set_wallpaper(url.localUrl)
	config.set('main', 'currentLocal', url.localUrl)
	export_config()
	
def next_image():
	global updateWallpaperThread
	urls = next_post(config.get('main', 'reddit'), last=config.get('main', 'last'), 
			sfw=config.getint('main', 'sfw') == 1, nsfw=config.getint('main', 'sfw') == 2, 
			score=config.getint('main', 'score'), title=config.get('main', 'title'))
	url = [i for i in urls][0]
	config.set('main', 'last', url['id'])
	config.set('main', 'currentUrl', url['url'])
	print("""Image info:
	Url: %s
	tTitle: %s
	Id: %s
	Images: %d""" % (url['url'], url['title'], url['id'], len(url['URLS'])))

	url = url['URLS'][0]
	if os.path.exists(config.get('main', 'currentLocal')):
		os.remove(config.get('main', 'currentLocal'))

	updateWallpaperThread = threading.Thread(None, lambda : wait_for_download(url))
	updateWallpaperThread.start()

if __name__ == '__main__':
	args = sys.argv[1:]
	args = [
	#	"-r", "all",
	#	'--nsfw',
	#	'--sfw',
	#	'--title', 'Cat',
	#	'--score', 1000
		]
	config = init_config()
	
	if len(args) > 0:
		args = parse_args(args)
		update(args)

	print("Getting next image")
	next_image()