#!/usr/bin/env python
#
# Internode usage applet for Avant Window Navigator
#
# Copyright (C) 2011  Dale Maggee (antisol [at] internode [dot] on [dot] net)
#
# Originally Based on internode Gnome Applet, which is copyright Sam Pohlenz
#	see: http://www.users.on.net/~spohlenz/internode/
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.	If not, see <http://www.gnu.org/licenses/>.

"""

TODO ITEMS:

- try to remove constants.py - figure out paths dynamically (?)
- make awn applet size icon according to applet size
- abstract away most UI stuff so that it can be used for either awn or gnome-panel

"""

from internode.node_dialog import *
import time
import sys
import os

try:
	import gtk
	import gtk.glade
	import gtk.gdk as gdk
	#gtk.gdk.threads_init()
except ImportError:
	print "Failed to open GTKGlade libraries."
	print "Please ensure they are installed correctly."
	sys.exit(1)

try:
	#import gnome.ui
	import gconf
	import gobject
except ImportError:
	print "Failed to open GNOME libraries."
	print "Please ensure they are installed correctly."
	sys.exit(1)

try:
	import awn
	from awn.extras import awnlib
except ImportError:
	print "Failed to open AWN libraries."
	print "Please ensure they are installed correctly"
	sys.exit(1)

from internode.nodeutil import *

from internode.node_dialog import *

applet_name = "Internode Usage Meter"
applet_version = "0.0.2"
applet_description = "Monitors your Internode ADSL usage"

#how often (mins) should we update?
update_interval = 90

class InternodeAwnApp:
	def __init__(self, applet):
		"""
		Applet Init
		"""
		log("---------------------------------------------------")
		log("Internode Applet - Init")

		#awnlib applet object...
		self.applet = applet

		#gconf client for retrieving gnome settings
		self.gconf_client = gconf.client_get_default()

		#HOWTO: show a notification:
		#self.notification = applet.notify.create_notification("Alert", NodeIcons.logo, "dialog-warning", 20)
		#self.notification.show()

		#TODO: Replace this with a better way(tm) to do config
		self.ui_dir = os.path.dirname(__file__)
		#self.pixmap_dir = os.path.join(self.ui_dir, 'pixmaps')

		applet.set_icon_pixbuf(NodeIcons.icons["x"])

		#tooltip...
		applet.set_tooltip_text("Internode Usage Meter")

		#nodeutil...
		self.nodeutil = NodeUtil()
		self.nodeutil.user_agent_text = "AWN Applet"

		alertdlg = applet.dialog.new("UsageAlert")
		self.alert = NodeDialog_UsageAlert(self.nodeutil,alertdlg,None,None,True)

		#check for a new version
		latest = self.nodeutil.check_version()
		if float(VERSION) < latest:
			log("A New Version of Nodeutils is available!")
			dlg = applet.dialog.new("Alert")
			markup = "<b>A New version of the Internode Usage Meter is available!</b>\nversion %02.1f is out, get it now!" % latest
			NodeDialog_Alert(self.nodeutil,dlg,"Internode Usage Meter",markup)
			#self.alert.show("A New Version (v%02.1f) of Nodeutils is available!" % latest,False)
			
		#self.nodeutil.on_status_change(self.status_changed)

		#icon text overlay for displaying percentage...
		self.overlay = awn.OverlayText()
		self.overlay.props.gravity = gtk.gdk.GRAVITY_SOUTH
		self.overlay.props.font_sizing = 18
		self.overlay.props.text = "??%"
		self.overlay.props.active = False
		applet.add_overlay(self.overlay)

		#icon throbber for indicating 'fetching' status...
		self.throbber = awn.OverlayThrobber()
		self.throbber.props.scale = 0.75
		self.throbber.props.gravity = gtk.gdk.GRAVITY_SOUTH_EAST
		self.throbber.props.apply_effects = True
		self.throbber.props.active = True
		applet.add_overlay(self.throbber)

		#get preferences...
		self.load_prefs()

		#setup a main dialog for detailed info...
		dialog = applet.dialog.new("main")
		self.main_dialog = NodeDialog_Main(self.nodeutil,dialog)

		self.main_dialog.on_refresh_click(self.update)

		#self.main_dialog.show()

		ic = self.main_dialog.get_widget("icon")
		ic.set_from_pixbuf(NodeIcons.logo)

		self.setup_context_menu()

		applet.connect("clicked", self.on_clicked)

		#we can now easily popup an alert with the likes of:
		#	self.alert.set_text("Yo Momma!")
		#	self.alert.show()
		#or, more simply:
		#	self.alert.show('MERT!')

		#applet.timing.register(self.update, update_interval * 60)

		#we register an update function to run every second.
		#	the update function only updates the gui, and
		#	every once in a while triggers the nodeutil update thread
		applet.timing.register(self.update, 2)
		applet.timing.delay(self.update, 1.0)

		#self.nodeutil.update()

		log("Init Complete")
		#self.show_alert("Some text");

	#def status_changed(self):
	#	log("-------------------------------------------------------")
	#	log("Status is: %s (%s)" % (self.nodeutil.status, self.nodeutil.error))
	#	#self.update()

	def show_alert(self,text):
		#TODO: set text on the alert
		self.alert.show_all()

	def	close_alert(self, widget = None, data = None):
		self.alert.hide()

	def load_prefs(self):
		"""
		Reads the username and password from the GConf registry
		"""

		log("Loading Preferences")

		username = self.gconf_client.get_string("/apps/internode-applet/username")
		password = self.gconf_client.get_string("/apps/internode-applet/password")
		show_used = self.gconf_client.get_bool("/apps/internode-applet/show_used")

		if username == None or password == None:
			if username == None:
				username = ""
			if password == None:
				password = ""
			log("missing preferences! showing dialog...")
			self.show_prefs()
		else:
			self.nodeutil.username = username
			self.nodeutil.password = password
			self.nodeutil.show_used = show_used
			#self.update()
			#self.set_timeout(True)


	def update(self, widget = None, data = None):
		"""
		Updates the awn applet display.

		Note that while this function calls nodeutil.update() regularlu (every 2s),
			nodeutil will only spawn an update thread every half hour, unless force
			is True (i.e: the timing of the fetch is usually handled by nodeutil, not here)

		"""

		#set applet image according to status
		self.update_image()

		#we only read this once (to prevent odd states where status changes while we're updating)
		status = self.nodeutil.status

		#if we're responding to a signal (i.e: click on 'update'), force nodeutil to update...
		force = True if widget else False
		
		#when we're in an error state, force a retry after 10 mins.
		if (status == "Error") and (
			(time.time() - self.nodeutil.time) > 600):
				force = True
				
		self.nodeutil.update(force)

		#now that we've called nodeutil.update, we update the display...
		if status == "Updating":
			self.overlay.props.active = False
			self.throbber.props.active = True
			tiptext = "Updating..."

		elif status == "OK":
			self.throbber.props.active = False
			self.update_image()

			if self.nodeutil.show_used:
				percent = self.nodeutil.percent_used
				usage = self.nodeutil.used
				status = "used"
			else:
				percent = self.nodeutil.percent_remaining
				usage = self.nodeutil.remaining
				status = "remaining"

			if self.nodeutil.daysleft == 1:
				daystring = 'day'
			else:
				daystring = 'days'

			rate_per_day = self.nodeutil.remaining / self.nodeutil.daysleft

			tiptext = "Internode usage for: %s\n%.2f / %iMB %s\n%i %s (%i MB / day) remaining\nLast Update: %s ago" % \
				(self.nodeutil.username,usage, self.nodeutil.quota, status, self.nodeutil.daysleft,
					daystring,rate_per_day,friendly_time(time.time() - self.nodeutil.time))

			self.overlay.props.text = "%i%%" % percent
			self.main_dialog.refresh()
						
			"""

			#scroll graph to the end of the data...
			#start = len(self.nodeutil.history) - (self.graph.days-1)
			self.graph.fill_data()
			#log("Start: %2d" % start)

			#self.graph.start = start
			#self.graph.end = len(self.nodeutil.history)

			"""

			self.overlay.props.active = True

			#log("Updated OK")

		elif status == "Error":
			#log("Update error: %s" % self.nodeutil.error)
			tiptext = self.nodeutil.error
			self.overlay.props.active = False
			self.throbber.props.active = False
			self.update_image()

		else:
			#self.label.set_text("??%")
			log("Unknown NodeUtil Status: %s" % self.nodeutil.status)
			tiptext = "??"
			self.overlay.props.active = False
						

		#self.tooltips.set_tip(self.eventbox, tiptext)
		self.applet.set_tooltip_text(tiptext)

		# Return true so the GTK timeout will continue
		return True


	def update_image(self):
		"""
		Sets the icon to the appropriate image.
		"""
		#log("update_image status: '%s'" % self.nodeutil.status)

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

		self.applet.set_icon_pixbuf(icon)

	def show_graph(self, widget = None, data = None):
		"""
		Displays the graph window
		"""
		graph_window = NodeDialog_Chart(self.nodeutil)


	def on_clicked(self, widget):
		pass
		#log("Clicked")
		#self.notebook.set_current_page(0)
		#self.graph.graph.refresh()


	def setup_context_menu(self):
		"""
		Creates the context menu
		"""

		menu = self.applet.dialog.menu
		setup_item = gtk.MenuItem("Preferences")
		setup_item.connect("activate", self.show_prefs)
		menu.insert(setup_item, 2)

		chart_item = gtk.MenuItem("Chart...")
		chart_item.connect("activate",self.show_graph)
		menu.insert(chart_item,3)

		chart_item = gtk.MenuItem("Refresh")
		chart_item.connect("activate",self.update)
		menu.insert(chart_item,4)

		if DEBUG:
			menu.insert(gtk.SeparatorMenuItem(), 5)

			chart_item = gtk.MenuItem("Die")
			chart_item.connect("activate",self.exit)
			menu.insert(chart_item,6)

	def exit(self,widget):
		sys.exit(666)


	def write_prefs(self):
		"""
		Writes the username and password to the GConf registry
		"""

		self.gconf_client.set_string("/apps/internode-applet/username", self.nodeutil.username)
		self.gconf_client.set_string("/apps/internode-applet/password", self.nodeutil.password)
		self.gconf_client.set_bool("/apps/internode-applet/show_used", self.nodeutil.show_used)


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
			#self.update()

		preferences.destroy()


if __name__ == "__main__":
	awnlib.init_start(InternodeAwnApp, {"name": applet_name,
		"short": "Internode Usage Meter",
		"version": applet_version,
		"description": applet_description,
		"logo": NodeIcons.logo_path,
		"author": "Dale Maggee",
		"copyright-year": 2011,
		"authors": ["Dale Maggee", "Sam Pohlenz"]})
