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


###########
# Imports #
###########

import sys
import os

from constants import *

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

if INTERNODE_GNOMEAPPLET == 'gnomeapplet':
	import gnomeapplet
else:
	import gnome.applet
	gnomeapplet = gnome.applet

from nodeutil import NodeUtil, UpdateError
from history_window import HistoryWindow


#####################
# Class Definitions #
#####################

class InternodeMeter:
	"""
	Main class of the GNOME Internode Usage Meter Panel Applet.
	"""

	#ui_dir = os.path.join(INTERNODE_PREFIX, 'share', 'internode')
	#DM: use temp path
	ui_dir = '/home/antisol/Downloads/internode-applet-1.7'

	pixmap_dir = os.path.join(ui_dir, 'pixmaps') 

	def __init__(self, applet, iid):
		"""
		Initialises the usage meter
		"""

		# Initialize GConf
		self.gconf_client = gconf.client_get_default()

		# Initialize images
		self.init_images()

		# Initialize GTK widgets
		self.image = gtk.Image()
		self.image.set_from_pixbuf(self.icons["x"])
		self.label = gtk.Label("??%")
		self.eventbox = gtk.EventBox()
		self.hbox = gtk.HBox()
		self.tooltips = gtk.Tooltips()
	
		# Add widgets to applet
		self.hbox.add(self.image)
		self.hbox.add(self.label)
		self.eventbox.add(self.hbox)

		applet.add(self.eventbox)

		# Load the right-click menu
		f = open(self.ui_dir + "/menu.xml", 'r')
		menu = f.read()	
		applet.setup_menu(menu,
						 [("Preferences", self.show_prefs),
						  ("About", self.show_about),
						  ("Graph", self.show_graph),
						  ("Update", self.update)],
						  None)
		
		applet.show_all()

		# Initialize Internode Usage Checker
		self.nodeutil = NodeUtil()
		self.load_prefs()

		# Connect background callback
		applet.connect("change_background", self.change_background)


	def init_images(self):
		"""
		Initialises the icons and images used by the usage meter
		"""

		self.icons = {}
		
		# Show Percentage Remaining icons
		self.icons["0"] = gtk.gdk.pixbuf_new_from_file(self.pixmap_dir + "/internode-0.png")
		self.icons["25"] = gtk.gdk.pixbuf_new_from_file(self.pixmap_dir + "/internode-25.png")
		self.icons["50"] = gtk.gdk.pixbuf_new_from_file(self.pixmap_dir + "/internode-50.png")
		self.icons["75"] = gtk.gdk.pixbuf_new_from_file(self.pixmap_dir + "/internode-75.png")
		self.icons["100"] = gtk.gdk.pixbuf_new_from_file(self.pixmap_dir + "/internode-100.png")
		self.icons["x"] = gtk.gdk.pixbuf_new_from_file(self.pixmap_dir + "/internode-x.png")

		# Show Percentage Used icons
		self.icons["u0"] = gtk.gdk.pixbuf_new_from_file(self.pixmap_dir + "/internode-u0.png")
		self.icons["u25"] = gtk.gdk.pixbuf_new_from_file(self.pixmap_dir + "/internode-u25.png")
		self.icons["u50"] = self.icons["50"]
		self.icons["u75"] = gtk.gdk.pixbuf_new_from_file(self.pixmap_dir + "/internode-u75.png")
		self.icons["u100"] = gtk.gdk.pixbuf_new_from_file(self.pixmap_dir + "/internode-u100.png")

		# About logo
		self.logo = gtk.gdk.pixbuf_new_from_file(self.pixmap_dir + "/logo.png")


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
				self.image.set_from_pixbuf(self.icons[prefix + "100"])
			elif percent > 62:
				self.image.set_from_pixbuf(self.icons[prefix + "75"])
			elif percent > 37:
				self.image.set_from_pixbuf(self.icons[prefix + "50"])
			elif percent > 12:
				self.image.set_from_pixbuf(self.icons[prefix + "25"])
			else:
				self.image.set_from_pixbuf(self.icons[prefix + "0"])
		else:
			# Show error image
			self.image.set_from_pixbuf(self.icons["x"])


	def set_timeout(self, enable = True, interval = 5):
		"""
		Sets or unsets the timeout to automatically update the usage meter
		"""

		if enable:
			self.timeout = gobject.timeout_add(interval, self.update, self)
		else:
			gobject.timeout_remove(self.timeout)
		

	def update(self, widget = None, data = None):
		"""
		Fetches the latest usage information and updates the display
		"""

                tiptext = "??"

		#try:
                self.update_image()
                self.nodeutil.update()

                if self.nodeutil.status == "OK":
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

                    tiptext = "%.2f/%iMB %s\n%i %s remaining" % \
                            (usage, self.nodeutil.quota, status, self.nodeutil.daysleft, daystring)

                elif self.nodeutil.status == "Updating":
                    tiptext = "Updating..."
                    
                elif self.nodeutil.status == "Error":
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
			None, self.logo)

		result = about.run()
		
		
        def show_graph(self, widget = None, data = None):
                """
                Displays the graph window
                """
                graph_window = HistoryWindow(self.nodeutil, self.ui_dir)

	
	def show_prefs(self, widget = None, data = None):
		"""
		Displays the Preferences dialog
		"""

		# Load and show the preferences dialog box
		glade = gtk.glade.XML(self.ui_dir + "/internode-applet.glade", "preferences")
		preferences = glade.get_widget("preferences")
		
		# Set the input text to the current username/password values
		usertext = glade.get_widget("username")
		usertext.set_text(self.nodeutil.username)
		passtext = glade.get_widget("password")
		passtext.set_text(self.nodeutil.password)
		
		# Set the used/remaining radio buttons
		used = glade.get_widget("show_used")
		used.set_active(self.nodeutil.show_used)
		
		result = preferences.run()
		
		if result == gtk.RESPONSE_OK:
			# Update username and password
			self.nodeutil.username = usertext.get_text()
			self.nodeutil.password = passtext.get_text()
			self.nodeutil.show_used = used.get_active()
			self.write_prefs()
			self.update()

		preferences.destroy()
	
	
	def write_prefs(self):
		"""
		Writes the username and password to the GConf registry
		"""
		
		self.gconf_client.set_string("/apps/internode-applet/username", self.nodeutil.username)
		self.gconf_client.set_string("/apps/internode-applet/password", self.nodeutil.password)
		self.gconf_client.set_bool("/apps/internode-applet/show_used", self.nodeutil.show_used)


	def load_prefs(self):
		"""
		Reads the username and password from the GConf registry
		"""

		username = self.gconf_client.get_string("/apps/internode-applet/username")
		password = self.gconf_client.get_string("/apps/internode-applet/password")
		show_used = self.gconf_client.get_bool("/apps/internode-applet/show_used")
		
		if username == None or password == None:
			if username == None:
				username = ""
			if password == None:
				password = ""

			self.show_prefs()
		else:
			self.nodeutil.username = username
			self.nodeutil.password = password
			self.nodeutil.show_used = show_used
			self.update()
			self.set_timeout(True)
		

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
