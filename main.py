from set_wallpaper import set_wallpaper
from reddit_download import next_post, download_from_url
import sys, os, time, threading
import shutil
from argparse import ArgumentParser
from reddit_download import next_post
import pickle
from getch import getch

LEFT = 75
RIGHT = 77
UP = 79
DOWN = 74

updateWallpaperThread = None

class ImagePathExistsError(Exception):
	pass

class Settings:
	def __init__(self):
		self.saveDirectory = ''
		self.reddit = 'wallpapers'
		self.sfw = 0
		self.last = ''
		self.score = 0
		self.title = ''
		self.post = None
		self.interval = 10
		self.path = ''
		self.verbose = False

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

	PARSER.add_argument('-v', '--verbose', action='store_true', required=False, help='With iterating interfaces, display image info on change')

	parsed_argument = PARSER.parse_args(args)

	if parsed_argument.sfw is True and parsed_argument.nsfw is True:
		# negate both argument if both argument exist
		parsed_argument.sfw = parsed_argument.nsfw = False

	return parsed_argument

def save_image(path):
	tmpPath = config.post.currentImage().path
	if os.path.exists(path):
		if os.path.isdir(path):
			resPath = os.path.join(path, os.path.basename(tmpPath))
		else:
			raise ImagePathExistsError()
	else:
		resPath = path
	resPath = os.path.abspath(resPath)
	config.saveDirectory = os.path.dirname(path)
	if config.verbose:
		print('Saving image at %s to %s' % (path, resPath))
	shutil.copyfile(tmpPath, resPath)


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
	image = None

	if not post and config.post:
		image = config.post.next()

	if not image:
		if config.verbose:
			print("New Post...")
		if config.post:
			config.post.currentImage().removeLocal()
		config.post = next_post(config.reddit, last=config.last,
				sfw=config.sfw == 1, nsfw=config.sfw == 2,
				score=config.score, title=config.title)
		config.last = config.post.id
		image = config.post.currentImage()

	if config.verbose:
		print_info()

	show_image(image)

def gui():
	from qtpy import QtCore, QtGui, QtWidgets
	app = QtWidgets.QApplication([])
	win = QtWidgets.QWidget()
	layout = QtWidgets.QGridLayout()
	win.setLayout(layout)
	def nextImagePressed():
		next_image()
		infoText.setText(str(config.post))
	def nextPostPressed():
		next_image(post=True)
		infoText.setText(str(config.post))
	def prevImagePressed():
		prev_image()
		infoText.setText(str(config.post))
	def downloadPressed():
		im = QtWidgets.QFileDialog.getSaveFileName(win, 'Save file as', os.path.join(config.saveDirectory, os.path.basename(config.post.currentImage().path)), '*.jpg')
		if isinstance(im, tuple):
			im = im[0]
		if not im:
			return
		save_image(im)
	infoText = QtWidgets.QLabel(str(config.post))
	lastButton = QtWidgets.QPushButton("<")
	lastButton.pressed.connect(prevImagePressed)
	nextButton = QtWidgets.QPushButton('>')
	nextButton.pressed.connect(nextImagePressed)
	nextPostButton = QtWidgets.QPushButton('>>')
	nextPostButton.pressed.connect(nextPostPressed)
	downloadButton = QtWidgets.QPushButton("Download")
	downloadButton.pressed.connect(downloadPressed)
	layout.addWidget(infoText, 0, 0, 1, 2)
	layout.addWidget(downloadButton, 0, 2)
	layout.addWidget(lastButton, 1, 0)
	layout.addWidget(nextButton, 1, 1)
	layout.addWidget(nextPostButton, 1, 2)
	win.show()
	app.exec_()

def show_image(image=None):
	global updateWallpaperThread
	if not image:
		image = config.post.currentImage()

	if image.path == '':
		updateWallpaperThread = threading.Thread(None, lambda : download_and_show_image(image))
		updateWallpaperThread.start()
	else:
		res = set_wallpaper(image.path)
		config.path = image.path
	config.save()

def prev_image():
	if config.post.image_index > 0:
		config.post.image_index -= 1
		show_image()

	if config.verbose:
		print_info()

def getKey():
	k=getch()
	if ord(k) == 27 and ord(getch()) == 91:
		k = ord(getch())
		return [UP, DOWN, RIGHT, LEFT][k - 65]
	return k

def interactive():
	while True:
		key = getKey()
		if key == 'q':
			return
		elif key == 't':
			path = input("Enter name(%s):" % os.path.basename(config.post.currentImage().path))
			save_image(path)
		elif key == 'r':
			config.reddit = input('Reddit:')
			config.last = ''
			config.save()
		elif key == 'i':
			print_info()
		elif key == LEFT:
			prev_image()
		elif key == 'n':
			next_image(post=True)
		elif key == RIGHT:
			next_image()
		else:
			pass
			#print(key)


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
	#args = ['-g']
	config = Settings.load()
	args = parse_args(args)
	config.update(args)
	
	if not config.reddit:
		raise Exception("No subreddit specified. Use -r [subreddit] to scrape images")

	if args.gui:
		gui()
	elif args.control:
		interactive()
	elif args.download:
		path = args.download
		save_image(path)
	elif args.info:
		print_info()
	elif args.time:
		schedule_intervals()
	else:
		next_image()
		if args.info:
			print_info()
