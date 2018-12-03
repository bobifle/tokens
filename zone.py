#!/usr/bin/env python
# -*- coding: utf-8 -*-

#from mtoken import Map
from util import jenv, getLogger, guid

log = getLogger(__name__)

class Zone(object):
	sentinel = object()
	def __init__(self, name):
		self.name = name
		self.tokens = []
		self._guid = self.sentinel

	def __repr__(self): return '%s<%s, %s tokens>' % (self.__class__.__name__, self.name, len(self.tokens))

	@property
	def guid(self):
		if self._guid is self.sentinel: self._guid = guid()
		return self._guid

	@property
	def content_xml(self):
		content = jenv().get_template('zone_content.template').render(zone=self).encode("utf-8")
		return content or ''

	def render(self): return self.content_xml

	def build(self, tokens):
		"""Build a campaign given the tokens, properties all json data."""
		offsets = {"PC": (100,400,50), "Lib": (200, 50,150), "NPC":(100,500,50)}
		by_type = lambda token_list, _type: (t for t in token_list if t.type==_type)
		for _type in offsets:
			for index, tok in enumerate(by_type(tokens, _type)):
				x,y,xscale = offsets[_type]
				line = index/20
				col = index%20
				tok.x = x + (col)*xscale
				tok.y = y + line*100
				log.debug("Placing %s at x=%s y=%s" % (tok, tok.x, tok.y))
		#main_scene = Map()
		#main_scene.name = 'empty_page_blue'
		#main_scene.y = 0
		#main_scene.x=0
		#self.tokens.append(main_scene)
		self.tokens.extend(tokens)
