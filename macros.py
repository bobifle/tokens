#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import jinja2
import copy

log = logging.getLogger(__name__)

class Macro(object):
	def __init__(self, label, command):
		self._command = command
		self._label = label
		self.token=None
		self.action=None
	
	def __str__(self): return '%s<%s,grp=%s>' % (self.__class__.__name__, self.label, self.group)
	def __repr__(self): return str(self)

	@property
	def command(self): return jinja2.Template(self._command).render(macro=self)

	@property
	def label(self): return self._label

	@property
	def group(self): return 'unkown' 

	@property
	def color(self): return {'Health' : 'green', 'Action': 'black'}[self.group]

class ActionMacro(Macro):
	def __init__(self, label):
		Macro.__init__(self, label, '''[h:jsonWeaponData = json.set("{}",
"WeaponName", "{{macro.label}}",
"DamageType", "{{macro.damageType}}",
"DamageDie", "{{macro.action['damage_dice']}}",
"PrimaryStat", "Str",
"MagicBonus","0",
"SpecialAbility","",
"MiscAttackBonus",-1,
"MiscDamageBonus",0,
"MinimumCritRoll","20",
"FlavorText","The {{macro.token.name}} lashes out with claws.",
"ButtonColor","{{macro.color}}",
"FontColor","white")]

[macro("WeaponAttack@Lib:Melek"):jsonWeaponData])
				''')
	@property
	def group(self): return 'Action'
	@property
	def damageType(self):
		if 'slashing' in self.action['desc']: return 'Slashing'
		if 'bludge' in self.action['desc']: return 'Bludgeoning'
		if 'pierc' in self.action['desc']: return 'Piercing'
		return 'unknown'

class DescrMacro(Macro):
	def __init__(self, label):
		Macro.__init__(self, label, '''{{macro.action['desc']}}''')
	@property
	def group(self): return 'Action'

class HealthMacro(Macro):
	def __init__(self, label, macro_name):
		self.mname = macro_name
		Macro.__init__(self, label, '''[h:Flavor=token.name+" FLAVOR TEXT HERE"]

[h:FlavorData = json.set("",
	"Flavor",Flavor,
	"ParentToken",currentToken())]

[macro("{{macro.mname}}") : FlavorData]''')
	@property
	def group(self): return 'Health'

common = [
	HealthMacro('Potion of Healing', 'Potion of Healing@Lib:Melek' ),
	HealthMacro('Change HP', 'Change HP@Lib:Melek'),
]

optionals = [
	ActionMacro('Claw'),
	ActionMacro('Club'),
	ActionMacro('Scimitar'),
	ActionMacro('Tail'),
	ActionMacro('Tentacle'),
]

def getAction(token, action):
	rmacro = None
	for macro in optionals:
		if action['name'].lower().strip() == macro.label.lower().strip():
			rmacro = copy.copy(macro)
			break
	if rmacro is None:
		rmacro = DescrMacro(action['name'])
	rmacro.token = token
	rmacro.action = action
	return rmacro
	
def commons(token):
	for macro in common:
		rmacro = copy.copy(macro)
		rmacro.token = token
		yield rmacro
