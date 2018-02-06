import os, random, configparser, requests, json, re, time, pickle, sys, tempfile
from collections import OrderedDict
from .reddit import getitems
from .url_util import extract_urls, download_from_url
from set_wallpaper import set_wallpaper

__all__ = ['Signal', 'FlickrSearchScraper', 'FlickrProfileScraper', 'SubredditScraper', 'SCRAPER_TYPES', 'ScraperSession', 'AbstractScraper']

def unjsonpify(jsonp):
	return jsonp[14:-1]  # totally hacky strip off jsonp func

def random_choice(weights):
	l = []
	for i, count in enumerate(weights):
		l.extend([i] * count)
	return random.choice(l)

class Signal():
	def __init__(self):
		self.links = []

	def connect(self, l):
		self.links.append(l)

	def fire(self, *args, **kargs):
		for l in self.links:
			l(*args, **kargs)


class ImageScrapeError(Exception):
	def __init__(self, s):
		Exception.__init__(self, s)

class AbstractScraper:
	ScraperValidityChanged = Signal()
	DEFAULT_ARGUMENTS = {}
	def __init__(self, name):
		self._name = name
		self._invalid = False
		self.options = self.__class__.DEFAULT_ARGUMENTS.copy()

	@property
	def invalid(self):
		return self._invalid

	@invalid.setter
	def invalid(self, iv):
		if iv != self._invalid:
			self._invalid = iv
			self.ScraperValidityChanged.fire(scraper=self, invalid=iv)

	@property
	def name(self):
		return self._name

	@staticmethod
	def newScraper():
		raise NotImplementedError()

	@name.setter
	def name(self, name):
		self._name = name

	def __str__(self):
		return self._name

	def __iter__(self):
		return self

	def __next__(self):
		raise NotImplementedError()

	def getState(self):
		raise NotImplementedError()


class FlickrAPI():
	FLICKR_API_KEY = None
	REST_ENDPOINT = 'https://api.flickr.com/services/rest/'
	def __init__(self):
		config = configparser.ConfigParser()
		config.read(['flickr.ini'])
		FlickrAPI.FLICKR_API_KEY = config.get('flickr', 'api_key')

	@staticmethod
	def reload():
		config = configparser.ConfigParser()
		config.read(['flickr.ini'])
		FlickrAPI.FLICKR_API_KEY = config.get('flickr', 'api_key')

	@staticmethod
	def request(**kwargs):
		response = requests.get(FlickrAPI.REST_ENDPOINT, params=dict(
				api_key=FlickrAPI.FLICKR_API_KEY,
				format='json',
				nojsoncallback=1,
				content_type=1,
				**kwargs), timeout=2)
		data = response.json()
		if data['stat'] != 'ok':
			if (data['code'] == 100):
				FlickrAPI.reload()
			raise Exception('Failed to parse response from Flickr API. Code %s: %s' % (data['code'], data['message']))
		return data

	@staticmethod
	def getImageUrl(photo):
		output = 'flickr/'
		prefix = "http://farm{farm}.staticflickr.com/{server}/"
		suffix = "{id}_{secret}_b.jpg"
		template = prefix + suffix
		url = template.format(**photo)
		return url

class FlickrProfileScraper(AbstractScraper, FlickrAPI):
	DEFAULT_ARGUMENTS = OrderedDict([('username', ''),])
	def __init__(self, username):
		AbstractScraper.__init__(self, "Flickr Profile " + username)
		FlickrAPI.__init__(self)
		self.options['username'] = username
		self._nsid = FlickrProfileScraper.getNSIDforUsername(username)
		self.photos = []
		self._page = 1
		self._index = 0
		self._current_image = None
		self.get_photos_for_person()

	def getState(self):
		return "%s page %d (%d/%d)" % (self._name, self._page, self._index, len(self.photos))

	@staticmethod
	def newScraper():
		username = input("Username: ")
		scraper = FlickrProfileScraper(username)
		return scraper

	def get_photos_for_person(self):
		response = self.request(method='flickr.people.getPhotos', user_id=self._nsid, page=self._page)

		pages = response['photos']['pages']
		if self._page > pages:
			self._page = 0

		self.photos = response['photos']['photo']

	@staticmethod
	def getNSIDforUsername(username):
		data = FlickrAPI.request(method='flickr.people.findByUsername', username=username)
		if data['stat'] == 'ok':
				return data['user']['nsid']
		return None

	def __next__(self):
		if self._index >= len(self.photos):
			self._page += 1
			self._index = 0
			self.get_photos_for_person()

		if self._index >= len(self.photos):
			print("%d out of range %d" % (self._index, len(self.photos)))
			self._index = 0
			self._page = 0
			self.photos = []
			return next(self)

		photo = self.photos[self._index]
		self._index += 1
		url = FlickrAPI.getImageUrl(photo)
		self._current_image = photo
		photo['url'] = url
		return photo

class FlickrSearchScraper(AbstractScraper, FlickrAPI):
	PAGE_SIZE = 500
	DEFAULT_ARGUMENTS = OrderedDict([('keyword', ''),])
	def __init__(self, keyword, safe_search=1, sort='relevance'):
		AbstractScraper.__init__(self, "Flickr Search " + keyword)
		FlickrAPI.__init__(self)
		self.options.update({'keyword': keyword, 'safe_search': safe_search, 'sort': sort})
		self.photos = []
		self._page = 0
		self._index = 0

	def getState(self):
		return "%s page %d (%d/%d)" % (self._name, self._page, self._index, len(self.photos))

	@staticmethod
	def newScraper():
		keyword = input('Keyword: ')
		return FlickrSearchScraper(keyword)


	def scrape(self):
		params = {'text': self.options['keyword'],
							'safe_search': self.options['safe_search'],  # safest
							'media': 'photos',  # just photos
							'privacy_filter': '1',  # public photos
							'license': '1,2,4,5',  # see README.md
							'per_page': str(self.PAGE_SIZE),  # max=500
							'page': str(self._page),
							'sort': self.options['sort'],
							'method': 'flickr.photos.search'}
		query_dict = {'text': self.options['keyword']}
		clean_query = self.options['keyword'].replace(' ', '-')
		result = self.request(**params)
		if result['stat'] != 'ok':
			raise ImageScrapeError("Flickr API search failed.")
		photos = result['photos']
		photos = photos['photo']
		return photos

	def __next__(self):
		if self._index >= len(self.photos):
			self._index = 0
			self._page += 1
			self.photos = self.scrape()

		if self._index >= len(self.photos):
			raise ImageScrapeError("Unable to find images for search")

		photo = self.photos[self._index]
		self._index += 1
		photo['url'] = FlickrAPI.getImageUrl(photo)

		self._current_image = photo
		return photo

class RedditPost():
	def __init__(self, data):
		self.data = data
		self.urls = []
		self.extract_image_urls()

	def __len__(self):
		return len(self.urls)

	def __getitem__(self, i):
		if isinstance(i, int):
			return self.urls[i]
		elif i in self.data:
			return self.data[i]

	def extract_image_urls(self):
		urls = []
		for u in extract_urls(self.data['url']):
			if u.endswith(('.png', '.jpg', '.jpeg', '.gif')):
				urls.append({'url': u})
		self.urls = urls

class SubredditScraper(AbstractScraper):
	DEFAULT_ARGUMENTS = OrderedDict([('subreddit', 'wallpapers'), ('sfw', True), ('nsfw', False), ('score', 0), ('title', '')])
	def __init__(self, subreddit, sfw=True, nsfw=False, score=0, title=''):
		AbstractScraper.__init__(self, "Subreddit " + subreddit)
		options = {'subreddit': subreddit, 'sfw': sfw, 'nsfw':nsfw, 'score': score, 'title': title}
		self.options.update(options)

		self.current_post = None
		self.posts = []
		self.postNum = 0
		self._index = 0

	@staticmethod
	def newScraper():
		sub = input('Subreddit: ')
		return SubredditScraper(sub)

	def getState(self):
		return self._name if self.current_post == None else "%s post %d (%d/%d)" % (self._name, self.postNum, self._index, len(self.current_post))

	def __iter__(self):
		return self

	def __next__(self):
		if self.current_post == None or self._index >= len(self.current_post):
			self._index = 0
			if len(self.posts) == 0:
				self.getPosts()
			if len(self.posts) == 0:
				raise ImageScrapeError("No images returned from scrape")
			self.current_post = RedditPost(self.posts.pop(0))
			self.postNum += 1

		if len(self.current_post) == 0:
			return next(self)

		img = self.current_post[self._index]
		self._index += 1
		return img

	def getPosts(self):
		SKIPPED = 0
		# compile reddit comment url to check if url is one of them
		reddit_comment_regex = re.compile(r'.*reddit\.com\/r\/(.*?)\/comments')

		start_time = time.clock()

		previd = None
		if len(self.posts) > 0:
			previd = self.posts[-1]['id']
		elif self.current_post is not None:
			previd = self.current_post['id']

		while len(self.posts) < 10 and SKIPPED < 30:
			ITEMS = getitems(self.options['subreddit'], previd=previd)
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
				print("No posts could be loaded at this time")
				break

			for ITEM in ITEMS:
				if 'dropbox.com' in ITEM['url']:
					print("Skipping dropbox items")
					SKIPPED += 1
					continue
				if 'youtube.com' in ITEM['url'] or ('reddit.com/r/' + self.options['subreddit'] + '/comments/' in ITEM['url'] or
						re.match(reddit_comment_regex, ITEM['url']) is not None):
					print("Skipping non image")
					SKIPPED += 1
					continue
				if 'over_18' in ITEM:
					if not self.options['nsfw'] and self.options['sfw'] and ITEM['over_18']:
						print("Skipping nsfw")
						SKIPPED += 1
						continue
					elif not self.options['sfw'] and self.options['nsfw'] and not ITEM['over_18']:
						print("Skipping sfw")
						SKIPPED += 1
						continue
				if self.options['title'] and self.options['title'].lower() not in ITEM['title'].lower():
					print("Skipping unrelated")
					SKIPPED += 1
					continue

				if 'score' in ITEM and self.options['score'] and ITEM['score'] < int(self.options['score']):
					print("Skipping low score")
					SKIPPED += 1
					continue

				previd = ITEM['id'] if ITEM is not None else None
				self.posts.append(ITEM)

class ScraperSession:
	ImageChanged = Signal()
	def __init__(self, scrapers=[]):
		self.scrapers = scrapers
		self.weights = {s: 1 for s in scrapers}

		self._current_scraper = None
		self._history = []
		self._current_image = None
		self._current_url = ''

	def screensaver(self, interval):
		val = int(interval)
		while 1:
			time.sleep(val)
			self.nextWallpaper()

	def setWeight(self, scraper, w):
		if scraper in self.weights:
			self.weights[scraper] = w

	@staticmethod
	def fromFile(fname):
		obj = None
		with open(fname, 'rb') as inf:
			obj = pickle.loads(inf.read())
		return obj

	def addScraper(self, scraper, weight=1):
		self.scrapers.append(scraper)
		self.weights[scraper] = weight

	def getState(self):
		return self._current_scraper.getState()

	def __iter__(self):
		return self

	def __next__(self):
		old_scraper = self._current_scraper

		image = None
		scraper = None
		attempts = 0

		while image is None:
			if len(self.scrapers) == 0:
				raise Exception("No scrapers available")

			if scraper is None:
				attempts = 0
				scrapers = [s for s in self.scrapers if not s.invalid]
				opts = [self.weights[s] for s in self.scrapers if not s.invalid]
				if sum(opts) == 0:
					raise Exception("At least one scraper must have a nonzero weight")
				ID = random_choice(opts)

				scraper = scrapers[ID]

				print("Scraping from %s" % scraper)
				invalid = False

			try:
				image = next(scraper)
				if image is None:
					raise ImageScrapeError("No image returned by scraper")
			except NotImplementedError:
				print("%s has not implemented a read function" % scraper)
				invalid = True
			except ImageScrapeError as e:
				print("Attempt %d of 4. Failed to scrape %s: %s. Trying again..." % (attempts, scraper, e))
				attempts += 1
				invalid = attempts > 3
			if invalid:
				#self.scrapers.remove(scraper)
				scraper.invalid = True
				scraper = None
			else:
				self._current_scraper = scraper

		self._history.append(image)
		self._current_image = image

		self.ImageChanged.fire(old_scraper, self._current_scraper)
		return image

	def nextWallpaper(self):
		wallpaper = next(self)

		self.setWallpaperFromURL(wallpaper['url'])
		return wallpaper

	def setWallpaperFromURL(self, url):
		if self._current_url and os.path.exists(self._current_url):
			os.remove(self._current_url)

		temp_url = tempfile.mkstemp(".jpg")
		temp_url = temp_url[1]

		if os.path.exists(temp_url):
			os.remove(temp_url)

		print("Saving %s to %s" % (url, temp_url))
		download_from_url(url, temp_url)

		set_wallpaper(temp_url, True)
		self._current_url = temp_url

	def save(self, f):
		with open(f, 'wb') as outf:
			pickle.dump(self, outf)

	def removeScraper(self, scraper):
		if scraper not in self.scrapers:
			return False
		self.scrapers.remove(scraper)
		print("Removed %s" % scraper)
		del self.weights[scraper]
		return True

SCRAPER_TYPES = [SubredditScraper, FlickrProfileScraper, FlickrSearchScraper]
