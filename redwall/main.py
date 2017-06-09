from .set_wallpaper import set_wallpaper
from .reddit_download import get_next_post, download_from_url
from .getch import getch

import sys, os, time, threading
import shutil
from argparse import ArgumentParser
import pickle

LEFT = 75
RIGHT = 77
UP = 79
DOWN = 74

updateWallpaperThread = None

class ImagePathExistsError(Exception):
	pass

class Settings:
	def __init__(self):
		self._reddit = 'wallpaperdump'
		self.sfw = 1
		self.last = ''
		#self.score = 0
		#self.title = ''
		self.verbose = False

		self.saveDirectory = ''
		self.post = None
		self.interval = 10
		self.path = ''

	@property
	def reddit(self):
		return self._reddit

	@reddit.setter
	def reddit(self, value):
		self._reddit = value
		self.post = None
		self.last = ''
		self.save()

	def update(self, args):
		if args.reddit:
			self.reddit = args.reddit
		'''
		args_map = {'score': 'score', 'sfw': 'sfw', 'title_contain': 'title'}
		for k, v in args_map.items():
			ak = getattr(args, k)
			cv = getattr(self, v)
			if ak and cv != av:
				setattr(self, v, ak)
		'''
		self.verbose = args.verbose
		if args.last:
			self.last = args.last

	@staticmethod
	def load(path=None):
		if not path:
			path = os.path.expanduser('~/.redwall.p')
		settings = Settings()
		if os.path.exists(path):
			try:
				settings = pickle.load(open(path, 'rb'))
			except Exception as e:
				print("Failed to load settings. \n%s\nUsing defaults" % e)
		return settings

	def save(self, path=None):
		if not path:
			path = os.path.expanduser('~/.redwall.p')
		return pickle.dump(self, open(path, 'wb'))

	def __str__(self):
		reddit = self.reddit
		return "Subreddit: %s\n%s\n" % (reddit, str(self.post) if self.post else "No Post")

def parse_args(args):
	PARSER = ArgumentParser(description='Downloads files with specified extension'
			'from the specified subreddit.')
	PARSER.add_argument('-r', '--reddit', default=None, help='Subreddit name.', required=False)

	PARSER.add_argument('--last', metavar='l', default='', required=False,
			help='ID of the last downloaded file.')
	#PARSER.add_argument('--score', metavar='s', default='0', type=int, required=False,
	#		help='Minimum score of images to download.')
	PARSER.add_argument('--sfw', default=0, required=False,
			help='SFW level: 0=no preference, 1=sfw, 2=nsfw')
	#PARSER.add_argument('--title-contain', metavar='TEXT', required=False,
	#		help='Download only if title contain text (case insensitive)')
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
	if os.path.isdir(path):
		resPath = os.path.join(path, os.path.basename(tmpPath))
	else:
		resPath = path
	resPath = os.path.abspath(resPath)
	
	if os.path.exists(resPath):
		raise ImagePathExistsError()

	config.saveDirectory = os.path.dirname(path)
	print('Saving image at %s to %s' % (tmpPath, resPath))
	a = shutil.copyfile(tmpPath, resPath)

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
	
def gui():
	from qtpy import QtCore, QtGui, QtWidgets
	app = QtWidgets.QApplication([])
	win = QtWidgets.QWidget()
	layout = QtWidgets.QGridLayout()
	win.setLayout(layout)
	def nextImagePressed():
		infoText.setText("Loading...")
		QtWidgets.QApplication.instance().processEvents()
		next_image()
		showInfo()
	def nextPostPressed():
		infoText.setText("Loading...")
		QtWidgets.QApplication.instance().processEvents()
		next_image(post=True)
		showInfo()
	def prevImagePressed():
		infoText.setText("Loading...")
		QtWidgets.QApplication.instance().processEvents()
		prev_image()
		showInfo()
	def showInfo():
		prevButton.setEnabled(config.post is not None and config.post.image_index != 0)
		infoText.setText("")
	def downloadPressed():
		path = QtWidgets.QFileDialog.getSaveFileName(win, 'Save file as', os.path.join(config.saveDirectory, os.path.basename(config.post.currentImage().path)), '*.jpg')
		if isinstance(path, tuple):
			path = path[0]
		if not path:
			return
		while True:
			try:
				save_image(path)
				break
			except ImagePathExistsError:
				QtWidgets.QMessageBox.question(self, 'Error', 
					 "%s already exists. Overwrite?" % path, QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.No)
				if reply == QtWidgets.QMessageBox.Yes:
					os.remove(path)
					save_image(path)
				else:
					break
	def redditPressed():
		reddit, res = QtWidgets.QInputDialog.getText(win, "Change subreddit", "New subreddit:", text=config.reddit)
		if reddit and res:
			config.reddit = reddit
		show_image()
		showInfo()

	infoButton = QtWidgets.QPushButton("")
	infoText = QtWidgets.QLabel("")
	prevButton = QtWidgets.QPushButton("")
	prevButton.pressed.connect(prevImagePressed)
	nextButton = QtWidgets.QPushButton('')
	nextButton.pressed.connect(nextImagePressed)
	nextPostButton = QtWidgets.QPushButton('')
	nextPostButton.pressed.connect(nextPostPressed)
	downloadButton = QtWidgets.QPushButton("")
	downloadButton.pressed.connect(downloadPressed)
	redditButton = QtWidgets.QPushButton("Sub(s)")
	redditButton.pressed.connect(redditPressed)
	prevButton.setEnabled(config.post is not None and config.post.image_index != 0)

	icon = QtGui.QIcon(os.path.join(os.path.dirname(__file__), "images/prev.png"))
	prevButton.setIcon(icon)
	icon = QtGui.QIcon(os.path.join(os.path.dirname(__file__), "images/next.png"))
	nextButton.setIcon(icon)
	icon = QtGui.QIcon(os.path.join(os.path.dirname(__file__), "images/nextPost.png"))
	nextPostButton.setIcon(icon)
	icon = QtGui.QIcon(os.path.join(os.path.dirname(__file__), "images/download.png"))
	downloadButton.setIcon(icon)
	icon = QtGui.QIcon(os.path.join(os.path.dirname(__file__), "images/info.png"))
	infoButton.setIcon(icon)

	def showLabel():
		win.panel = QtWidgets.QWidget()
		win.panel.label = QtWidgets.QLabel(str(config))
		#win.panel.label.setReadOnly(True)
		win.panel.label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
		layout = QtWidgets.QGridLayout()
		win.panel.setLayout(layout)
		layout.addWidget(win.panel.label)
		layout.setContentsMargins(10, 10, 10, 10)
		win.panel.show()

	infoButton.pressed.connect(showLabel)

	layout.addWidget(infoButton, 0, 0, 1, 2)
	layout.addWidget(infoText, 1, 0, 1, 2)
	layout.addWidget(downloadButton, 0, 2)
	layout.addWidget(redditButton, 1, 2)
	layout.addWidget(prevButton, 2, 0)
	layout.addWidget(nextButton, 2, 1)
	layout.addWidget(nextPostButton, 2, 2)
	win.show()
	app.exec_()

def show_image(image=None):
	global updateWallpaperThread
	if not image:
		if not config.post:
			image = next_image()
			return
		image = config.post.currentImage()

	if image.path == '':
		#updateWallpaperThread = threading.Thread(None, lambda : download_and_show_image(image))
		#updateWallpaperThread.start()
		return download_and_show_image(image)
	else:
		res = set_wallpaper(image.path)
		config.path = image.path
		if config.verbose:
			print_info()
	config.save()

def next_image(post=False):
	image = None

	if not post and config.post:
		if config.post.currentImage():
			config.post.currentImage().removeLocal()
		
		image = config.post.next()

	if not image:
		return next_post()
	else:
		if config.verbose:
			print("New Image...")

	show_image(image)


def next_post():
	if config.verbose:
		print("New Post...")
	if config.post and config.post.currentImage():
		config.post.currentImage().removeLocal()

	config.post = get_next_post(config.reddit, last=config.last,
			sfw=config.sfw == 1, nsfw=config.sfw == 2)#,
			#score=config.score, title=config.title)
	config.last = config.post.id
	image = config.post.currentImage()

	show_image(image)
	return image


def prev_image():
	if config.post and config.post.image_index > 0:
		if config.post.currentImage():
			config.post.currentImage().removeLocal()
		config.post.image_index -= 1
		show_image()

def getKey():
	k=getch()
	k = chr(ord(k))
	if k == 'à':
		k = chr(ord(getch()))
	return k.lower()

def interactive():
	help_text = '''
Interactive Mode
Keys:
 d - Next Image in Post
 a - Previous Image in Post
 n - Next Post
 i - Post/Image Information
 s - Save Image Locally
 r - Enter a new subreddit to scrape
 h - Display they help
 q - Quit
'''
	un = 0
	print(help_text)
	while True:
		key = getKey()
		if key == 'q':
			return
		elif key == 's':
			path = input("Enter name(%s):" % os.path.basename(config.post.currentImage().path))
			if path.strip() == '':
				path = os.path.basename(config.post.currentImage().path)
			while True:
				try:
					save_image(path.strip())
					break
				except ImagePathExistsError:
					res = input("%s already exists. Overwrite (y/n)?" % path)
					if res == 'y':
						os.remove(path)
						save_image(path)
					else:
						break
		elif key == 'r':
			config.reddit = input('Reddit:')
			config.save()
		elif key == 'i':
			print_info()
		elif key == 'a':
			prev_image()
		elif key == 'n':
			next_image(post=True)
		elif key == 'd':
			next_image()
		elif key == 'h':
			print(help_text)
		elif key == 'q':
			break
		else:
			print("Unkown key %s" % key)
			un += 1
			if un > 5:
				print("Key unrecognized 5 times. Quitting")
				return
			#print(key)


def print_info():
	print(str(config.post))

def schedule_intervals():
	print("Scheduled every %s seconds" % config.interval)
	while True:
		next_image()
		time.sleep(config.interval)

def main():
	global config
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
		while True:
			try:
				save_image(path.strip())
				break
			except ImagePathExistsError:
				res = input("%s already exists. Overwrite (y/n)?" % path)
				if res == 'y':
					os.remove(im)
					save_image(im)
				else:
					break
	elif args.info:
		print_info()
	elif args.time:
		schedule_intervals()
	else:
		next_image()


if __name__ == '__main__':
	config = None
	main()
