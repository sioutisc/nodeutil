#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++#
#                                                                             #
# internode.py - A GNOME ADSL Internode Usage Meter Panel Applet              #
#                                                                             #
# Copyright (C) 2005  Sam Pohlenz <retrix@internode.on.net>                   #
#                                                                             #
# This program is free software; you can redistribute it and/or               #
# modify it under the terms of the GNU General Public License                 #
# as published by the Free Software Foundation; either version 2              #
# of the License, or (at your option) any later version.                      #
#                                                                             #
# This program is distributed in the hope that it will be useful,             #
# but WITHOUT ANY WARRANTY; without even the implied warranty of              #
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the               #
# GNU General Public License for more details.                                #
#                                                                             #
# You should have received a copy of the GNU General Public License           #
# along with this program; if not, write to the Free Software                 #
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA. #
#                                                                             #
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++#

INTERNODE_NAME = 'Internode Usage Meter'
INTERNODE_URL = 'http://www.users.on.net/~antisol/nodeutil'
INTERNODE_COPYRIGHT = '(C) 2011 Dale Maggee'
INTERNODE_DESCRIPTION = 'Applet for monitoring your Internode ADSL usage.'
INTERNODE_AUTHORS = [
	'Dale Maggee <antisol(at)internode(dot)on(dot)net>',
	'Sam Pohlenz <retrix@internode.on.net>',
	'Chris Scobell <chris@thescobells.com>'
	]

###########
# Imports #
###########

from node_dialog import *
import sys
import os

#from constants import *

try:
	if not sys.modules.has_key('gtk'):
		import pygtk
		pygtk.require('2.0')
except ImportError:
	print "Failed to open PyGTK libraries."
	print "Please ensure they are installed correctly."
	sys.exit(1)

try:
	import gtk
	import gtk.glade
	import gtk.gdk
        gtk.gdk.threads_init()
except ImportError:
	print "Failed to open GTKGlade libraries."
	print "Please ensure they are installed correctly."
	sys.exit(1)
	
try:
	import gnome.ui
	import gconf
	import gobject
except ImportError:
	print "Failed to open GNOME libraries."
	print "Please ensure they are installed correctly."
	sys.exit(1)

#import internode.constants
# Test whether we want to import the deprecated gnome.applet or
# the newer gnomeapplet
try:
    import gnomeapplet
    # Use gnomeapplet
    INTERNODE_GNOMEAPPLET = 'gnomeapplet'
except ImportError:
    # Use (deprecated) gnome.applet
    INTERNODE_GNOMEAPPLET = 'gnome.applet'

if INTERNODE_GNOMEAPPLET == 'gnomeapplet':
	#import gnomeapplet
	pass
else:
	import gnome.applet
	gnomeapplet = gnome.applet

from nodeutil import * 

INTERNODE_VERSION = "%2.1f" % VERSION

#####################
# Class Definitions #
#####################

class InternodeMeter:
	"""
	Main class of the GNOME Internode Usage Meter Panel Applet.
	"""

	def __init__(self, applet, iid):
		"""
		Initialises the usage meter
		"""
		log("---------------------------------------------------")
		log("Internode GNOME Applet (%s) - Init" % INTERNODE_GNOMEAPPLET)
		log("%s" % applet)

		# Initialize GConf
		self.gconf_client = gconf.client_get_default()

		self.applet = applet

		# Initialize GTK widgets
		self.image = gtk.Image()
		self.image.expand = True

		self.label = gtk.Label("??%")
		self.eventbox = gtk.EventBox()
		self.hbox = gtk.HBox()
		self.hbox.expand = False
		self.hbox.padding = 2
		self.tooltips = gtk.Tooltips()
	
		# Add widgets to applet
		self.hbox.add(self.image)
		self.hbox.add(self.label)
		self.eventbox.add(self.hbox)

		applet.add(self.eventbox)

		icon = NodeIcons.icons["x"]
		#s = self.applet.get_size() - 2
		s = self.applet.get_size()
		#log("Reported size: %s" % s)
		s2 = s - (s % 8) - 8
		if s2 <= (s - 3):
			s = s2
		if s < 25: s= 25
		#log("s2: %s" % s)
		self.image.set_from_pixbuf(icon.scale_simple(s,s,gtk.gdk.INTERP_HYPER))
		
		#hardcoded menu XML:
		menu = """
			<popup name="button3">
			<menuitem name="Item 1" verb="Preferences" label="_Preferences..."
				pixtype="stock" pixname="gtk-properties"/>
			<menuitem name="Item 2" verb="About" label="_About..."
				pixtype="stock" pixname="gnome-stock-about"/>
			<menuitem name="Item 3" verb="Graph" label="_Graph..."/>
			<menuitem name="Item 4" verb="Update" label="_Update"/>
			</popup>
		"""
		
		applet.setup_menu(menu,
						 [("Preferences", self.show_prefs),
						  ("About", self.show_about),
						  ("Graph", self.show_graph),
						  ("Update", self.update)],
						  None)
		
		applet.show_all()

		# Initialize Internode Usage Checker
		self.nodeutil = NodeUtil()
		self.nodeutil.user_agent_text = "GNOME Applet"
		if not self.nodeutil.load_prefs():
			self.show_prefs()
		self.set_timeout(True)
		self.dialog = None
		applet.connect("button-press-event",self.on_clicked)
		applet.connect("change-size",self.on_resize)

		# Connect background callback
		applet.connect("change_background", self.change_background)

		#check for a new version
		latest = self.nodeutil.check_version()
		if float(VERSION) < latest:
			log("A New Version of Nodeutils is available!")
			markup = "<b>A New version of the Internode Usage Meter is available!</b>\nversion %02.1f is out, get it now!" % latest
			NodeDialog_Alert(self.nodeutil,None,"Internode Usage Meter",markup)
			#self.alert.show("A New Version (v%02.1f) of Nodeutils is available!" % latest,False)

		#update nodeutil...
		self.nodeutil.update(True)
		log("Init Complete")

	def on_resize(self, applet, new_size):
		log("Resize event (%s)" % new_size)

	def update_image(self):
		"""
		Sets the icon to the appropriate image.
		"""

		if self.nodeutil.status == "OK":
			if self.nodeutil.show_used:
				percent = self.nodeutil.percent_used
				prefix = "u"
			else:
				percent = self.nodeutil.percent_remaining
				prefix = ""
			
			# No error
			if percent > 87:
				icon = NodeIcons.icons[prefix + "100"]
			elif percent > 62:
				icon = NodeIcons.icons[prefix + "75"]
			elif percent > 37:
				icon = NodeIcons.icons[prefix + "50"]
			elif percent > 12:
				icon = NodeIcons.icons[prefix + "25"]
			else:
				icon = NodeIcons.icons[prefix + "0"]
		else:
			# Show error image
			icon = NodeIcons.icons["x"]

		#GRRR: This, nor [image|hbox|panel].get_allocation(), gets the actual panel size!
		#	they seem to return only from a list (something like: 24, 36, 48, 64, 80, 128),
		#	and whichever you are closest to, meaning that sometimes 
		#	get_size() returns greater than actual panel height, giving you
		#	a cut-off icon! WTF?!? >:(
		s = self.applet.get_size()
		#log("s1: %s" % s)
		s2 = s - (s % 8) - 8
		if s2 <= s:
			s = s2
		if s < 25: s= 25
		#log("s2: %s" % s)
		self.image.set_from_pixbuf(icon.scale_simple(s,s,gtk.gdk.INTERP_HYPER))

	def set_timeout(self, enable = True, interval = 1000):
		"""
		Sets or unsets the timeout to automatically update the usage meter
		"""

		if enable:
			self.timeout = gobject.timeout_add(interval, self.update, self)
		else:
			gobject.timeout_remove(self.timeout)
		
        def on_clicked(self, widget = None, event = None):
            if event.type == gtk.gdk.BUTTON_PRESS and event.button == 1:
                if not self.dialog:
                    self.dialog = NodeDialog_Main(self.nodeutil)
                    self.dialog.get_widget("icon").set_from_pixbuf(NodeIcons.logo)
                    self.dialog.parent.set_icon(NodeIcons.logo)
                    self.dialog.refresh()
                    self.dialog.on_refresh_click(self.force_update)
                    self.dialog.parent.connect("destroy",self.dialog_closed)
                    self.dialog.show()
                else:
                    self.dialog.parent.destroy()


        def dialog_closed(self,widget = None, data = None):
            self.dialog = None

        def force_update(self,widget = None, data = None):
            self.update(widget, "Force")

	def update(self, widget = None, data = None):
		"""
		Fetches the latest usage information and updates the display
		"""

                #print "update '%s'" % data

                tiptext = "??"
                if data:
                    force = True
                else:
                    force = False
                    
		#try:
                self.update_image()
                self.nodeutil.update(force)

                status = self.nodeutil.status

                if status == "OK":
                    if self.nodeutil.show_used:
                            percent = self.nodeutil.percent_used
                            usage = self.nodeutil.used
                            status = "used"
                    else:
                            percent = self.nodeutil.percent_remaining
                            usage = self.nodeutil.remaining
                            status = "remaining"

                    self.label.set_text("%i%%" % percent)

                    if self.nodeutil.daysleft == 1:
                            daystring = 'day'
                    else:
                            daystring = 'days'

                    self.update_image()

                    if self.dialog:
                        self.dialog.refresh()

                    tiptext = "%.2f/%iMB %s\n%i %s remaining" % \
                            (usage, self.nodeutil.quota, status, self.nodeutil.daysleft, daystring)

                elif status == "Updating":
                    tiptext = "Updating..."
                    
                elif status == "Error":
                    tiptext = "Error: %s" % self.nodeutil.error
                    self.label.set_text("??%")
                    self.update_image()

		#except UpdateError:
		#	# An error occurred
		#	self.label.set_text("??%")
		#	tiptext = self.nodeutil.error
		#	self.update_image()

		self.tooltips.set_tip(self.eventbox, tiptext)
		
		# Return true so the GTK timeout will continue
		return True


	def show_about(self, widget = None, data = None):
		"""
		Displays the About dialog
		"""

		about = gnome.ui.About(INTERNODE_NAME, INTERNODE_VERSION, INTERNODE_COPYRIGHT,
			INTERNODE_DESCRIPTION, INTERNODE_AUTHORS, None,
			None, NodeIcons.logo)

		result = about.run()
		
		
        def show_graph(self, widget = None, data = None):
                """
                Displays the graph window
                """
                graph_window = NodeDialog_Chart(self.nodeutil)

	
	def show_prefs(self, widget = None, data = None):
		"""
		Displays the Preferences dialog
		"""
		NodeDialog_Config(self.nodeutil)

	def change_background(self, applet, bg_type, color, pixmap):
		"""
		Changes the background of the applet when the panel's background changes.
		"""

		applet.set_style(None)
		self.eventbox.set_style(None)
		
		applet.modify_style(gtk.RcStyle())
		self.eventbox.modify_style(gtk.RcStyle())

		if bg_type == gnomeapplet.PIXMAP_BACKGROUND:
			style = applet.get_style()
			style.bg_pixmap[gtk.STATE_NORMAL] = pixmap
			applet.set_style(style)
			self.eventbox.set_style(style)
		elif bg_type == gnomeapplet.COLOR_BACKGROUND:
			applet.modify_bg(gtk.STATE_NORMAL, color)
			self.eventbox.modify_bg(gtk.STATE_NORMAL, color)
