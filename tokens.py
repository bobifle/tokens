#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import requests
import logging
import base64
import zipfile
import uuid
import jinja2
import glob
import difflib
import hashlib
import io
import pickle
import argparse
import itertools
from PIL import Image

# local import
import macros

log = logging.getLogger()

ubase = 'http://dnd5eapi.co/api/'
imglib = '../imglib'

md5Template = '''<net.rptools.maptool.model.Asset>
  <id>
    <id>{{md5}}</id>
  </id>
  <name>{{name}}</name>
  <extension>{{extension}}</extension>
  <image/>
</net.rptools.maptool.model.Asset>'''

args = None

def guid(): 
	return base64.urlsafe_b64encode(uuid.uuid4().bytes)

def dnd5Api(category):
	"""Fetch all category items from the dnd database"""
	items = requests.post(ubase+category+'/').json()
	log.info("Found %s %s" % (items['count'], category))
	for item in items['results']:
		log.info("fetching %s" % item['name'])
		yield requests.get(item['url']).json()

class Token(object):
	sentinel = object()
	def __init__(self, js):
		self.js = js
		# for cached properties
		self._guid = self.sentinel
		self._img = self.sentinel
		self._md5 = self.sentinel

	def __str__(self): 
		return 'Token<name=%s,attr=%s,hp=%s(%s),ac=%s,CR%s,img=%s>' % (self.name, [
			self.strength, self.dexterity, self.constitution, 
			self.intelligence, self.wisdom, self.charisma
			], self.hit_points, self.roll_max_hp, self.armor_class,
			self.challenge_rating, self.img_name)

	# The 2 following methods are use by pickle to serialize a token
	def __getstate__(self): return {'js' : self.js}
	def __setstate__(self, state): 
		self.js = state['js']
		self._guid = self.sentinel
		self._img = self.sentinel
		self._md5 = self.sentinel

	# called when an attribute is not found in the Token instance
	# automatically search for its related item in the json data
	def __getattr__(self, attr):
		v = self.js.get(attr, None)
		if v is None: raise AttributeError("Cannot find the attribute %s" % attr)
		return v

	@property
	def name(self):
		# required otherwise this would later be misinterpreted for a path separator
		return self.js['name'].replace('/', '_')

	@property
	def guid(self):
		return ''
		if self._guid is self.sentinel:
			self._guid = self._guid or guid()
		return self._guid

	@property
	def content_xml(self):
		with open('content.template') as template:
			 t = jinja2.Template(template.read())
			 return t.render(token=self, guid=guid)

	@property
	def properties_xml(self):
		with open('properties.template') as template:
			 t = jinja2.Template(template.read())
			 return t.render()

	@property
	def bcon(self): return (self.constitution-10)/2

	@property
	def roll_max_hp(self): 
		dice, value = map(int, self.hit_dice.split('d'))
		return '%sd%s+%s' % (dice, value, dice*self.bcon)

	@property
	def max_hit_dice(self):
		dice, value = map(int, self.hit_dice.split('d'))
		hd = {'1d12':0, '1d10':0, '1d8':0, '1d6':0}
		hd.update({'1d%s'%value:dice})
		return hd

	@property
	def macros(self): 
		# get optinal macros related to the token actions
		if 'actions' in self.js:
			actions = (macros.getAction(self, action) for action in self.actions)
		else: # XXX some monster like the frog has no 'actions' field
			actions=[]
		return itertools.chain((m for m in actions if m is not None), macros.commons(self))

	@property
	def img(self):
		# try to fetch an appropriate image from the imglib directory
		# using a stupid heuristic: the image / token.name match ratio
		if self._img is self.sentinel: # cache to property
			# compute the diff ratio for the given name compared to the token name
			ratio = lambda name: difflib.SequenceMatcher(None, name.lower(), self.name.lower()).ratio()
			# morph "/abc/def/anyfile.png" into "anyfile"
			short_name = lambda full_path: os.path.splitext(os.path.basename(full_path))[0]
			# list of all img files
			files = glob.glob(os.path.join(os.path.expanduser(imglib), '*.png'))
			bratio=0
			if files:
				# generate the diff ratios
				ratios = ((f, ratio(short_name(f))) for f in files)
				# pickup the best match, it's a tuple (fpath, ratio)
				bfpath, bratio = max(ratios, key = lambda i: i[1])
				log.debug("Best match from the img lib is %s(%s)" % (bfpath, bratio))
			if bratio > 0.8:
				self._img = Image.open(bfpath, 'r') 
			else: 
				self._img = Image.open('dft.png', 'r')
		return self._img

	@property
	def img_name(self): return os.path.splitext(os.path.basename(self.img.filename))[0]

	@property
	def md5(self):
		if self._md5 is self.sentinel: # cache this expensive property
			out = io.BytesIO()
			self.img.save(out, format='png')
			self._md5 = hashlib.md5(out.getvalue()).hexdigest()
		return self._md5
	
	def zipme(self):
		"""Zip the token into a rptok file."""
		with zipfile.ZipFile(os.path.join('build', '%s.rptok'%self.name), 'w') as zipme:
			zipme.writestr('content.xml', self.content_xml.encode('utf-8'))
			zipme.writestr('properties.xml', self.properties_xml)
			log.debug('Token image md5 %s' % self.md5)
			# default image for the token, right now it's a brown bear
			# zip the xml file named with the md5 containing the asset properties
			zipme.writestr('assets/%s' % self.md5, jinja2.Template(md5Template).render(name=self.name, extension='png', md5=self.md5))
			# zip the img itself
			out = io.BytesIO() ; self.img.save(out, format='PNG')
			zipme.writestr('assets/%s.png' % self.md5, out.getvalue())
			# build thumbnails
			out = io.BytesIO()
			im = self.img.copy() ; im.thumbnail((50,50)) ; im.save(out, format='PNG')
			zipme.writestr('thumbnail', out.getvalue())
			out = io.BytesIO()
			im = self.img.copy() ; im.thumbnail((500,500)) ; im.save(out, format='PNG')
			zipme.writestr('thumbnail_large', out.getvalue())

def main():
	parser = argparse.ArgumentParser(description='Process some integers.')
	parser.add_argument('--verbose', '-v', action='count')
	parser.add_argument('--max-token', '-m', type=int)
	global args
	args = parser.parse_args()
	if not os.path.exists('build'): os.makedirs('build')
	pfile = os.path.join('build', 'tokens.pickle')

	if os.path.exists(pfile):
		log.warning('Found serialized Tokens, delete %s to refresh the tokens from %s' % (pfile, ubase))
		with open(pfile, 'r') as fpickle:
			tokens = pickle.load(fpickle)
	else:
		# fetch token using dnd5api on the net
		for category in ['monsters',]:
			tokens = (Token(item) for item in dnd5Api(category))

	sTokens = [] # used for further serialization
	for token in itertools.islice(tokens, args.max_token):
		log.info(token)
		log.info('macros :%s' % list(token.macros))
		token.zipme()
		sTokens.append(token)
	
	# serialize the data if not already done
	if not os.path.exists(pfile):
		with open(pfile, 'w') as fpickle:
			pickle.Pickler(fpickle).dump(sTokens)

if __name__ == '__main__':
	logging.basicConfig(level=logging.INFO)
	main()
