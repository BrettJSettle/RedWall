from .reddit import getitems
from .reddit_objects import Post, Image

import re, time
import sys

if sys.version.startswith('2'):
	ipnut = raw_input

class RedditScraper():
	def __init__(self, subreddit='images', previd=None, sfw=True, nsfw=False, score=0, title=None, nonimages=False):
		self.subreddit = subreddit
		self.previd = previd
		self.nsfw = nsfw
		self.sfw = sfw
		self.score = score
		self.title = title
		self.nonimages = nonimages

		self.posts = []
		self.post_index = 0

		self._foresight = 5
		self._started = False

	def update(self, name, val, reset=True):
		self.__dict__[name] = val
		if reset:
			if name != self.previd:
				self.previd = ''
			self.posts = []
			self.post_index = 0
			print("Scraping sites in preparation...")
			self.getPosts(3)
			print("READY")
		self.posts = self.posts[:self.post_index+1]

	def __iter__(self):
		return self

	def __next__(self):
		if self._started:
			self.post_index += 1
		else:
			self._started = True
			
		if self.post_index >= len(self.posts) - self._foresight:
			self.getPosts(self.post_index + self._foresight - len(self.posts))
		
		if self.post_index >= len(self.posts):
			return None
		
		return self.posts[self.post_index]

	def next(self):
		return self.__next__()

	def imageIter(self):
		for post in self:
			if post == None:
				yield None
			for image in post.images:
				yield image

	def getPosts(self, count=None):
		
		SKIPPED = 0

		# compile reddit comment url to check if url is one of them
		reddit_comment_regex = re.compile(r'.*reddit\.com\/r\/(.*?)\/comments')

		start_time = time.clock()
		postCount = 0

		while postCount < count:
			ITEMS = getitems(self.subreddit, previd=self.previd)
			
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
					SKIPPED += 1
					continue
				if self.nonimages and 'youtube.com' in ITEM['url'] or ('reddit.com/r/' + self.subreddit + '/comments/' in ITEM['url'] or
						re.match(reddit_comment_regex, ITEM['url']) is not None):
					#print("Skipping non image")
					SKIPPED += 1
					continue
				if self.sfw and ITEM['over_18']:
					#print("Skipping nsfw")
					SKIPPED += 1
					continue
				elif self.nsfw and not ITEM['over_18']:
					#print("Skipping sfw")
					SKIPPED += 1
					continue
				if self.title and self.title.lower() not in ITEM['title'].lower():
					#print("Skipping unrelated")
					SKIPPED += 1
					continue
				if self.score and ITEM['score'] < self.score:
					#print("Skipping low score")
					SKIPPED += 1
					continue
					
				POST = Post(ITEM)
				if not self.nonimages:
					POST.images = [im for im in POST.images if im.url.endswith(('.png', '.jpg', '.jpeg', '.gif'))]

				if len(POST) == 0:
					print("NO images from %s" % POST.url)
					continue

				self.posts.append(POST)
				self.previd = ITEM['id'] if ITEM is not None else None
				postCount += 1

if __name__ == '__main__':
	i = 0
	scraper = RedditScraper('images')
	for image in scraper.imageIter():
		i += 1
		if i > 10:
			break
