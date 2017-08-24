#!/usr/bin/env python2

from __future__ import print_function

import os, re, time, sys, tempfile, threading

if sys.version_info >= (3, 0):
	from urllib.request import urlopen, HTTPError, URLError
	from http.client import InvalidURL
else:
	from urllib2 import urlopen, HTTPError, URLError
	from httplib import InvalidURL

from os.path import (
	exists as pathexists, join as pathjoin, basename as pathbasename,
	splitext as pathsplitext)
from os import mkdir, getcwd
from io import StringIO, BytesIO

from .gfycat import gfycat
from .deviantart import process_deviant_url

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

	if url.endswith(('.jpg', '.png', '.jpeg')):
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
