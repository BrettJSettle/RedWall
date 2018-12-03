from .url_util import extract_urls, download_from_url

import threading, tempfile, os, sys, time
if sys.version_info >= (3, 0):
	from urllib.request import HTTPError
else:
	from urllib2 import HTTPError


class WrongFileTypeException(Exception):
	"""Exception raised when incorrect content-type discovered"""

class Post:
	def __init__(self, info):
		self.subreddit = info['subreddit']
		self.title = info['title'] if 'title' in info else 'No Title'
		self.url = info['url']
		self.id = info['id']
		self.permalink = info['permalink']
		self.images = []
		urls = []
		for url in extract_urls(self.url):
			if url in urls:
				continue
			urls.append(url)
			self.images.append(Image(self, url))
		self.next_index = 0

	def __getitem__(self, i):
		return self.images[i]

	def __str__(self):
		return """
Title: %s
Post: http://reddit.com%s
ID: %s
Image %d/%d
%s
""" % (self.title, self.permalink, self.id, self.next_index+1, len(self.images), str(self.peek()))

	def __iter__(self):
		for image in self.images:
			yield image
			self.next_index += 1

	def peek(self):
		if self.next_index - 1 >= len(self.images):
			return None
		return self.images[max(0, self.next_index - 1)]

	def __len__(self):
		return len(self.images)

class Image:
	def __init__(self, post, url):
		self.post = post
		self.url = url
		self.path = ""

	def download(self, limit=5):
		if self.path and os.path.exists(self.path):
			return self.path
		def download_file():
			fp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
			try:
				download_from_url(self.url, fp)
				self.path = fp.name
			except WrongFileTypeException:
				self.path = None
				print("File is incorrect filetype to set as wallpaper")
			except HTTPError:
				self.path = None
				print("HTTPError on download")


		self.downloadThread = threading.Thread(None, download_file)
		self.downloadThread.start()
		s = time.time()
		while self.path == '':
			if (time.time() - s > limit):
				print("Took too long to download")
				break
			pass
		return self.path


	def removeLocal(self):
		if not self.path:
			return
		if os.path.exists(self.path):
			try:
				os.remove(self.path)
			except Exception as e:
				print("Failed to remove. %s" % e)
				pass
		else:
			print("%s does not exist" % self.path)
		self.path = ''

	def __str__(self):
		s ="Image URL: %s" % self.url
		if self.path:
			s += "\nLocal Path: %s" % self.path
		return s
