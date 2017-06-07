#!/usr/bin/env python2
"""Download images from a reddit.com subreddit."""

from __future__ import print_function

import os
import re
import sys
if sys.version_info >= (3, 0):
	from urllib.request import urlopen, HTTPError, URLError
	from http.client import InvalidURL
else:
	from urllib2 import urlopen, HTTPError, URLError
	from httplib import InvalidURL
from argparse import ArgumentParser
from os.path import (
	exists as pathexists, join as pathjoin, basename as pathbasename,
	splitext as pathsplitext)
from os import mkdir, getcwd
import time
from io import StringIO, BytesIO
import tempfile, threading


from .gfycat import gfycat
from .reddit import getitems
from .deviantart import process_deviant_url

exts = ('.png', '.jpg', '.jpeg')

class Post:
	def __init__(self, ID, url):
		self.id = ID
		self.url = url
		self.images = []
		self.image_index = 0
		self.new = True

	def add_image(self, image):
		if isinstance(image, str):
			image = ImageURL(image)
		if isinstance(image, ImageURL):
			self.images.append(image)
			return True
		return False

	def __str__(self):
		return """Post: %s
ID: %s
Image %d/%d
%s""" % (self.url, self.id, self.image_index+1, len(self.images), str(self.currentImage()))

	def next(self):
		if self.new:
			self.new = False
		else:
			self.image_index += 1
	
		if self.image_index >= len(self.images):
			return False
		return self.images[self.image_index]

	def currentImage(self):
		self.new = False
		if self.image_index >= len(self.images):
			return None
		if os.path.exists(self.images[self.image_index].path):
			return self.images[self.image_index]
		else:
			self.images[self.image_index].path = ''
			self.images[self.image_index].download()
			while self.images[self.image_index].path == '':
				pass
			return self.images[self.image_index]


	def __len__(self):
		return len(self.images)

class ImageURL:
	downloadThread = None
	def __init__(self, url, download=False):
		self.url = url
		self.path = ""
		if download:
			self.download()

	def download(self):
		def download_file():
			fp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
			try:
				download_from_url(self.url, fp)
				self.path = fp.name
			except WrongFileTypeException:
				print("FAILED TO DOWNLOAD")
				pass

		ImageURL.downloadThread = threading.Thread(None, download_file)
		ImageURL.downloadThread.start()

	def removeLocal(self):
		if os.path.exists(self.path):
			try:
				os.remove(self.path)
			except:
				pass
			#print("Removing %s" % self.path)
		self.path = ''

	def __str__(self):
		return "Image URL: %s\nLocal Path: %s" % (self.url, self.path)

def request(url, *ar, **kwa):
	_retries = kwa.pop('_retries', 4)
	_retry_pause = kwa.pop('_retry_pause', 0)
	res = None
	for _try in range(_retries):
		try:
			res = urlopen(url, *ar, **kwa)
		except Exception as exc:
			if _try == _retries - 1:
				raise
			print("Try %r err %r  (%r)" % (_try, exc, url))
		else:
			break
	return res


# '.wrong_type_pages.jsl'
_WRONGDATA_LOGFILE = os.environ.get('WRONGDATA_LOGFILE')


def _log_wrongtype(_logfile=_WRONGDATA_LOGFILE, **kwa):
	if not _logfile:
		return
	import json
	data = json.dumps(kwa) + "\n"
	with open(_logfile, 'a', 1) as f:
		f.write(data)


class WrongFileTypeException(Exception):
	"""Exception raised when incorrect content-type discovered"""


class FileExistsException(Exception):
	"""Exception raised when file exists in specified directory"""

def extract_imgur_album_urls(album_url):
	"""
	Given an imgur album URL, attempt to extract the images within that
	album

	Returns:
		List of qualified imgur URLs
	"""
	response = request(album_url)
	info = response.info()

	# Rudimentary check to ensure the URL actually specifies an HTML file
	if 'content-type' in info and not info['content-type'].startswith('text/html'):
		return []

	filedata = response.read()
	# TODO: stop parsing HTML with regexes.
	match = re.compile(r'\"hash\":\"(.[^\"]*)\",\"title\"')
	items = []

	memfile = StringIO(filedata.decode('utf-8'))
	#print("REALLY LOOKING")
	for line in memfile.readlines():
		results = re.findall(match, line)
		if not results:
			continue

		items += results

	memfile.close()
	# TODO : url may contain gif image.
	urls = ['http://i.imgur.com/%s.jpg' % (imghash) for imghash in items]

	return urls


def download_from_url(url, dest_file):
	"""
	Attempt to download file specified by url to 'dest_file'

	Raises:

		WrongFileTypeException

			when content-type is not in the supported types or cannot
			be derived from the URL

		FileExceptionsException

			If the filename (derived from the URL) already exists in
			the destination directory.

		HTTPError
...
	"""
	# Don't download files multiple times!
	if type(dest_file) == str and pathexists(dest_file):
		raise FileExistsException('URL [%s] already downloaded.' % url)

	response = request(url)
	info = response.info()
	actual_url = response.url
	if actual_url == 'http://i.imgur.com/removed.png':
		raise HTTPError(actual_url, 404, "Imgur suggests the image was removed", None, None)

	# Work out file type either from the response or the url.
	if 'content-type' in info.keys():
		filetype = info['content-type']
	elif url.endswith('.jpg') or url.endswith('.jpeg'):
		filetype = 'image/jpeg'
	elif url.endswith('.png'):
		filetype = 'image/png'
	elif url.endswith('.gif'):
		filetype = 'image/gif'
	elif url.endswith('.mp4'):
		filetype = 'video/mp4'
	elif url.endswith('.webm'):
		filetype = 'video/webm'
	else:
		filetype = 'unknown'

	# Only try to download acceptable image types
	if filetype not in ['image/jpeg', 'image/png', 'image/gif', 'video/webm', 'video/mp4']:
		raise WrongFileTypeException('WRONG FILE TYPE: %s has type: %s!' % (url, filetype))

	filedata = response.read()
	if dest_file == '':
		return

	if type(dest_file) == str:
		filehandle = open(dest_file, 'wb')
	else:
		filehandle = dest_file

	filehandle.write(filedata)

	if type(dest_file) == str:
		filehandle.close()


def process_imgur_url(url):
	"""
	Given an imgur URL, determine if it's a direct link to an image or an
	album.  If the latter, attempt to determine all images within the album

	Returns:
		list of imgur URLs
	"""
	if 'imgur.com/a/' in url or 'imgur.com/gallery/' in url:
		return extract_imgur_album_urls(url)

	# use beautifulsoup4 to find real link
	# find vid url only
	'''
	try:
		print("TRYING AT %s" % url)
		from bs4 import BeautifulSoup
		html = urlopen(url).read()
		soup = BeautifulSoup(html, 'lxml')
		vid = soup.find('div', {'class': 'video-container'})
		vid_type = 'video/webm'  # or 'video/mp4'
		vid_url = vid.find('source', {'type': vid_type}).get('src')
		if vid_url.startswith('//'):
			vid_url = 'http:' + vid_url
		return vid_url

	except Exception:
		# do nothing for awhile
		pass
	'''

	# Change .png to .jpg for imgur urls.
	if url.endswith('.png'):
		url = url.replace('.png', '.jpg')
	else:
		# Extract the file extension
		ext = pathsplitext(pathbasename(url))[1]
		if ext == '.gifv':
			url = url.replace('.gifv', '.gif')
		if not ext:
			# Append a default
			url += '.jpg'
	return [url]

def extract_urls(url):
	"""
	Given an URL checks to see if its an imgur.com URL, handles imgur hosted
	images if present as single image or image album.

	Returns:
		list of image urls.
	"""
	if 'i.imgur.com' in url:
		url = url.replace('i.imgur', 'imgur')

	if url.endswith(exts):
		return [url]
	urls = []

	if 'imgur.com' in url:
		urls = process_imgur_url(url)
	elif 'deviantart.com' in url:
		urls = process_deviant_url(url)
	elif 'gfycat.com' in url:
		# choose the smallest file on gfycat
		gfycat_json = gfycat().more(url.split("gfycat.com/")[-1]).json()
		if gfycat_json["mp4Size"] < gfycat_json["webmSize"]:
			urls = [gfycat_json["mp4Url"]]
		else:
			urls = [gfycat_json["webmUrl"]]
	elif 'wallpapersmicro' in url:
		pass
	else:
		urls = [url]
	return urls



def slugify(value):
	"""
	Normalizes string, converts to lowercase, removes non-alpha characters,
	and converts spaces to hyphens.
	"""
	# taken from http://stackoverflow.com/a/295466
	# with some modification
	import unicodedata
	value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore')
	value = unicode(re.sub(r'[^\w\s-]', '', value).strip())
	# value = re.sub(r'[-\s]+', '-', value) # not replacing space with hypen
	return value


def parse_args(args):
	PARSER = ArgumentParser(description='Downloads files with specified extension'
							'from the specified subreddit.')
	PARSER.add_argument('reddit', metavar='<subreddit>', help='Subreddit name.')

	PARSER.add_argument('--num', metavar='n', default=1000, type=int, required=False,
						help='Number of images to download. Set to 0 to disable the limit')
	PARSER.add_argument('--last', metavar='l', default='', required=False,
						help='ID of the last downloaded file.')
	PARSER.add_argument('--score', metavar='s', default=0, type=int, required=False,
						help='Minimum score of images to download.')
	PARSER.add_argument('--sfw', default=False, action='store_true', required=False,
						help='Download safe for work images only.')
	PARSER.add_argument('--nsfw', default=False, action='store_true', required=False,
						help='Download NSFW images only.')
	PARSER.add_argument('--filename-format', default='reddit', required=False,
						help='Specify filename format: reddit (default), title or url')
	PARSER.add_argument('--title-contain', metavar='TEXT', required=False,
						help='Download only if title contain text (case insensitive)')
	PARSER.add_argument('--non-images', default=False, action='store_true', required=False,
						help='Show results that are not image files')
	PARSER.add_argument('--verbose', default=False, action='store_true',
						required=False, help='Enable verbose output.')

	# TODO fix if regex, title contain activated

	parsed_argument = PARSER.parse_args(args)

	if parsed_argument.sfw is True and parsed_argument.nsfw is True:
		# negate both argument if both argument exist
		parsed_argument.sfw = parsed_argument.nsfw = False

	return parsed_argument


def parse_reddit_argument(reddit_args):
	if '+' not in reddit_args:
		return 'Downloading images from "%s" subreddit' % (reddit_args)
	elif len('Downloading images from "%s" subreddit' % (reddit_args)) > 80:
		# other print format if the line is more than 80 chars
		return 'Downloading images from subreddits:\n{}'.format('\n'.join(reddit_args.split('+')))
	else:
		# print in one line but with nicer format
		return 'Downloading images from "{}" subreddit'.format(', '.join(reddit_args.split('+')))


def get_next_post(reddit, last='', sfw=False, nsfw=False, title='', score=0):

	SKIPPED = 0

	# compile reddit comment url to check if url is one of them
	reddit_comment_regex = re.compile(r'.*reddit\.com\/r\/(.*?)\/comments')

	start_time = time.clock()

	while True:
		ITEMS = getitems(reddit, previd=last)
		# measure time and set the program to wait 4 second between request
		# as per reddit api guidelines
		end_time = time.clock()

		if start_time is not None:
			elapsed_time = end_time - start_time

			if elapsed_time <= 4:  # throttling
				time.sleep(4 - elapsed_time)

		start_time = time.clock()

		if not ITEMS:
			# No more items to process
			print("No more")
			break

		for ITEM in ITEMS:
			if 'youtube.com' in ITEM['url'] or ('reddit.com/r/' + reddit + '/comments/' in ITEM['url'] or
					re.match(reddit_comment_regex, ITEM['url']) is not None):
				#print("Skipping non image")
				SKIPPED += 1
				continue
			if sfw and ITEM['over_18']:
				#print("Skipping nsfw")
				SKIPPED += 1
				continue
			elif nsfw and not ITEM['over_18']:
				#print("Skipping sfw")
				SKIPPED += 1
				continue
			if title and title.lower() not in ITEM['title'].lower():
				#print("Skipping unrelated")
				SKIPPED += 1
				continue
			if score and ITEM['score'] < score:
				#print("Skipping low score")
				SKIPPED += 1
				continue

			POST = Post(ITEM['id'], ITEM['url'])
			try:
				for url in extract_urls(POST.url):
					if url.endswith(exts):
						POST.add_image(url)
			except Exception as e:
				print("Failed to extract urls for %s. %s" % (POST.url, e))
				continue

			if len(POST) == 0:
				print("NO images from %s" % POST.url)
				continue

			return POST

		print("Skipped %d images. ID: %s" % (SKIPPED, last))
		last = ITEM['id'] if ITEM is not None else None


if __name__ == "__main__":
	a = get_next_post("wallpaperdump")
	print(a)
