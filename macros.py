#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import jinja2
import copy

log = logging.getLogger(__name__)

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

class DescrMacro(Macro):
	def __init__(self, token, action):
		damage_dice = action.get('damage_dice', '')
		damage_bonus = action.get('damage_bonus', 0)
		label = action['name']
		if damage_dice:
			label += ' +%s %s+%s'%(action['attack_bonus'], damage_dice, damage_bonus)
		Macro.__init__(self, token, action, label, '''/self {{macro.action['desc']}}''')
	@property
	def group(self): return 'Action'

class ActionMacro(DescrMacro) : pass
class LegendaryMacro(ActionMacro) : 
	@property
	def color(self): return 'orange'
	@property
	def group(self): return 'Legendary' 


class SpecialMacro(DescrMacro):
	@property
	def group(self): return 'Special'
	@property
	def color(self): return 'maroon'

class SpellMacro(Macro):
	def __init__(self, token, spell, groupName):
		# XXX pass the spell as action ... probably a sign of bad design
		self._group = groupName
		with open('spell.template') as template:
			 t = jinja2.Template(template.read())
			 macro =  t.render(spell=spell)

		Macro.__init__(self, token, spell.js, spell.name, macro)
		self.action['description'] = '\n'.join(self.action['desc'])

	@property
	def group(self): return self._group
	@property
	def color(self): return 'blue'


class SheetMacro(Macro):
	def __init__(self, token):
		with open('token_sheet.template') as template:
			 # t = jinja2.Template(template.read())
			 # macro =  t.render(token=token)
			Macro.__init__(self, None, None, 'Sheet', template.read())

	@property
	def group(self): return 'Sheet'
	@property
	def color(self): return 'black'


common = [
	SheetMacro(None)
]

def commons(token):
	for macro in common:
		rmacro = copy.copy(macro)
		rmacro.token = token
		yield rmacro
