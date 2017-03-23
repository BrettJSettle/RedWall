import numpy as np
import pandas as pd

ratings = pd.read_pickle('ratings.txt')

from glob import glob
from PIL import Image
import requests
from io import BytesIO
from skimage import io
import os

def preprocess(im):
	if im.shape[2] == 4:
		im = im[:, :, :3]

	im_BRG = im[2], im[0], im[1]
	# Note this was NOT a transposition, as the dimensions 
	# stays ordered the same in the np array.

	# For the mean normalisation, you could do: 
	mean = np.mean(im_BRG)
	im_BRG -= mean
	return im_BRG

ratings['image'] = [None] * len(ratings['url'])

for i in range(len(ratings['url'])):
	continue
	url = ratings['url'][i]
	response = requests.get(url)
	img = Image.open(BytesIO(response.content))
	ratings['image'] = preprocess(np.array(img))

other_dirs = ['C:\\Users\\Brett\\OneDrive\\Pictures\\Wallpapers', 'C:\\Users\\Brett\\OneDrive\\Pictures\\Old Wallpapers']

for d in other_dirs:
	for f in glob(d + "\\*"):
		if f.endswith('db'):
			continue
		if not os.path.exists(f):
			print("File not found: %s" % f)
			continue
		img = io.imread(f)
		ratings = ratings.append(pd.DataFrame([[1, f, preprocess(img)]], columns= ['rating', 'url', 'image']))
		#print(f, img.shape)

print(ratings)