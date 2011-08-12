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

import time
import sys
import os

try:
	import gtk
	import gtk.glade
	import gtk.gdk as gdk
except ImportError:
	print "Failed to open GTKGlade libraries."
	print "Please ensure they are installed correctly."
	sys.exit(1)

try:
	#import gnome.ui
	import gconf
	#import gobject
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
	
from internode.nodeutil import NodeUtil, UpdateError
from internode.history_window import HistoryWindow

applet_name = "Internode Usage Meter"
applet_version = "0.0.2"
applet_description = "Monitors your Internode ADSL usage"

# Or provide the path to your own logo:
applet_logo = os.path.join(os.path.dirname(__file__), "pixmaps","logo.png")

#how often (mins) should we update?
update_interval = 90

#debugging mode. When this is on, log() does something,
#	and there is a 'die' menu item for easy reloading during testing
DEBUG=True

class InternodeAwnApp:
	def __init__(self, applet):
		"""
		Applet Init
		"""

		self.log("Internode Applet - Init")

		self.applet = applet
		# set icon
		self.applet.set_icon_name("internode-x")

		self.gconf_client = gconf.client_get_default()

		self.notification = applet.notify.create_notification("Alert", applet_logo, "dialog-warning", 20)
		#self.notification.show()

		self.ui_dir = os.path.dirname(__file__)
		self.pixmap_dir = os.path.join(self.ui_dir, 'pixmaps')

		# set applet icon...
		icon = gdk.pixbuf_new_from_file(os.path.join(self.pixmap_dir,"internode-x.png"))

		applet.set_icon_pixbuf(icon)

		self.init_images()

		applet.set_tooltip_text("Internode Usage Meter")

		self.nodeutil = NodeUtil()

		self.overlay = awn.OverlayText()
		self.overlay.props.gravity = gtk.gdk.GRAVITY_SOUTH
		self.overlay.props.font_sizing = 18
		self.overlay.props.text = "??%"
		self.overlay.props.active = False
		applet.add_overlay(self.overlay)

		self.throbber = awn.OverlayThrobber()
		self.throbber.props.scale = 0.75
		self.throbber.props.gravity = gtk.gdk.GRAVITY_SOUTH_EAST
		self.throbber.props.apply_effects = True
		self.throbber.props.active = True
		applet.add_overlay(self.throbber)

		self.load_prefs()
		
		#setup a main dialog for detailed info...
		
		dialog = applet.dialog.new("main")
		
		stats = gtk.glade.XML(os.path.join(self.ui_dir,"internode-applet.glade"), "details_vbox")
		#stats.get_widget("graph_vbox").reparent(dialog)
		details = stats.get_widget("details_vbox")
		
		#vars for controls on the dialog...
		self.progressbar = stats.get_widget("progressbar")
		self.percent = stats.get_widget("percentage")
		self.usage = stats.get_widget("usage")
		
		notebook = stats.get_widget("notebook")
		
		#add a history window to the details pane...
		graph_window = HistoryWindow(self.nodeutil, self.ui_dir,notebook)
		
		#request a graph taller than 2px...
		graph_window.graph.set_size_request(0,200)
		
		self.graph = graph_window
		
		notebook.set_tab_label_text(self.graph.vbox, "Chart")
		
		dialog.add(details)
		
		alert = applet.dialog.new("alert")
		alertglade = gtk.glade.XML(os.path.join(self.ui_dir,"internode-applet.glade"), "alert_vbox")
		box = alertglade.get_widget("alert_vbox")
		alertglade.get_widget("btnOK").connect("clicked",self.close_alert)
		alertglade.get_widget("btnBuyData").connect("clicked",self.buy_data)

		#mert = gtk.Label("mert")
		alert.add(box)
		
		self.alert = alert
		
		ic = stats.get_widget("icon")
		#print ic.__class__.__name__
		#print dir(ic)
		ic.set_from_pixbuf(self.logo)
		
		self.dialog = dialog
		
		self.setup_context_menu()
		
		#commented out - awnlib does this automagically
		#applet.connect("clicked", self.on_clicked)

		#icon = applet.get_icon()
		#effect = awn.Effects(icon)

		applet.timing.register(self.update, update_interval * 60)
		applet.timing.delay(self.update, 1.0)

		self.log("Init Complete")
		self.show_alert();
		
	def show_alert(self):
		self.alert.show_all()
	
	def	close_alert(self, widget = None, data = None):
		self.alert.hide()
		
	def buy_data(self, widget = None, data = None):
		os.spawnlp(os.P_NOWAIT,"gnome-www-browser","gnome-www-browser",
			"https://secure.internode.on.net/myinternode")
		self.close_alert(widget,data)

	def log(self,message):
		"""
		Logs a message to the logfile and/or screen, depending on DEBUG settings
		"""

		if DEBUG:
			print "internode-applet: %s" % message

	def load_prefs(self):
		"""
		Reads the username and password from the GConf registry
		"""

		self.log("Loading Preferences")

		username = self.gconf_client.get_string("/apps/internode-applet/username")
		password = self.gconf_client.get_string("/apps/internode-applet/password")
		show_used = self.gconf_client.get_bool("/apps/internode-applet/show_used")

		if username == None or password == None:
			if username == None:
				username = ""
			if password == None:
				password = ""
			self.log("missing preferences! showing dialog...")
			self.show_prefs()
		else:
			self.nodeutil.username = username
			self.nodeutil.password = password
			self.nodeutil.show_used = show_used
			#self.update()
			#self.set_timeout(True)


	def update(self, widget = None, data = None):
		"""
		Fetches the latest usage information and updates the display
		"""

		self.log("Updating...")

		#self.notification.show()
		self.overlay.props.active = False
		self.throbber.props.active = True
		try:
			self.nodeutil.update()
			self.update_image()

			if self.nodeutil.show_used:
				percent = self.nodeutil.percent_used
				usage = self.nodeutil.used
				status = "used"
			else:
				percent = self.nodeutil.percent_remaining
				usage = self.nodeutil.remaining
				status = "remaining"

			#self.label.set_text("%i%%" % percent)

			if self.nodeutil.daysleft == 1:
				daystring = 'day'
			else:
				daystring = 'days'

			tiptext = "Internode usage for: %s\n%.2f / %iMB %s\n%i %s (%i MB / day) remaining\nLast Update: %s" % \
				(self.nodeutil.username,usage, self.nodeutil.quota, status, self.nodeutil.daysleft,
					daystring,self.nodeutil.remaining / self.nodeutil.daysleft,time.ctime(self.nodeutil.time))

			self.overlay.props.text = "%i%%" % percent
			self.overlay.props.active = True
			
			self.progressbar.set_fraction(percent / float(100))
			
			self.percent.set_markup('<span size="16000"><i>%3d%%</i></span>' % percent)
			
			self.usage.set_markup('<span size="16000"><b>%2d</b>MB / <b>%2d</b>MB</span>' % (usage,self.nodeutil.quota))

			#scroll graph to the end of the data...
			#start = len(self.nodeutil.history) - (self.graph.days-1)
			self.graph.fill_data()
			#self.log("Start: %2d" % start)
			
			#self.graph.start = start
			#self.graph.end = len(self.nodeutil.history)

			self.log("Updated OK")

		except UpdateError:
			# An error occurred
			#self.label.set_text("??%")
			self.log("Update error: %s" % self.nodeutil.error)
			tiptext = self.nodeutil.error
			self.overlay.props.active = False
			self.update_image()

		#self.tooltips.set_tip(self.eventbox, tiptext)
		self.applet.set_tooltip_text(tiptext)

		self.throbber.props.active = False

		# Return true so the GTK timeout will continue
		return True


	def update_image(self):
		"""
		Sets the icon to the appropriate image.
		"""

		if self.nodeutil.error == "":
			if self.nodeutil.show_used:
				percent = self.nodeutil.percent_used
				prefix = "u"
			else:
				percent = self.nodeutil.percent_remaining
				prefix = ""

			# No error
			if percent > 87:
				icon = self.icons[prefix + "100"]
			elif percent > 62:
				icon = self.icons[prefix + "75"]
			elif percent > 37:
				icon = self.icons[prefix + "50"]
			elif percent > 12:
				icon = self.icons[prefix + "25"]
			else:
				icon = self.icons[prefix + "0"]
		else:
			# Show error image
			icon = self.icons["x"]

		self.applet.set_icon_pixbuf(icon)


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
		self.logo = gtk.gdk.pixbuf_new_from_file(self.pixmap_dir + "/internode-applet.png")


	def show_graph(self, widget = None, data = None):
		"""
		Displays the graph window
		"""
		graph_window = HistoryWindow(self.nodeutil, self.ui_dir)


	#def on_clicked(self, widget):
		#self.log("Clicked")
		
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
			self.update()

		preferences.destroy()


if __name__ == "__main__":
	awnlib.init_start(InternodeAwnApp, {"name": applet_name,
		"short": "Internode Usage Meter",
		"version": applet_version,
		"description": applet_description,
		"logo": applet_logo,
		"author": "Dale Maggee",
		"copyright-year": 2011,
		"authors": ["Dale Maggee", "Sam Pohlenz"]})
