#!/usr/bin/env python

###########
# Imports #
###########

import sys

import pygtk
pygtk.require('2.0')

import gtk

import internode

if internode.constants.INTERNODE_GNOMEAPPLET == 'gnomeapplet':
	import gnomeapplet
else:
	import gnome.applet
	gnomeapplet = gnome.applet

########################
# Function Definitions #
########################

def internode_factory(applet, iid):
	"""
	Creates an Internode Usage Meter Applet
	"""

	internode.InternodeMeter(applet, iid)
	return True



if len(sys.argv) == 2 and sys.argv[1] == "--window":
	# Launch the applet in its own window
	main_window = gtk.Window(gtk.WINDOW_TOPLEVEL)
	main_window.set_title("Internode")
	main_window.connect("destroy", gtk.main_quit)

	app = gnomeapplet.Applet()
	internode_factory(app, None)
	app.reparent(main_window)
	main_window.show_all()

	gtk.main()
	sys.exit()
else:
	# Launch the applet through the bonobo interfaces (as a panel applet)
	gnomeapplet.bonobo_factory("OAFIID:InternodeUsageMeterApplet_Factory",
		gnomeapplet.Applet.__gtype__, "internode", "0", internode_factory)

