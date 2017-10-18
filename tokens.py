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
from PIL import Image

log = logging.getLogger()

ubase = 'http://dnd5eapi.co/api/'
imglib = '~/nobackup/perso/vamp/charSheet/maptool/imglib'

md5Template = '''<net.rptools.maptool.model.Asset>
  <id>
    <id>{{md5}}</id>
  </id>
  <name>{{name}}</name>
  <extension>{{extension}}</extension>
  <image/>
</net.rptools.maptool.model.Asset>'''


def guid(): 
	return base64.urlsafe_b64encode(uuid.uuid4().bytes)

def fetch(category):
	"""Fetch all category items from the dnd database"""
	items = requests.post(ubase+category+'/').json()
	log.info("Found %s %s" % (items['count'], category))
	slist = []
	for item in items['results']:
		log.info("fetching %s" % item['name'])
		slist.append(requests.get(item['url']).json())
		break # XXX remove
	return slist

class Macro(object):
	def __init__(self, label, command):
		self._command = command
		self._label = label

	@property
	def command(self): return self._command

	@property
	def label(self): return self._label

	@property
	def group(self): return 'Health' # TODO handler more than one group

	@property
	def color(self): return {'Health' : 'green'}[self.group]

common = [
	Macro('Potion of Healing', '''[h:Flavor=token.name+" FLAVOR TEXT HERE"]

[h:FlavorData = json.set("",
	"Flavor",Flavor,
	"ParentToken",currentToken())]

[macro("Potion of Healing@Lib:Melek") : FlavorData]'''
	)
]

sentinel = object()

class Token(object):
	def __init__(self, js):
		self.js = js
		self._guid = None
		self._img = sentinel

	def __str__(self): 
		return 'Token<name=%s,attr=%s,hp=%s(%s),ac=%s,CR%s>' % (self.name, [
			self.strength, self.dexterity, self.constitution, 
			self.intelligence, self.wisdom, self.charisma
			], self.hit_points, self.roll_max_hp, self.armor_class,
			self.challenge_rating)

	# called when an attribute is not found in the Token instance
	# automatically search for its related item in the json data
	def __getattr__(self, attr):
		v = self.js.get(attr, None)
		if v is None: raise AttributeError("Cannot find the attribute %s" % attr)
		return v

	@property
	def guid(self):
		return ''
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
	def macros(self): return common # TODO add more macros

	@property
	def img(self):
		# try to fetch an appropriate image from the imglib directory
		# using a stupid heuristic: the image / token.name match ratio
		if self._img is sentinel:
			# compute the diff ratio for the given name compared to the token name
			ratio = lambda name: difflib.SequenceMatcher(None, name.lower(), self.name.lower()).ratio()
			# morph "/abc/def/anyfile.png" into "anyfile"
			short_name = lambda full_path: os.path.splitext(os.path.basename(full_path))[0]
			# list of all img files
			files = glob.glob(os.path.join(os.path.expanduser(imglib), '*.png'))
			# generate the diff ratios
			ratios = ((f, ratio(short_name(f))) for f in files)
			# pickup the best match, it's a tuple (fpath, ratio)
			bfpath, bratio = max(ratios, key = lambda i: i[1])
			log.debug("Best match from the img lib is %s(%s)" % (bfpath, bratio))
			if bratio > 0.8:
				log.info("Found a suitable image %s" % bfpath)
				self._img = Image.open(bfpath, 'r') 
			else: 
				log.info("No suitable image found for the token, using the brown bear")
				self._img = Image.open('dft.png', 'r')
		return self._img

	def zipme(self):
		"""Zip the token into a rptok file."""
		with zipfile.ZipFile(os.path.join('build', '%s.rptok'%self.name), 'w') as zipme:
			zipme.writestr('content.xml', self.content_xml)
			zipme.writestr('properties.xml', self.properties_xml)
			out = io.BytesIO()
			self.img.save(out, format='png')
			md5 = hashlib.md5(out.getvalue()).hexdigest()
			log.debug('Token image md5 %s' % md5)
			# default image for the token, right now it's a brown bear
			# zip the xml file named with the md5 containing the asset properties
			zipme.writestr('assets/%s' % md5, jinja2.Template(md5Template).render(name=self.name, extension='png', md5=md5))
			# zip the img itself
			zipme.writestr('assets/%s.png' % md5, out.getvalue())
			# build thumbnails
			out = io.BytesIO()
			im = self.img.copy() ; im.thumbnail((50,50)) ; out.seek(0); im.save(out, format='PNG')
			zipme.writestr('thumbnail', out.getvalue())
			out = io.BytesIO()
			im = self.img.copy() ; im.thumbnail((500,500)) ; out.seek(0); im.save(out, format='PNG')
			zipme.writestr('thumbnail_large', out.getvalue())

def main():
	for category in ['monsters',]:
		for token in (Token(item) for item in fetch(category)):
			log.info(token)
			token.zipme()

if __name__ == '__main__':
	logging.basicConfig(level=logging.INFO)
	main()
