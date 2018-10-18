#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import jinja2
import copy
import re

log = logging.getLogger(__name__)

spellTemplate = '''
[h:data = json.set("{}",
	"Flavor", "{{token.name}} casts {{spell.name}}",
	"ParentToken",currentToken(),
	"SpellName", "{{spell.name}}",
	"sLevel", {{spell.level}},
	"sSchool", "{{spell.school}}",
	"sDamage", "{{spell.damage}}",
	"sDamageType", "{{spell.damage_type}}",
	"sConcentration", {{spell.concentration}},
	"sSpellSave", "{{spell.save}}",
	"sSaveType", "{{spell.save_type}}",
	"sSpellAttack", {{spell.attack}},
	"sOnHit", "{{spell.on_hit}}",
	"sDescription", "{{spell.desc}}",
	"CastTime","{{spell.casting_time}}",
	"Range", "{{spell.range}}",
	"Target", "{{spell.target}}",
	"Components", "{{spell.components}}",
	"Duration","{{spell.duration}}",
	"Ritual", {{spell.ritual}})]

[macro("CastSpell@Lib:Addon5e"):data]
'''

class Macro(object):

	def __init__(self, token, action, label, command):
		self._command = command
		self._label = label
		self.token = token
		self.action = action
	
	def __str__(self): return '%s<%s,grp=%s>' % (self.__class__.__name__, self.label, self.group)
	def __repr__(self): return str(self)

	@property
	def command(self): return jinja2.Template(self._command).render(macro=self)

	@property
	def label(self): return self._label

	@property
	def group(self): return 'unknown' 

	@property
	def color(self): return {'Health' : 'green', 'Action': 'black'}.get(self.group, 'black')

	@property
	def fontColor(self): return 'white'


class DescrMacro(Macro):
	def __init__(self, token, action):
		Macro.__init__(self, token, action, action['name'], '''[h:data = json.set("{}",
	"Name", "%s",
	"Description", "%s")]

[macro("Description@Lib:Addon5e"):data]'''%(action['name'], action['desc']))
	@property
	def group(self): return 'Misc'

class ActionMacro(DescrMacro) :
	def __init__(self, token, action):
		self.action = action
		label = action['name']
		if self.damage_dice:
			label += ' +%s %s+%s'%( self.attack_bonus, self.damage_dice, self.damage_bonus)
			Macro.__init__(self, token, action, label, '''[h:jsonWeaponData = json.set("{}",
	"Name", "%s",
	"DamageDie", "%s",
	"DamageBonus",%s,
	"DamageType",%s,
	"HitBonus",%s,
	"SecDamageType", 0,
	"SecDamageDie", 0,
	"SecDamageBonus",0,
	"SpecialAbility","",
	"Description", "%s",
	"FlavorText","%s attacks!",
	"ButtonColor","green",
	"FontColor","white")]

[macro("NPCAttack@Lib:Addon5e"):jsonWeaponData]'''%(label, self.damage_dice, self.damage_bonus, self.damage_type, self.attack_bonus, action['desc'], token.name))
		else:
			DescrMacro.__init__(self, token, action)

	@property
	def desc(self): return self.action.get('desc', "")

	@property
	def hit_dd_db_type(self):
		match = re.search(r'\+(\d+) to hit,.*\((\d+d\d+) \+ (\d+)\) (\w+) damage', self.desc)
		return match.groups() if match else None


	@property
	def damage_dice(self):
		dd = self.action.get('damage_dice', None)
		# try infering the damage dice from the description
		if dd is None and self.hit_dd_db_type is not None:
			dd = self.hit_dd_db_type[1]
		return dd

	@property
	def damage_bonus(self):
		db = self.action.get('damage_bonus', None)
		# try infering the damage dice from the description
		if db is None and self.hit_dd_db_type is not None:
			db = self.hit_dd_db_type[2]
		return db

	@property
	def damage_type(self):
		dt = self.action.get('damage_type', None)
		# try infering the damage dice from the description
		if dt is None and self.hit_dd_db_type is not None:
			dt = self.hit_dd_db_type[3]
		return dt

	@property
	def attack_bonus(self):
		ab = self.action.get('attack_bonus', None)
		# try infering the damage dice from the description
		if ab is None and self.hit_dd_db_type is not None:
			ab = self.hit_dd_db_type[0]
		return ab

	@property
	def group(self): return 'Action'

class LairMacro(ActionMacro) : 
	@property
	def color(self): return 'orange'
	@property
	def fontColor(self): return 'black'
	@property
	def group(self): return 'Lair (on init 20)' 

class RegionalEffectMacro(ActionMacro) : 
	@property
	def color(self): return 'blue'
	@property
	def fontColor(self): return 'white'
	@property
	def group(self): return 'Regional Effects' 

class LegendaryMacro(ActionMacro) : 
	@property
	def color(self): return 'orange'
	@property
	def fontColor(self): return 'black'
	@property
	def group(self): return 'Legendary' 

class SpecialMacro(DescrMacro):
	@property
	def group(self): return 'special'
	@property
	def color(self): return 'maroon'

class SpellCastingMacro(DescrMacro):
	def __init__(self, token, spell, groupName):
		self._group = groupName
		DescrMacro.__init__(self, token, spell)
	@property
	def group(self): return self._group
	@property
	def color(self): return 'maroon'

class SpellMacro(Macro):
	def __init__(self, token, spell):
		self._group = 'Level %s' % spell.level if spell.level >= 1 else 'Cantrips'
		# not used anymore the window popping is annoying
		#with open('spell.template') as template:
		#	 t = jinja2.Template(template.read())
		#	 macro =  t.render(spell=spell)
		suffix = '('
		suffix += 'B' if 'bonus' in spell.casting_time else ''
		suffix += 'R' if 'reaction' in spell.casting_time else ''
		suffix += (('c' if suffix=='(' else ',c') if spell.concentration else '')
		suffix += ')'
		Macro.__init__(self, token, spell.js, spell.name+(suffix if suffix!='()' else ''), jinja2.Template(spellTemplate).render(spell=spell, token=token))
		self.action['description'] = '\n'.join(self.action['desc'])

	@property
	def group(self): return self._group
	@property
	def color(self): return 'blue'


class SheetMacro(Macro):
	def __init__(self, token):
		with open('token_sheet.template') as template:
			Macro.__init__(self, None, None, 'Sheet', template.read())

	@property
	def group(self): return 'Sheet'
	@property
	def color(self): return 'yellow'
	@property
	def fontColor(self): return 'black'


common = [
	SheetMacro(None)
]

def commons(token):
	for macro in common:
		rmacro = copy.copy(macro)
		rmacro.token = token
		yield rmacro
