#!/usr/bin/env python
# -*- coding: utf-8 -*-
import jinja2
import io
import os
import hashlib
import base64
import uuid
from PIL import Image
try:
	import coloredlogs # optional
except ImportError: pass
import logging

# the jinja environment
_jenv = None

# Name of the main logger
lName = 'mtools'
# the main logger
mLog = logging.getLogger(lName)
def getLogger(name):
	return logging.getLogger(lName+'.'+name if lName != name else lName)
# the util sublogger
log = getLogger(__name__)

def configureLogger(verbose):
	"""Configure the loggers, do not call twice."""
	formatter = logging.Formatter('%(name)s : %(levelname)s : %(message)s')
	# logging to the stream, use the colored version if available
	try:
		coloredlogs.DEFAULT_FIELD_STYLES['levelname'] = {'color': 'white'}
		coloredlogs.install(level=logging.DEBUG, fmt='%(name)s %(levelname)8s %(message)s', logger=mLog)
		mLog.handlers[-1].setLevel(logging.WARNING-verbose*10)
	except NameError:
		ch = logging.StreamHandler()
		ch.setLevel(logging.WARNING-verbose*10)
		ch.setFormatter(formatter)
		mLog.addHandler(ch)

	mLog.setLevel(logging.DEBUG) # don't filter anythig let the handlers to the filtering
	if not os.path.exists('logs'): os.makedirs('logs')
	fh = logging.FileHandler(os.path.join('logs', mLog.name+'.log'), mode="w") # mode w will erase previous logs
	fh.setLevel(logging.DEBUG)
	# create formatter and add it to the handlers
	fh.setFormatter(formatter)
	mLog.addHandler(fh)

def jenv():
	"""Return a jinja environment."""
	global _jenv # pylint: disable= W0603
	if _jenv is None:
		_jenv = jinja2.Environment(loader=jinja2.FileSystemLoader(['macros', 'templates']))
		_jenv.filters['json2mt'] = lambda s: s.replace(r"\"", r"\'")
	return _jenv

# a cache for the Images
imgCache = {}

class Img(object):
	"""A PIL.Image higher layer for MT assets."""
	def __init__(self, fp):
		self.fp = fp
		# first try to get the img and byte array from the cache
		img, byteArray = imgCache.get(fp, (None, None))
		if img is None:
			# not in the cache, let's build the img
			_bytes = io.BytesIO()
			img = Image.open(fp)
			img.save(_bytes, format='png')
			byteArray = _bytes.getvalue()
			imgCache[fp] = (img, byteArray)
		# store the byte content, md5 for further use
		self.bytes = byteArray
		self._md5 = hashlib.md5(self.bytes).hexdigest()
		self.x, self.y = img.size

	def resize(self, x,y):
		self.bytes = self.thumbnail(100,100).getvalue()
		self._md5 = hashlib.md5(self.bytes).hexdigest()
		self.x, self.y = x,y

	def __repr__(self): return "Img<%s,%s>" % (os.path.basename(self.fp), self.md5)

	@property
	def name(self): return os.path.splitext(os.path.basename(self.fp))[0]

	@property
	def md5(self): return self._md5

	def thumbnail(self, x,y):
		thumb = io.BytesIO()
		img = Image.open(self.fp)
		img.thumbnail((x,y))
		img.save(thumb, format='png')
		return thumb

def guid():
	"""Return a serialized GUID, it's an uuid4 encoded in base64."""
	return base64.b64encode(uuid.uuid4().bytes)
