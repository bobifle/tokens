# Tokens

Drop-in DnD 5e Tokens for maptool.

These a specifically aimed at:
* in person play
* online play, with minimum automated management. Some players love to roll dice and track their HP

These tokens won't add anything to you campaign settings, they are drop-in macros. They can be dragged into any exisiting campaign session.
Updating them is as trivial as dragging tokens into your maptool map.

If you are searching for fully automated frameworks, they are more heavy frameworks to be found on the maptool forum.

## Installation

Extract the zip file.
You should see:

`tokens/*rptok`
`Lib_Addon5e.rptok`

Copy `Lib_Addon5e.rptok` into your library map (any non player visible map), create one if you don't have any. **Rename the token "Lib:Addon5e"**,
(depending on your Maptool options, the application may have renamed it when you dragged it).

Drag any token file in your maps to start using it.

Optionaly, you can add the tokens directory to your maptool library window.

## Known limitations
* all macros broadcast to the GM and players alike. GM, you won't be able to fudge. I'm working on it...
* some dragons miss their legendary/lair actions
* as a general rule, for important NPCs, double check with the monster manual
* tokens are not editable, not in a friendly way. Maptool does restrict access to token's properties. Maybe things will change in the future...

## Credits

* I borrowed a lot from existing frameworks (Paulstrait's, Wolf42)
* I stole all SRD monsters data from dnd5Api.com
* This was made possible by the active community on the Maptool forum and the discord server. Thanks for their valuable help.


## Changelogs
### v0.2
* dependency to the DnD5e framework is now gone, these are now complete drop-in tokens
* added 40+ tokens from volo's
* fix a bug where the to-hit bonus was used instead of the damage bonus :-/
* add rolls for ability checks
* add rolls for saving throws
* add an init button to auto add and set a NPC token to the init windows
* fix a lot of issues with non ascii characters messing with the monsters sheet

