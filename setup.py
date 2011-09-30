import os
import sys

from distutils.core import setup

# Get the install prefix and write to the constants file
prefix = '/usr/local'
for arg in sys.argv:
		if arg.startswith('--prefix='):
				prefix = arg[9:]
				prefix = os.path.expandvars(prefix)

infile = open(os.path.join('internode', 'constants.py.in'))
data = infile.read()
infile.close()

outfile = open(os.path.join('internode', 'constants.py'), 'w')
outfile.write(data)
outfile.write("\nINTERNODE_PREFIX = '%s'\n\n" % prefix)

# Test whether we want to import the deprecated gnome.applet or
# the newer gnomeapplet
try:
	import gnomeapplet
	# Use gnomeapplet
	outfile.write("\nINTERNODE_GNOMEAPPLET = 'gnomeapplet'\n\n")
except ImportError:
	# Use (deprecated) gnome.applet
	outfile.write("\nINTERNODE_GNOMEAPPLET = 'gnome.applet'\n\n")

outfile.close()


# Write the install prefix to the InternodeUsageMeterApplet.server file (bonobo)
infile = open('InternodeUsageMeterApplet.server.in')
data = infile.read().replace('@PREFIX@', prefix)
infile.close()

outfile = open('InternodeUsageMeterApplet.server', 'w')
outfile.write(data)
outfile.close()

from internode.constants import *

# Do the setup routine
setup(name = INTERNODE_NAME,
	  version = INTERNODE_VERSION,
	  description = INTERNODE_DESCRIPTION,
	  url = INTERNODE_URL,
	  author = INTERNODE_AUTHORS[0].split('<')[0],
	  author_email = INTERNODE_AUTHORS[0],
	  license = 'GPL',
	  packages = ['internode'],
	  scripts = ['internode-applet.py'],
	  data_files = [('/usr/lib/bonobo/servers', ['InternodeUsageMeterApplet.server']),
	  				('share/internode', ['internode-applet.glade', 'menu.xml']),
					('share/internode/pixmaps', ['pixmaps/internode-0.png',
												 'pixmaps/internode-25.png',
												 'pixmaps/internode-50.png',
												 'pixmaps/internode-75.png',
												 'pixmaps/internode-100.png',
												 'pixmaps/internode-u0.png',
												 'pixmaps/internode-u25.png',
												 'pixmaps/internode-u75.png',
												 'pixmaps/internode-u100.png',
												 'pixmaps/internode-x.png',
												 'pixmaps/internode-applet.png',
												 'pixmaps/logo.png']), ]
	  )
