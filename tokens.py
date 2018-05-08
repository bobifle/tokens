#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import json
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
imglibs = [
  '../imglib',
  r'C:\sources\dnd5\Monster Manual Roll20 Tokens',
]

md5Template = '''<net.rptools.maptool.model.Asset>
  <id>
    <id>{{md5}}</id>
  </id>
  <name>{{name}}</name>
  <extension>{{extension}}</extension>
  <image/>
</net.rptools.maptool.model.Asset>'''

args = None

monsters = [
	{
		u'name': u'Aarakocra', 
		u'size': u'Medium', 
		u'type': u'humanoid', 
		u'alignment': u'neutral good', 
		u'armor_class': 12, 
		u'hit_points': 13, 
		u'hit_dice': u'3d8', 
		u'speed': u'20 ft., fly 50 ft.', 
		u'strength': 10, 
		u'dexterity': 14,
		u'constitution': 10, 
		u'intelligence': 11,
		u'wisdom_save': 12,
		u'charisma': 11, 
		u'perception': '+5', 
		u'constitution_save': 0, 
		u'intelligence_save': 0, 
		u'actions': [{u'attack_bonus': 0, u'name': u'Multiattack', u'desc': u'The aboleth makes three tentacle attacks.'}, {u'damage_dice': u'2d6', u'damage_bonus': 5, u'attack_bonus': 9, u'name': u'Tentacle', u'desc': u"Melee Weapon Attack: +9 to hit, reach 10 ft., one target. Hit: 12 (2d6 + 5) bludgeoning damage. If the target is a creature, it must succeed on a DC 14 Constitution saving throw or become diseased. The disease has no effect for 1 minute and can be removed by any magic that cures disease. After 1 minute, the diseased creature's skin becomes translucent and slimy, the creature can't regain hit points unless it is underwater, and the disease can be removed only by heal or another disease-curing spell of 6th level or higher. When the creature is outside a body of water, it takes 6 (1d12) acid damage every 10 minutes unless moisture is applied to the skin before 10 minutes have passed."}, {u'damage_dice': u'3d6', u'damage_bonus': 5, u'attack_bonus': 9, u'name': u'Tail', u'desc': u'Melee Weapon Attack: +9 to hit, reach 10 ft. one target. Hit: 15 (3d6 + 5) bludgeoning damage.'}, {u'attack_bonus': 0, u'name': u'Enslave (3/day)', u'desc': u"The aboleth targets one creature it can see within 30 ft. of it. The target must succeed on a DC 14 Wisdom saving throw or be magically charmed by the aboleth until the aboleth dies or until it is on a different plane of existence from the target. The charmed target is under the aboleth's control and can't take reactions, and the aboleth and the target can communicate telepathically with each other over any distance.\nWhenever the charmed target takes damage, the target can repeat the saving throw. On a success, the effect ends. No more than once every 24 hours, the target can also repeat the saving throw when it is at least 1 mile away from the aboleth."}], 
		u'damage_resistances': u'', 
		u'languages': 
		u'Deep Speech, telepathy 120 ft.',
		u'damage_vulnerabilities': u'',
		u'senses': u'darkvision 120 ft., passive Perception 20',
		u'wisdom': 15, 
		u'special_abilities': [{u'attack_bonus': 0, u'name': u'Amphibious', u'desc': u'The aboleth can breathe air and water.'}, {u'attack_bonus': 0, u'name': u'Mucous Cloud', u'desc': u'While underwater, the aboleth is surrounded by transformative mucus. A creature that touches the aboleth or that hits it with a melee attack while within 5 ft. of it must make a DC 14 Constitution saving throw. On a failure, the creature is diseased for 1d4 hours. The diseased creature can breathe only underwater.'}, {u'attack_bonus': 0, u'name': u'Probing Telepathy', u'desc': u"If a creature communicates telepathically with the aboleth, the aboleth learns the creature's greatest desires if the aboleth can see the creature."}], 
		u'condition_immunities': u'', 
		u'damage_immunities': u'', 
		u'legendary_actions': [{u'attack_bonus': 0, u'name': u'Detect', u'desc': u'The aboleth makes a Wisdom (Perception) check.'}, {u'attack_bonus': 0, u'name': u'Tail Swipe', u'desc': u'The aboleth makes one tail attack.'}, {u'attack_bonus': 0, u'name': u'Psychic Drain (Costs 2 Actions)', u'desc': u'One creature charmed by the aboleth takes 10 (3d6) psychic damage, and the aboleth regains hit points equal to the damage the creature takes.'}], 
		u'challenge_rating': 10, 
	},
]


def guid(): 
	return base64.urlsafe_b64encode(uuid.uuid4().bytes)

def dnd5Api(category):
	"""Fetch all category items from the dnd database"""
	items = requests.post(ubase+category+'/').json()
	log.info("Found %s %s" % (items['count'], category))
	for item in items['results']:
		log.info("fetching %s" % item['name'])
		yield requests.get(item['url']).json()
	
class State(object):
	def __init__(self, name, value):
		self.name = name
		self.value = value

class Prop(object):
	def __init__(self, name, value):
		self.name = name
		self.value = value
	def __repr__(self): return '%s<%s,%s>' % (self.__class__.__name__, self.name, self.value)
	def render(self):
		return jinja2.Template('''      <entry>
        <string>{{prop.name.lower()}}</string>
        <net.rptools.CaseInsensitiveHashMap_-KeyValue>
          <key>{{prop.name}}</key>
          <value class="string">{{prop.value}}</value>
          <outer-class reference="../../../.."/>
        </net.rptools.CaseInsensitiveHashMap_-KeyValue>
      </entry>''').render(prop=self)

class Dnd5ApiObject(object):
	sfile_name = 'nofile.pickle' # filename used for serialization
	category = 'unknown'

	@classmethod
	def load(cls, build_dir):
		items = None
		fp = os.path.join(build_dir, cls.sfile_name)
		if os.path.exists(fp):
			log.warning('Found serialized %ss, delete %s to refresh the items from %s' % (cls.__name__, fp, ubase))
			with open(fp, 'r') as fpickle:
				items = pickle.load(fpickle)
		return iter(items) if items else (cls(item) for item in dnd5Api(cls.category))

	@classmethod
	def dump(cls, build_dir, items):
		# serialize the data if not already done
		fp = os.path.join(build_dir, cls.sfile_name)
		if not os.path.exists(fp):
			with open(fp, 'w') as fpickle:
				pickle.Pickler(fpickle).dump(list(items))

	def __init__(self, js):
		self.js = js

	def __repr__(self): return '%s<name=%s>' % (self.__class__.__name__, self.name)

	# called when an attribute is not found in the Token instance
	# automatically search for its related item in the json data
	def __getattr__(self, attr):
		if attr.lower() == 'charisma' and self.js['name'] == 'Aboleth' : return 18 # 5e api bug
		v = self.js.get(attr, None)
		# XXX raising RuntimeError instead of AttributeError, because there's 
		# a bad interraction between AttributeError and properties
		if v is None: raise RuntimeError("Cannot find the attribute %s" % attr)
		return v

	@property
	def name(self):
		# required otherwise this would later be misinterpreted for a path separator
		return self.js['name'].replace('/', '_')

	# The 2 following methods are use by pickle to serialize objects
	def __getstate__(self): return {'js' : self.js}
	def __setstate__(self, state): self.js = state['js']

class Spell(Dnd5ApiObject):
	sfile_name = 'spells.pickle' 
	category = 'spells'
	spellDB = []

	@property
	def desc(self): return '\n'.join(self.js['desc'])

	@property
	def comp(self): return ', '.join(self.js['components'])

class Token(Dnd5ApiObject):
	sentinel = object()
	sfile_name = 'tokens.pickle' 
	category = 'monsters'
	def __init__(self, js):
		self.js = js
		# for cached properties
		self._guid = self.sentinel
		self._img = self.sentinel
		self._md5 = self.sentinel

	def __repr__(self): 
		return 'Token<name=%s,attr=%s,hp=%s(%s),ac=%s,CR%s,img=%s>' % (self.name, [
			self.strength, self.dexterity, self.constitution, 
			self.intelligence, self.wisdom, self.charisma
			], self.hit_points, self.roll_max_hp, self.armor_class,
			self.challenge_rating, self.img_name)

	# The 2 following methods are use by pickle to serialize a token
	def __setstate__(self, state): 
		Dnd5ApiObject.__setstate__(self, state)
		self._guid = self.sentinel
		self._img = self.sentinel
		self._md5 = self.sentinel

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
	def bdex(self): return (self.dexterity-10)/2

	@property
	def bwis(self): return (self.wisdom-10)/2

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

	# spellcasting 
	@property
	def sc(self): return next((spe for spe in self.specials if spe['name'] == 'Spellcasting'), None)

	# wisdom, charisma ot intelligence
	@property
	def scAttributes(self):  # spellcasting attribute
		desc = self.sc['desc'].lower() if self.sc else ''
		attr = next((attr for attr in ['intelligence', 'charisma', 'wisdom'] if attr in desc), None)
		match = re.search(r'save dc (\d+)', desc)
		dc = match and int(match.group(1))
		match = re.search(r'([+-]\d+) to hit with spell', desc)
		attack = match and match.group(1)
		return (attr, dc, attack) if desc else None

	@property
	def scDC(self): return 

	@property
	def actions(self): return self.js.get('actions', [])

	@property
	def specials(self): return self.js.get('special_abilities', [])

	@property
	def legends(self): return self.js.get('legendary_actions', [])

	@property
	def perception(self): return self.js.get('perception', 10+self.bdex)

	@property
	def wisdom_save(self): return self.js.get('wisdom_save', 10+self.bwis)

	@property
	def note(self): return ''

	@property
	def immunities(self): return self.js.get('damage_immunities', '')

	@property
	def resistances(self): return self.js.get('damage_resistances','')

	@property
	def size_guid(self):
		# XXX may depend on the maptool version
		return {
			'tiny':       'fwABAc5lFSoDAAAAKgABAA==',
			'small':      'fwABAc5lFSoEAAAAKgABAA==',
			'medium':     'fwABAc9lFSoFAAAAKgABAQ==',
			'large':      'fwABAdBlFSoGAAAAKgABAA==',
			'huge':       'fwABAdBlFSoHAAAAKgABAA==',
			'gargantuan': 'fwABAdFlFSoIAAAAKgABAQ==',
		}[self.size.lower()]

	@property
	def macros(self): 
		# get optinal macros related to the token actions
		actions = (macros.ActionMacro(self, action) for action in self.actions)
		specials= (macros.SpecialMacro(self, spe) for spe in self.specials)
		legends= (macros.LegendaryMacro(self, leg) for leg in self.legends)
		attributes = self.scAttributes
		groupName = 'Spells'
		if attributes:
			attr, dc, attack = attributes
			groupName = 'Spells(%s) DC%s %s' % (attr[:3], dc, attack)
		spells = (macros.SpellMacro(self, spell, groupName) for spell in self.spells)
		return itertools.chain(actions, specials, legends, macros.commons(self), spells)

	@property
	def spells(self):
		spells = []
		for ability in (a for a in self.specials if a['name'] == 'Spellcasting'):
			spells = [s for s in Spell.spellDB if s.name.lower() in ability['desc']]
		return spells

	@property
	def props(self):
		return (Prop(name, value) for name, value in [
			('mname', self.name),
			('AC', self.armor_class),
			('MaxHp', self.hit_points),
			('Hp', self.hit_points),
			('HitDice', self.hit_dice),
			('Charisma', self.charisma),
			('Strength', self.strength),
			('Dexterity', self.dexterity),
			('Intelligence', self.intelligence),
			('Initiative', '{Dx}'),
			('Wisdom', self.wisdom),
			('Constitution', self.constitution),
			('Immunities', self.immunities), # XXX add condition immunities ?
			('Resistances', self.resistances),
			('CreatureType', self.type + ', CR ' + str(self.challenge_rating)),
			('Alignment', self.alignment),
			('Speed', self.speed),
			('Senses', self.senses),
			('WisdomSave', self.wisdom_save),
			('Languages', self.languages),
			('Perception', self.perception),
			('ImageName', self.img_name),
			])

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
			files = itertools.chain(*(glob.glob(os.path.join(os.path.expanduser(imglib), '*.png')) for imglib in imglibs))
			bratio=0
			if files:
				# generate the diff ratios
				ratios = ((f, ratio(short_name(f))) for f in files)
				# pickup the best match, it's a tuple (fpath, ratio)
				bfpath, bratio = max(itertools.chain(ratios, [('', 0)]), key = lambda i: i[1])
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

	@property
	def states(self): return (s for s in [State('Concentrating', 'false')])
	
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

def fromText(tfile):
	"""WIP"""
	with open(tfile, 'r') as _tfile:
		text = _tfile.read()
	# O -> 0
	# lawful -> tawful
	count = 0
	p1 = '([A-Z 0]+)\n(\w+) (\w+)( \(.*?\))?, (tawful|lawful|chaotic|neutral|unaligned)[\s\S]*?STR[\s\S]*?'
	# 1 -> l
	p2 = '([0-9lO]+) ?[({]([-+]? ?[0-9lO]+)[)}][\s\S]*?'*3
	mp1 = re.findall(p1, text)
	matches = re.findall(p1+p2, text)
	for m in matches:
		count+=1
		print count, m
	for e in mp1:
		if e[0] not in [m[0] for m in matches]:
			print "missing %s" % str(e)
	

def main():
	parser = argparse.ArgumentParser(description='Process some integers.')
	parser.add_argument('--verbose', '-v', action='count')
	parser.add_argument('--max-token', '-m', type=int)
	global args
	args = parser.parse_args()
	if not os.path.exists('build'): os.makedirs('build')

	# fetch the monsters(token) and spells from dnd5Api or get them from the serialized file
	tokens = itertools.chain((Token(m) for m in monsters), Token.load('build'))
	Spell.spellDB = list(Spell.load('build'))

	sTokens = [] # used for further serialization, because tokens is a generator and will be consumed
	for token in itertools.islice(tokens, args.max_token):
		#if 'Mage' not in token.name: continue
		log.info(token)
		token.zipme()
		sTokens.append(token)
	
	Token.dump('build', sTokens)
	Spell.dump('build', Spell.spellDB)

if __name__ == '__main__':
	logging.basicConfig(level=logging.INFO)
	#fromText('volo.txt')
	main()
