from set_wallpaper import set_wallpaper
from reddit_download import next_post, download_from_url
import sys, os, time, threading
if sys.version_info >= (3, 0):
    from configparser import SafeConfigParser
else:
    from ConfigParser import SafeConfigParser
from argparse import ArgumentParser
from reddit_download import next_post

updateWallpaperThread = None
default_values = {'saveDirectory': '', 'reddit': 'wallpapers', 'sfw': '0', 'last': '', 'score': '0', 'title': '', 'url': '', 'path': '', 'time': '0'}

def init_config():
    config = SafeConfigParser()
    config.read('config.ini')
    if 'main' not in config.sections():
        config.add_section('main')
    for k, v in default_values.items():
        if k not in config.options('main'):
            config.set('main', k, v)
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
    PARSER.add_argument('-t', '--time', type=int, default=0, required=False, help="Interval time in minutes.")

    PARSER.add_argument('-i', '--info', action='store_true', required=False, help="Display the info of the current image")

    PARSER.add_argument('-d', '--download', default=config.get('main', 'saveDirectory'), required=False, help="Download the image to specified directory.")

    parsed_argument = PARSER.parse_args(args)

    if parsed_argument.sfw is True and parsed_argument.nsfw is True:
        # negate both argument if both argument exist
        parsed_argument.sfw = parsed_argument.nsfw = False

    return parsed_argument

def saveImage(localPath):
    tmpPath = config.get('main', 'path')
    if os.path.exists(localPath):
        if os.path.isdir(localPath):
            resPath = os.path.join(localPath, os.path.basename(tmpPath))
        else:
            while os.path.exists(localPath):
                localPath = input("File exists, enter a different location: ")
            resPath = localPath
    else:
        resPath = localPath

    print('Saving image at %s to %s' % (localPath, resPath))
    shutil.copyfile(localPath, resPath)

def update(args):
    for k, v in args._get_kwargs():
        if k != 'last' and k in config.options('main') and v:
            config.set('main', k, str(v).lower())
            config.set('main','last', '')

    if args.last:
        config['main']['last'] = args.last

def wait_for_download(url):
    url.download()
    start = time.clock()
    while url.localUrl == '':
        if time.clock() - start > 10000:
            return
        continue
    res = set_wallpaper(url.localUrl)
    if res == 0:
        print("Wallpaper failed to set")
    else:
        print("Wallpaper successfully set")
    config.set('main', 'path', url.localUrl)
    export_config()

def next_image():
    print("Next image...")
    global updateWallpaperThread
    urls = next_post(config.get('main', 'reddit'), last=config.get('main', 'last'),
                sfw=config.getint('main', 'sfw') == 1, nsfw=config.getint('main', 'sfw') == 2,
                score=config.getint('main', 'score'), title=config.get('main', 'title'))
    url = [i for i in urls][0]
    config.set('main', 'last', url['id'])
    url = url['URLS'][0]
    config.set('main', 'url', url.url)

    if os.path.exists(config.get('main', 'path')):
        os.remove(config.get('main', 'path'))

    updateWallpaperThread = threading.Thread(None, lambda : wait_for_download(url))
    updateWallpaperThread.start()

def print_info():
    print("""Image URL: %s
Local Path: %s
ID: %s
Subreddit: %s""" % (config.get('main', 'url'), config.get('main', 'path'), config.get('main', 'last'), config.get('main', 'reddit')))

def schedule_intervals():
    #import schedule
    #schedule.every(config.getint('main', 'time')).seconds.do(next_image)
    print("Scheduled every %s minutes" % config.getint('main', 'time'))
    while True:
        #schedule.run_pending()
        next_image()
        time.sleep(config.getint('main', 'time')) #60 * config.getint('main', 'time')-1)

if __name__ == '__main__':
    args = sys.argv[1:]
    #args = [
    #"-r", "all",
    #'--nsfw',
    #'--sfw',
    #'--title', 'Cat',
    #'--score', 1000
    #]
    config = init_config()
    args = parse_args(args)
    update(args)
    if args.download:
        path = args.download
        saveImage(path)
    elif args.info:
        print_info()
    elif args.time:
        schedule_intervals()
    else:
        next_image()
        if args.info:
            print_info()

