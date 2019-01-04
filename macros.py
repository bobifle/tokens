#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import jinja2
import copy
import re

log = logging.getLogger(__name__)

spellTemplate = u'''
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

	def __init__(self, token, action, label, command, **kwargs):
		self._command = command
		self._label = label
		self.token = token
		self.action = action
		self.tooltip = ''
		self._group = None
		self._bcolor = None # the background button color
		self._fcolor = None # the font color of the macro button
		for k,v in kwargs.iteritems(): setattr(self, k, v)

	def __str__(self): return '%s<%s,grp=%s>' % (self.__class__.__name__, self.label, self.group)
	def __repr__(self): return str(self)

	def verbose(self): return "\t%s\n" % self

	@property
	def command(self): return jinja2.Template(self._command).render(macro=self)

	@property
	def label(self): return self._label

	@property
	def group(self): return self._group or 'unknown'
	@group.setter
	def group(self, v): self._group = v

	@property
	def color(self): return {'Health' : 'green', 'Action': 'black'}.get(self.group, 'black') if self._bcolor is None else self._bcolor
	@color.setter
	def color(self, v): self._bcolor = v

	@property
	def fontColor(self): return self._fcolor or 'white'
	@fontColor.setter
	def fontColor(self, v): self._fcolor = v

	@property
	def colors(self): return self.fontColor, self.color # tuple (font, bg)
	
	@colors.setter
	def colors(self, fbg): self.fontColor, self.color = fbg


class DescrMacro(Macro):
	def __init__(self, token, action):
		Macro.__init__(self, token, action, action['name'], '''[h:data = json.set("{}",
	"Name", "%s",
	"Description", "%s")]

[macro("Description@Lib:Addon5e"):data]'''%(action['name'], action['desc']))

	@property
	def group(self): return self._group or 'Misc'

	@property
	def name(self): return self.action.get('name', "")

	@property
	def desc(self): return self.action.get('desc', "")

	def verbose(self):
		v = "\t%s\n" % self
		if self.desc: v+= "\t\t%s\n"%self.desc
		return v


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
	"DamageType","%s",
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

	def verbose(self):
		v = "\t%s\n" % self
		if self.desc: v+= "\t\t%s\n" % self.desc
		for field in ['attack_bonus', 'damage_dice', 'damage_bonus', 'damage_type', 'reach']:
			if getattr(self, field) : v += "\t\t%s: %s\n" % (field, getattr(self, field))
		return v

	@property
	def hit_dd_db_type(self):
		match = re.search(r'\+(\d+) to hit,.*\((\d+d\d+) \+ (\d+)\) (\w+) damage', self.desc)
		return match.groups() if match else None


	@property
	def damage_dice(self):
		dd = self.action.get('damage_dice', "")
		# try infering the damage dice from the description
		if dd == "" and self.hit_dd_db_type is not None:
			dd = self.hit_dd_db_type[1]
		return dd

	@property
	def damage_bonus(self):
		db = self.action.get('damage_bonus', 0)
		# try infering the damage dice from the description
		if db == 0 and self.hit_dd_db_type is not None:
			db = self.hit_dd_db_type[2]
		return db

	@property
	def damage_type(self):
		dt = self.action.get('damage_type', "")
		# try infering the damage dice from the description
		if dt == "" and self.hit_dd_db_type is not None:
			dt = self.hit_dd_db_type[3]
		return dt

	@property
	def attack_bonus(self):
		ab = self.action.get('attack_bonus', 0)
		# try infering the damage dice from the description
		if ab == 0 and self.hit_dd_db_type is not None:
			ab = self.hit_dd_db_type[0]
		return ab

	@property
	def reach(self):
		reach = self.action.get('reach', 0)
		if reach == 0 :
			match = re.search(r'reach (\d+) ?ft\.', self.desc)
			if match: reach = int(match.group(1))
		return reach

	@property
	def group(self): return self._group or 'Action'

class LairMacro(ActionMacro) : 
	@property
	def color(self): return self._bcolor or 'orange'
	@property
	def fontColor(self): return self._fcolor or 'black'
	@property
	def group(self): return self._group or 'Lair (on init 20)' 

class RegionalEffectMacro(ActionMacro) : 
	@property
	def color(self): return self._bcolor or 'blue'
	@property
	def fontColor(self): return self._fcolor or 'white'
	@property
	def group(self): return self._group or 'Regional Effects' 

class LegendaryMacro(ActionMacro) : 
	@property
	def color(self): return self._bcolor or 'orange'
	@property
	def fontColor(self): return self._fcolor or 'black'
	@property
	def group(self): return self._group or 'Legendary' 

class SpecialMacro(DescrMacro):
	@property
	def group(self): return self._group or 'special'
	@property
	def color(self): return self._bcolor or 'maroon'

class SpellCastingMacro(DescrMacro):
	def __init__(self, token, spell, groupName):
		DescrMacro.__init__(self, token, spell)
		self._group = groupName
	@property
	def group(self): return self._group
	@property
	def color(self): return self._bcolor or 'maroon'

class SpellMacro(Macro):
	def __init__(self, token, spell):
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
		self._group = 'Level %s' % spell.level if spell.level >= 1 else 'Cantrips'

	@property
	def group(self): return self._group
	@property
	def color(self): return 'blue'


class SheetMacro(Macro):
	def __init__(self, token):
		with open('macros/token_sheet.mtmacro') as template:
			Macro.__init__(self, token, None, 'Sheet', template.read(), **{'group':"Sheet", 'colors': ('black', 'yellow'), 'tooltip': 'Display the NPC sheet'})

