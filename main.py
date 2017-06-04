from set_wallpaper import set_wallpaper
from reddit_download import next_post, download_from_url
import sys, os, time, threading
import shutil
from argparse import ArgumentParser
from reddit_download import next_post
import pickle

updateWallpaperThread = None

class Settings:
	def __init__(self):
		self.saveDirectory = ''
		self.reddit = ''
		self.sfw = 0
		self.last = ''
		self.score = 0
		self.title = ''
		self.post = None
		self.interval = 10
		self.path = ''

	def update(self, args):
		args_map = {'score': 'score', 'sfw': 'sfw', 'title_contain': 'title'}
		if args.reddit:
			self.last = ''
			self.post = None
			self.reddit = args.reddit
		
		for k, v in args_map.items():
			ak = getattr(args, k)
			cv = getattr(self, v)
			if ak and cv != av:
				setattr(self, v, ak)

		if args.last:
			self.last = args.last

	@staticmethod
	def load(path='config.p'):
		settings = Settings()
		if os.path.exists(path):
			try:
				settings = pickle.load(open(path, 'rb'))
			except Exception as e:
				print("Failed to load settings. \n%s\nUsing defaults" % e)
		return settings

	def save(self, path='config.p'):
		return pickle.dump(self, open(path, 'wb'))

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

	PARSER.add_argument('-c', '--control', action='store_true', required=False, help='Enter a console with controls to iterate through images')

	PARSER.add_argument('-g', '--gui', action='store_true', required=False, help='Show a gui to control the wallpaper')

	PARSER.add_argument('-d', '--download', default=config.saveDirectory, required=False, help="Download the image to specified directory.")

	parsed_argument = PARSER.parse_args(args)

	if parsed_argument.sfw is True and parsed_argument.nsfw is True:
		# negate both argument if both argument exist
		parsed_argument.sfw = parsed_argument.nsfw = False

	return parsed_argument

def saveImage(path):
	print("Saving Image...")
	tmpPath = config.post.currentImage().path
	if os.path.exists(path):
		if os.path.isdir(path):
			resPath = os.path.join(path, os.path.basename(tmpPath))
		else:
			while os.path.exists(path):
				path = input("File exists, enter a different location: ")
			resPath = path
	else:
		resPath = path

	print('Saving image at %s to %s' % (path, resPath))
	shutil.copyfile(path, resPath)


def download_and_show_image(image):
	image.download()
	start = time.clock()
	while image.path == '':
		if time.clock() - start > 10000:
			return
		continue
	res = show_image(image)
	if res == 0:
		print("Wallpaper failed to set")
	

def next_image(post=False):
	print("Next %s..." % ('image' if not post else 'post'))
	image = None
	if not post and config.post:
		image = config.post.next()

	if not image:
		global updateWallpaperThread
		config.post = next_post(config.reddit, last=config.last,
				sfw=config.sfw == 1, nsfw=config.sfw == 2,
				score=config.score, title=config.title)
		config.last = config.post.id
		image = config.post.currentImage()
		config.save()

	print("%d/%d images, ID: %s" % (config.post.image_index + 1, len(config.post), config.post.id))

	show_image(image)

def gui():
	from qtpy import QtCore, QtGui, QtWidgets
	app = QtWidgets.QApplication([])
	win = QtWidgets.QWidget()
	layout = QtWidgets.QGridLayout()
	win.setLayout(layout)
	infoText = QtWidgets.QLabel("Info Here")
	lastButton = QtWidgets.QPushButton("<")
	lastButton.pressed.connect(prev_image)
	nextButton = QtWidgets.QPushButton('>')
	nextButton.pressed.connect(next_image)
	nextPostButton = QtWidgets.QPushButton('>>')
	nextPostButton.pressed.connect(lambda : next_image(True))
	layout.addWidget(infoText, 0, 0, 1, 3)
	layout.addWidget(lastButton, 1, 0)
	layout.addWidget(nextButton, 1, 1)
	layout.addWidget(nextPostButton, 1, 2)
	win.show()
	app.exec_()

def show_image(image=None):
	if not image:
		image = config.post.currentImage()
	if image.path == '':
		updateWallpaperThread = threading.Thread(None, lambda : download_and_show_image(image))
		updateWallpaperThread.start()
	else:
		res = set_wallpaper(image.path)
		config.path = image.path

def prev_image():
	if config.post.image_index > 0:
		print("Previous Image...")
		config.post.image_index -= 1
		show_image()

def interactive():
	from msvcrt import getch
	while True:
		key = ord(getch())
		if key in (3, 113):
			return
		elif key == 100:
			path = input("Enter name(%s):" % os.path.basename(config.post.currentImage().path))
			saveImage(path)
		elif key == 114:
			config.reddit = input('Reddit:')
			config.last = ''
			config.save()
		elif key == 105:
			print_info()
		elif key == 75:
			prev_image()
		elif key == 110:
			next_image(post=True)
		elif key == 77:
			next_image()
		elif key == 224:
			pass
		else:
			print(key)


def print_info():
	print("""Image URL: %s
Local Path: %s
ID: %s
Subreddit: %s""" % (config.post.currentImage().url, config.post.currentImage().path, config.last, config.reddit))

def schedule_intervals():
	print("Scheduled every %s seconds" % config.interval)
	while True:
		next_image()
		time.sleep(config.interval)

if __name__ == '__main__':
	args = sys.argv[1:]
	args = ['-g']
	config = Settings.load()
	args = parse_args(args)
	config.update(args)

	if args.gui:
		gui()
	elif args.control:
		interactive()
	elif args.download:
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