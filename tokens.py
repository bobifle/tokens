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
import collections
from PIL import Image

# local import
import macros

log = logging.getLogger()

ubase = 'http://dnd5eapi.co/api/'
#imglib = r'c:/Users/Sulay/OneDrive/RPG/maptool cmpgn/imglib'
imglib = r'c:/Users/Bobifle/OneDrive/RPG/maptool cmpgn/imglib'
if not os.path.exists(imglib):
	imglib = '../imglib'
imglibs = [imglib] + [ imglib+"/%s"%sub for sub in ['volo'] ]

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

class State(object):
	def __init__(self, name, value):
		self.name = name
		self.value = value
	def __repr__(self): return 'S<%s,%s>' % (self.name, self.value)

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
	pattern = r'(\d+d\d+) (\w+) damage'

	@property
	def html_desc(self): return ' '.join(self.js['desc']).replace("'", "&#39;")

	@property
	def desc(self): return ' '.join(self.js['desc'])

	@property
	def classes(self): return [item['name'] for item in self.js['classes']]

	@property
	def damage(self):
		match = re.search(self.pattern, self.desc)
		if match: return match.group(1)
		return 0

	@property
	def damage_type(self):
		match = re.search(self.pattern, self.desc)
		if match: return match.group(2)
		return "Damage"

	@property
	def school(self): return self.js['school']['name']

	@property
	def concentration(self): return int(self.js['concentration']=='yes')

	@property
	def save(self): return "unkown"

	@property
	def save_type(self): return "unkown type"

	@property
	def attack(self): return int("spell attack" in self.desc)

	@property
	def on_hit(self): return ""

	@property
	def components(self): return ', '.join(self.js['components'])

	@property
	def ritual(self): return int(self.js['ritual'] == 'yes')

	@property
	def target(self): return ""


class Token(Dnd5ApiObject):
	sentinel = object()
	sfile_name = 'tokens.pickle'
	category = 'monsters'
	pngFiles = sentinel
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
		content = t.render(token=self)
		return content or ''

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
	def lair_actions(self): return self.js.get('lair_actions', [])

	@property
	def regional_effects(self): return self.js.get('regional_effects', [])

	@property
	def perception(self): return self.js.get('perception', 10+self.bdex)

	@property
	def vulnerabilities(self): return self.js.get('damage_vulnerabilities', "")

	@property
	def immunities(self): return self.js.get('damage_immunities', "")

	@property
	def resistances(self): return self.js.get('damage_immunities', "")

	@property
	def skills(self): return self.js.get('skills', "")

	# saves can be specified in different ways:
	# either a field "saves": "Saving Throws Int +5, Wis +5, Cha +4"
	# or respective field like "wisdom_save": 5
	@property
	def saves(self): return self.js.get('saves', "")

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
		actions = (macros.ActionMacro(self, action) for action in self.actions if action["name"])
		lairs = (macros.LairMacro(self, action) for action in self.lair_actions if action["name"])
		reg = (macros.RegionalEffectMacro(self, action) for action in self.regional_effects if action["name"])
		legends= (macros.LegendaryMacro(self, leg) for leg in self.legends if leg["name"])
		attributes = self.scAttributes
		spellCast = []
		if attributes:
			attr, dc, attack = attributes
			groupName = 'Spells(%s) save DC%s attack %s' % (attr[:3], dc, attack)
			spellCast = (macros.SpellCastingMacro(self, spe, groupName) for spe in self.specials if spe['name'].lower()=="spellcasting")
		specials = (macros.SpecialMacro(self, spe) for spe in self.specials if spe['name'] and spe['name'].lower()!="spellcasting")
		spells = (macros.SpellMacro(self, spell) for spell in self.spells)
		commons = [
			macros.SheetMacro(self),
			macros.Macro(self, None, 'Init', '[macro("Init@Lib:Addon5e"):0]', **{'group': 'Rolls', 'colors': ('white', 'green'), 'tooltip': 'Roll and add to the init panel'}),
			macros.Macro(self, None, 'SaveMe', '[macro("SaveMe@Lib:Addon5e"):0]', **{'group': 'Rolls', 'colors': ('white', 'green'), 'tooltip': 'Roll Saving Throws'}),
			macros.Macro(self, None, 'CheckMe', '[macro("CheckMe@Lib:Addon5e"):0]', **{'group': 'Rolls', 'colors': ('white', 'green'), 'tooltip': 'Roll Skill Checks'}),
		]
		if not args.delivery: 
			commons.append(macros.Macro(self, None, 'Debug', '[macro("Debug@Lib:Addon5e"):0]', **{'group': 'zDebug', 'colors': ('white', 'black')}))
		return itertools.chain(actions, spellCast, specials, legends, lairs, reg, commons, spells)

	@property
	def slots(self): # current spendable slots
		slots = collections.OrderedDict()
		if self.sc is not None:
			sc = self.sc['desc']
			match = re.search(r'1st level \((\d) slot', sc)
			slots['First'] = int(match.group(1)) if match else 0
			match = re.search(r'2nd level \((\d) slot', sc)
			slots['Second'] = int(match.group(1)) if match else 0
			match = re.search(r'3rd level \((\d) slot', sc)
			slots['Third'] = int(match.group(1)) if match else 0
			match = re.search(r'4th level \((\d) slot', sc)
			slots['Fourth'] = int(match.group(1)) if match else 0
			match = re.search(r'5th level \((\d) slot', sc)
			slots['Fifth'] = int(match.group(1)) if match else 0
			match = re.search(r'6th level \((\d) slot', sc)
			slots['Sixth'] = int(match.group(1)) if match else 0
			match = re.search(r'7th level \((\d) slot', sc)
			slots['Seventh'] = int(match.group(1)) if match else 0
			match = re.search(r'8th level \((\d) slot', sc)
			slots['Eighth'] = int(match.group(1)) if match else 0
			match = re.search(r'9th level \((\d) slot', sc)
			slots['Ninth'] = int(match.group(1)) if match else 0
		return slots

	@property
	def spell_slots(self): #max slots available
		spells={}
		for i, (k,v) in enumerate(self.slots.iteritems()):
			spells["%s"%(i+1)] = v
		return spells

	@property
	def spells(self):
		spells = []
		for ability in (a for a in self.specials if 'spellcasting' in a['name'].lower()):
			spells.extend([s for s in Spell.spellDB if s.name.lower() in ability['desc']])
		return spells

	@property
	def attributes(self):
		return ['Strength', 'Dexterity', 'Constitution', 'Intelligence', 'Wisdom', 'Charisma']

	@property
	def props(self):
		return (Prop(name, value) for name, value in [
			('mname', self.name),
			('AC', self.armor_class),
			('MaxHp', self.hit_points),
			('Hp', self.hit_points),
			('HitDice', self.hit_dice),
			('Strength', self.strength),
			('Dexterity', self.dexterity),
			('Constitution', self.constitution),
			('Wisdom', self.wisdom),
			('Intelligence', self.intelligence),
			('Charisma', self.charisma),
			('Initiative', '[h,macro("getNPCInitBonus@Lib:Addon5e"):0][r: macro.return]'),
			('Immunities', self.immunities), # XXX add condition immunities ?
			('Resistances', self.resistances),
			('CreatureType', self.type + ', CR ' + str(self.challenge_rating)),
			('Alignment', self.alignment),
			('Speed', self.speed),
			('Saves', self.saves),
			('Skills', self.skills),
			('jSkills', '[h,macro("getNPCSkills@Lib:Addon5e"):0][r: macro.return]'),
			('Senses', self.senses),
			('Vulnerabilities', self.vulnerabilities),
			('Resistances', self.resistances),
			('Immunities', self.immunities),
			('Languages', self.languages),
			('Perception', self.perception),
			('ImageName', self.img_name),
			('SpellSlots', self.spell_slots),
			# do ('bstr', '{floor((getProperty("Strength")-10)/2)}') for all attributes
			] + [('b%s' % a[:3].lower(), '{floor((getProperty("%s")-10)/2)}' % a) for a in self.attributes] +
			[(k, v) for k,v in self.slots.iteritems()]
			)

	@property
	def pngs(self):
		if self.pngFiles is self.sentinel:
			Token.pngFiles = list(itertools.chain(*(glob.glob(os.path.join(os.path.expanduser(imglib), '*.png')) for imglib in imglibs)))
		return iter(self.pngFiles) if self.pngFiles else None

	@property
	def img(self):
		# try to fetch an appropriate image from the imglib directory
		# using a stupid heuristic: the image / token.name match ratio
		if self._img is self.sentinel: # cache to property
			# compute the diff ratio for the given name compared to the token name
			ratio = lambda name: difflib.SequenceMatcher(None, name.lower(), self.name.lower()).ratio()
			# morph "/abc/def/anyfile.png" into "anyfile"
			short_name = lambda full_path: os.path.splitext(os.path.basename(full_path))[0]
			bratio=0
			if self.pngs:
				# generate the diff ratios
				ratios = ((f, ratio(short_name(f))) for f in self.pngs)
				# pickup the best match, it's a tuple (fpath, ratio)
				bfpath, bratio = max(itertools.chain(ratios, [('', 0)]), key = lambda i: i[1])
				log.debug("Best match from the img lib is %s(%s)" % (bfpath, bratio))
			if bratio > 0.8:
				self._img = Image.open(bfpath, 'r')
			else:
				self._img = Image.open(imglib+'/dft.png', 'r')
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
	def states(self): return [s for s in [State('Concentrating', 'false')]]

	def zipme(self):
		"""Zip the token into a rptok file."""
		filename = os.path.join('build', '%s.rptok'%(self.name.replace(":","_")))
		# don't compress to avoid technical issue when sharing files
		# the gain is very small anyway
		with zipfile.ZipFile(filename, "w", zipfile.ZIP_STORED) as zipme:
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
		return filename

	def verbose(self):
		v = "%s\n" % self
		for attr in ['saves', 'skills', 'senses', 'vulnerabilities', 'immunities', 'resistances', 'slots', 'spell_slots']:
			v+= '%s: %s\n' % (attr, getattr(self, attr))
		for m in self.macros:
			v+="\n%s"%m.verbose()
		return v

class LibToken(Token):
	def __init__(self, name):
		Token.__init__(self, {'name': name, 'size': 'large'})
		self._macros = []
	def __repr__(self): return 'LibToken<%s>' % self.name
	@property
	def macros(self): return self._macros
	@property
	def props(self): 
		with open(r'../5e-database/5e-SRD-Ability-Scores.json', 'r') as afile:
			data = json.load(afile)
		all_skills = {}
		for attribute in data:
			for skill in attribute['skills']:
				all_skills[skill['name']] = attribute['full_name']
		return (Prop(name, value) for name, value in [
			('all_skills', json.dumps(all_skills)),
			('attributes', json.dumps(self.attributes)),
		])
	@property
	def spells(self): return []

	def add(self, macro): self._macros.append(macro)

def main():
	parser = argparse.ArgumentParser(description='DnD 5e token builder')
	parser.add_argument('--verbose', '-v', action='count')
	parser.add_argument('--max-token', '-m', type=int)
	parser.add_argument('--delivery', '-d', action="store_true", default=False)
	global args
	args = parser.parse_args()
	if not os.path.exists('build'): os.makedirs('build')
	localMonsters = []
	for f in [r'../5e-database/5e-SRD-Monsters-volo.json', r'../5e-database/5e-SRD-Monsters.json']:
		with open(f, 'r') as mfile:
			localMonsters += json.load(mfile)

	mLog = logging.getLogger()
	mLog.setLevel(logging.DEBUG)
	mLog.handlers[-1].setLevel(logging.WARNING-(args.verbose or 0)*10)
	fh = logging.FileHandler(os.path.join('build', 'tokens.log'), mode="w") # mode w will erase previous logs
	fh.setLevel(logging.DEBUG)
	fh.setFormatter(logging.Formatter('%(name)s : %(levelname)s : %(message)s'))
	mLog.addHandler(fh)

	# generate the lib addon token
	addon = LibToken('Lib:Addon5e')
	fromFile = lambda path: jinja2.Template(open(path, 'r').read()).render()
	params = {'group': 'zLib', 'prefix': 'a5e'}
	addon.add(macros.Macro(addon, '', 'onCampaignLoad', '''
[h: defineFunction( "%(prefix)s.jget", "jget@this" )]
[h: defineFunction( "%(prefix)s.debug", "debug@this" )]
[h: defineFunction( "%(prefix)s.output", "output@this" )]
[h: defineFunction( "%(prefix)s.rollDice", "rollDice@this",0,0)]
''' % params, **params))
	addon.add(macros.Macro(addon, '', 'debug', '''[h: props = getPropertyNames()] [foreach(name, props, "<br>"), code: { [name]: [getProperty(name)]: [getRawProperty(name)]}] ''', **params))
	addon.add(macros.Macro(addon, '', 'output', fromFile("macros/output.mtmacro"), **params))
	addon.add(macros.Macro(addon, '', 'rollDice', fromFile("macros/rollDice.mtmacro"), **params))
	addon.add(macros.Macro(addon, '', 'jget', '''
[h: '<!-- Like json.get, but will adapt if the requested reference cannot be made.  By default, returns 0, or returns a default named (as a third parameter). -->']

[h: object = arg(0)]
[h: key = arg(1)]
[h, if( argCount() > 2 ): default = arg(2); default = 0]

[h, if( json.type( object ) == "OBJECT" ), code:
{
	[h: macro.return = if( json.contains( object, key ), json.get( object, key ), default )]
};{
	[if( json.type( object ) == "ARRAY" && isNumber( key ) ), code:
	{
		[h, if( json.length( object ) > key ): 
			macro.return = json.get( object, key ) ;
			macro.return = default )]
	};{
		[h: macro.return = default ]
	}]
}]
''', **params))
	params = {'group': 'dnd5e'}
	addon.add(macros.Macro(addon, '', 'Description', jinja2.Template(open('macros/description.template', 'r').read()).render(), **params))
	addon.add(macros.Macro(addon, '', 'CastSpell', jinja2.Template(open('macros/castSpell.template', 'r').read()).render(), **params))
	addon.add(macros.Macro(addon, '', 'NPCAttack', jinja2.Template(open('macros/npcAttack.template', 'r').read()).render(), **params))
	addon.add(macros.Macro(addon, '', 'Init', jinja2.Template(open('macros/init.template', 'r').read()).render(), **params))
	addon.add(macros.Macro(addon, '', 'getNPCInitBonus', '''[h, macro("getNPCSkills@Lib:Addon5e"):0]
[h: jskills = macro.return]
[h: initb = json.get(jskills, "Initiative")]
[h, if (initb==""), code: {[h: initb=getProperty("bdex")]}]
[h:macro.return=initb]''', **params))
	# "Perception +5, Initiative +3" => {"Perception": 5, "Initiative": 3}
	addon.add(macros.Macro(addon, '', 'getNPCSkills', r'''[h: id = strfind(getProperty("skills"), "((\\w+) \\+(\\d+))")]
[h: jskills = "{}"]
[h: find = getFindCount(id)]
[h, while (find != 0), code: {
	[h: sname = getGroup(id, find, 2)]
	[h: svalue = getGroup(id, find, 3)]
	[h: jskills = json.set(jskills, sname, svalue)]
	[h: find = find - 1]
}]
<!-- Most of the token don't specify a modifier for all skills-->
<!-- for all skills missing a modifier, use the default one which is the attribute modifier -->
[h: all_skills= getLibProperty("all_skills", "Lib:Addon5e")]
[h, foreach(skill, all_skills), code: {
	[Attribute = json.get(all_skills, skill)]
	[att_ = lower(substring(Attribute, 0, 3))]
	[modifier = json.get(jskills, skill)]
    [default_mod = getProperty("b"+att_)]
    [no_mod = json.isEmpty(modifier) ]
	[if (no_mod): jskills = json.set(jskills, skill , default_mod)]
}]
[h: macro.return = jskills]''', **params))
	# "Wis +3, Con +2" => {"Wis": 2, "Con": 2}
	addon.add(macros.Macro(addon, '', 'getNPCSaves', r'''[h: id = strfind(getProperty("saves"), "((\\w+) \\+(\\d+))")]
[h: jsaves= "{}"]
[h: find = getFindCount(id)]
<!-- parse the prop "saves" which may contain some save modifiers-->
<!-- "Wis +3, Con +2" => "Wis": 2, "Con": 2 -->
[h, while (find != 0), code: {
	[h: sname = getGroup(id, find, 2)]
	[h: svalue = getGroup(id, find, 3)]
	[h: jsaves = json.set(jsaves, sname, svalue)]
	[h: find = find - 1]
}]
<!-- Most of the token don't specify a modifier for all saves -->
<!-- for all saves missing a modifier, use the default one which is the attribute modifier -->
[h, foreach(Attribute, getLibProperty("attributes", "Lib:Addon5e")), code: {
	[Att = substring(Attribute, 0, 3)]
	[att_ = lower(Att)]
	[modifier = json.get(jsaves, Att)]
    [default_mod = getProperty("b"+att_)]
    [no_mod = json.isEmpty(modifier) ]
	[if (no_mod): jsaves = json.set(jsaves, Att ,default_mod)]
}]
[h: macro.return = jsaves]''', **params))
	addon.add(macros.Macro(addon, '', 'SaveMe', jinja2.Template(open('macros/saveme.template', 'r').read()).render(), **params))
	addon.add(macros.Macro(addon, '', 'CheckMe', jinja2.Template(open('macros/checkme.template', 'r').read()).render(), **params))
	params = {'group': 'aMenu'}
	# TODO: control panel is currently empty but it is a customized panel where I can add whatever macro, it act as a campaign panel
	# but is fully customizable, it's a html form
	# see http://forums.rptools.net/viewtopic.php?f=20&t=23208&p=236662&hilit=amsave#p236662
	addon.add(macros.Macro(addon, '', 'ControlPanel', '''[dialog("A5e Panel", "width=215; height=700; temporary=0; input=1"): {[r,macro("cpanel@this"):0]}]''', **params))
	params = {'group': 'Format'}
	addon.add(macros.Macro(addon, '', 'cpanel', jinja2.Template(open('macros/cpanel.template', 'r').read()).render(), **params))
	addon.add(macros.Macro(addon, '', 'HTMLMacroButton','''[h:bgColor	= arg(1)]
[h,if(argCount() > 5): shadow = arg(5); shadow = "")]
[h,if(argCount() > 6): toolTip = arg(6); toolTip = "")]
[h,if(argCount() > 7): args = arg(7); args = "[]")]
[h,if(argCount() > 8): libType = arg(8); libType = "@this")]
[h,if(argCount() > 9): output = arg(9); output = "none")]

[h:btnformat	= strformat("padding:1px; border-width:1pt; border-style:solid; border-color:black; text-align:center; white-space:nowrap; background-image:url(%{shadow}); background-color:%{bgColor};")]
 
<td width='[r:arg(0)]%'>
	<table width='100%' cellpadding='0' cellspacing='0'>
		<tr>
			<td style='[r:btnformat]'>
				<span title='[r:toolTip]' style='text-decoration:none; color:[r:arg(2)]'>
					[r:macroLink(arg(3),arg(4)+libType,output,args)]
				</span>
			</td>
		</tr>
	</table>
</td>''' , **params))
	filename = addon.zipme()
	log.warning("Done generating 1 library token: %s" % addon)

	# fetch the monsters(token) and spells from dnd5Api or get them from the serialized file
	#tokens = itertools.chain((Token(m) for m in monsters), Token.load('build'))
	# dont use online api, use the fectched local database instead
	tokens = (Token(m) for m in localMonsters)
	# 5e-database is probably a link
	with open(r'../5e-database/5e-SRD-Spells.json', 'r') as mfile:
		localSpells = json.load(mfile)

	Spell.spellDB = [Spell(spell) for spell in localSpells]

	sTokens = [] # used for further serialization, because tokens is a generator and will be consumed
	cnt = 0
	deliveryFilename = 'build/dnd5eTokens.zip'
	zfile = zipfile.ZipFile(deliveryFilename, "w", zipfile.ZIP_STORED) if args.delivery else None
	# add lib:addon5e to the zipfile
	if zfile: 
		zfile.write(filename, os.path.basename(filename))
	for token in itertools.islice(tokens, args.max_token): 
		log.info(token)
		log.debug(token.verbose())
		filename = token.zipme()
		if zfile: 
			zfile.write(filename, os.path.join("tokens", os.path.basename(filename)))
		sTokens.append(token)
		if 'dft.png' in token.img.filename: log.warning(str(token))
		cnt += 1
	log.warning("Done generation %s tokens"%cnt)
	if zfile:
		zfile.close()
		log.warning("Done writing delivery zip file '%s'" % deliveryFilename)

	Token.dump('build', sTokens)
	Spell.dump('build', Spell.spellDB)

if __name__ == '__main__':
	logging.basicConfig(level=logging.INFO)
	main()
