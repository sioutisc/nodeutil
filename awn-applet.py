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
- make nodeutil spawn a thread for updating
- make awn applet size icon according to applet size
- abstract away most UI stuff so that it can be used for either awn or gnome-panel

"""

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
from internode.history_window import HistoryWindow

from internode.node_dialog import *

applet_name = "Internode Usage Meter"
applet_version = "0.0.2"
applet_description = "Monitors your Internode ADSL usage"

# Or provide the path to your own logo:
applet_logo = os.path.join(os.path.dirname(__file__), "pixmaps","logo.png")

#how often (mins) should we update?
update_interval = 90

#debugging mode. When this is on, log() does something,
#	and there is a 'die' menu item for easy reloading during testing
#DEBUG=True

#def log(text):
#	"""
#	Log a message with a timestamp
#		does nothing in debug mode
#	"""
#	if DEBUG:
#		print time.strftime("%Y-%m-%d %H:%M:%S") + " " + text


class InternodeAwnApp:
	def __init__(self, applet):
		"""
		Applet Init
		"""

		log("Internode Applet - Init")

                #awnlib applet object...
		self.applet = applet

                #gconf client for retrieving gnome settings
		self.gconf_client = gconf.client_get_default()

                #HOWTO: show a notification:
		#self.notification = applet.notify.create_notification("Alert", applet_logo, "dialog-warning", 20)
		#self.notification.show()

                #TODO: Replace this with a better way(tm) to do config
		self.ui_dir = os.path.dirname(__file__)
		self.pixmap_dir = os.path.join(self.ui_dir, 'pixmaps')

		#log("UI Dir: '%s'" % self.ui_dir)

		# set applet icon...
		self.init_images()

		icon = self.icons["x"]
                # or from a file:
		#icon = gdk.pixbuf_new_from_file(os.path.join(self.pixmap_dir,"internode.svg"))

		applet.set_icon_pixbuf(icon)

                #tooltip...
		applet.set_tooltip_text("Internode Usage Meter")

                #nodeutil...
		self.nodeutil = NodeUtil()

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


                #old code (move to NodeDialog):
                """
		
                #code for the alert editor:
                
		list = gtk.ListStore(int,str)
		list.append([100,"You be capped!"])
		list.append([90,"Internode usage is critically high!"])
		list.append([75,"Three Quarters of your Internode data has been used!"])
		list.append([50,"You've used half your Internode data!"])
		list.append([0,"A New Month!"])

		##alertlist = stats.get_widget("alertlist")
		#alertlist = gtk.TreeView(list)
		alerts = gtk.glade.XML(os.path.join(self.ui_dir,"internode-applet.glade"), "alerts_vbox")
		alerts_box = alerts.get_widget("alerts_vbox")
		alertlist = alerts.get_widget("alert_list")
		alertlist.set_model(list)
		alertlist.set_rules_hint(True)

		rendererText = gtk.CellRendererText()
		column = gtk.TreeViewColumn("At %", rendererText, text=0)
		column.set_sort_column_id(0)
		alertlist.append_column(column)

		rendererText = gtk.CellRendererText()
		column = gtk.TreeViewColumn("Message", rendererText, text=1)
		column.set_sort_column_id(1)
		alertlist.append_column(column)

		notebook.append_page(alerts_box)
		notebook.set_tab_label_text(alerts_box, "Alerts")
		##alertlist.realize()

		dialog.add(details)

                """

		ic = self.main_dialog.get_widget("icon")
		ic.set_from_pixbuf(self.logo)

		#self.dialog = dialog
		#self.notebook = notebook

		self.setup_context_menu()

		applet.connect("clicked", self.on_clicked)

		alertdlg = applet.dialog.new("alertdlg")
		self.alert = NodeDialog_Alert(self.nodeutil,"This be an alert!",alertdlg,None,True)

		#we can now easily popup an alert with the likes of:
		#	self.alert.set_text("Yo Momma!")
		#	self.alert.show()
		#or, more simply:
		#	self.alert.show('MERT!')

		#applet.timing.register(self.update, update_interval * 60)
                applet.timing.register(self.update, 5)
		applet.timing.delay(self.update, 1.0)

                self.nodeutil.update()

		log("Init Complete")
		#self.show_alert("Some text");

	def status_changed(self):
		log("-------------------------------------------------------")
		log("Status is: %s (%s)" % (self.nodeutil.status, self.nodeutil.error))
		#self.update()

	def show_alert(self,text):
		#TODO: set text on the alert
		self.alert.show_all()

	def	close_alert(self, widget = None, data = None):
		self.alert.hide()

	def buy_data(self, widget = None, data = None):
		os.spawnlp(os.P_NOWAIT,"gnome-www-browser","gnome-www-browser",
			"https://secure.internode.on.net/myinternode")
		self.close_alert(widget,data)

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
		Fetches the latest usage information and updates the display

		TODO: this should actually just update the awn applet based on the nodeutil's state
		we should never actually need to call nodeutil.update()

		"""

		#log("Updating UI")
		#log(self.nodeutil.status)

                #if self.nodeutil.status == "OK" and (time.time() - 60 > self.nodeutil.time):
                #    log("Calling nodeutil.update()")

                self.update_image()

                if widget or self.nodeutil.status == "Error":
                    #we're responding to a signal, or in an error state -
                    #   force nodeutil to update...
                    force = True
                else:
                    force = False
                    
                self.nodeutil.update(force)

                #we only read this once
                status = self.nodeutil.status

		#self.notification.show()
		if status == "Updating":
			self.overlay.props.active = False
			self.throbber.props.active = True
			tiptext = "Updating..."

		elif status == "OK":
			#self.nodeutil.do_update()
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

			#self.label.set_text("%i%%" % percent)

			if self.nodeutil.daysleft == 1:
				daystring = 'day'
			else:
				daystring = 'days'

			rate_per_day = self.nodeutil.remaining / self.nodeutil.daysleft

			tiptext = "Internode usage for: %s\n%.2f / %iMB %s\n%i %s (%i MB / day) remaining\nLast Update: %s ago" % \
				(self.nodeutil.username,usage, self.nodeutil.quota, status, self.nodeutil.daysleft,
					daystring,rate_per_day,friendly_time(time.time() - self.nodeutil.time))

			self.overlay.props.text = "%i%%" % percent
			#self.overlay.props.active = True

                        self.main_dialog.refresh()
                        
                        """

			self.progressbar.set_fraction(percent / float(100))

			self.percent.set_markup('<span size="16000"><i>%3d%%</i></span>' % percent)

			self.usage.set_markup('<span size="16000"><b>%2d</b> MB / <b>%2d</b> MB</span>' % (usage,self.nodeutil.quota))

			self.heading.set_markup('<span size="12000">Internode Usage for: <b>%s</b></span>' % self.nodeutil.username)

			self.remaining.set_markup('<span size="16000"><b>%2d</b></span> Days remaining' % self.nodeutil.daysleft)

			rate = (self.nodeutil.remaining * 1024) / (self.nodeutil.daysleft * 24 * 60 * 60)

			self.suggested_speed.set_markup('Suggested download rate: <span size="12000"><b>%3.2f</b> KB/s</span>' % rate)

			self.remaining_mb.set_markup('<span size="16000"><b>%2d</b> MB </span>remaining' % self.nodeutil.remaining)
			self.rate_per_day.set_markup('<span size="16000"><b>%2.2f</b> MB / Day</span> remaining' % rate_per_day)

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
			self.update_image()

		else:
			#self.label.set_text("??%")
                        log("Unknown NodeUtil Status: %s" % self.nodeutil.status)
                        tiptext = "??"
                        self.overlay.props.active = False
                        

		#self.tooltips.set_tip(self.eventbox, tiptext)
		self.applet.set_tooltip_text(tiptext)

		#self.throbber.props.active = False

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
		self.logo_large = gtk.gdk.pixbuf_new_from_file(self.pixmap_dir + "/internode.svg")
                #smaller logo
                self.logo = gtk.gdk.pixbuf_new_from_file_at_size(self.pixmap_dir + "/internode.svg", 44, 48)


	def show_graph(self, widget = None, data = None):
		"""
		Displays the graph window
		"""
		graph_window = HistoryWindow(self.nodeutil, self.ui_dir)


	def on_clicked(self, widget):
		log("Clicked")
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
		"logo": applet_logo,
		"author": "Dale Maggee",
		"copyright-year": 2011,
		"authors": ["Dale Maggee", "Sam Pohlenz"]})