# tokens
maptool token generator

Generates monster tokens for maptool, provided your are using the DnD 5e 
campaign framework from here: http://forums.rptools.net/viewtopic.php?f=85&t=25490

## Installation

You'll need python 2.7 installed
You'll probably need to install the module 'requests' and 'pillow'

pip install requests
pip install pillow 

on windows installing pillow is easier using the binary installer from their site.

## FAQ

Why are all my tokens bears ???

Because it's the default image I used when no suitable image is found. I do not own art.
However by editing one line in tokens.py, you can ad a directory, the script will
try to match the name of the token with the png files in that directory.
It way sometimes yield strange results because of the heuristic used by it will do the job

My tokens have almost no property, nor macro.

Make sure you're using the dnd 5e framework, the link is above.

