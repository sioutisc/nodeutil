#!/usr/bin/env python
#
# Internode usage applet for Avant Window Navigator
#
# Copyright (C) 2011  Dale Maggee (antisol [at] antisol [dot] org)
#
# Originally Based on internode Gnome Applet, which is copyright Sam Pohlenz
#	see: http://www.sampohlenz.com/
#
# BSD Licensed. See license.txt for details.

"""

TODO ITEMS:

- make awn applet size icon according to applet size
- abstract away most UI stuff so that it can be used for either awn or gnome-panel

"""

from internode.node_dialog import NodeDialog_Config
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
		log("Internode AWN Applet - Init")

		#awnlib applet object...
		self.applet = applet

		#HOWTO: show a notification:
		#self.notification = applet.notify.create_notification("Alert", NodeIcons.logo, "dialog-warning", 20)
		#self.notification.show()
		s = applet.get_size()
		applet.set_icon_pixbuf(NodeIcons.icons["x"].scale_simple(s,s,gtk.gdk.INTERP_HYPER))
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
		if not self.nodeutil.load_prefs():
			self.show_prefs()

		#setup a main dialog for detailed info...
		dialog = applet.dialog.new("main")
		self.main_dialog = NodeDialog_Main(self.nodeutil,dialog)

		self.main_dialog.on_refresh_click(self.update)

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

		#force nodeutil to retrieve immediately...
		self.nodeutil.update(True)

		log("Init Complete")
		#self.show_alert("Some text");

	def show_alert(self,text):
		#TODO: set text on the alert
		self.alert.show_all()

	def	close_alert(self, widget = None, data = None):
		self.alert.hide()

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

			tiptext = "Internode usage for: %s\n%.2f / %iMB %s\n%i %s (%i MB / day) remaining\nLast Update: %s ago" % \
				(self.nodeutil.username,usage, self.nodeutil.quota, status, self.nodeutil.daysleft,
					daystring,self.nodeutil.mbperday,friendly_time(time.time() - self.nodeutil.time))

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

		#self.applet.set_icon_pixbuf(icon)

		#ai = self.applet.get_icon()
		#scale icon...
		s = self.applet.get_size()
		self.applet.set_icon_pixbuf(icon.scale_simple(s,s,gtk.gdk.INTERP_HYPER))
		#ai.set_from_pixbuf(icon.scale_simple(s,s,gtk.gdk.INTERP_HYPER)) #INTERP_BILINEAR

	def show_graph(self, widget = None, data = None):
		"""
		Displays the graph window
		"""
		graph_window = NodeDialog_Chart(self.nodeutil)


	def on_clicked(self, widget):
		self.main_dialog.notebook.set_current_page(0)
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

		global debug
		if debug:
			menu.insert(gtk.SeparatorMenuItem(), 5)

			chart_item = gtk.MenuItem("Die")
			chart_item.connect("activate",self.exit)
			menu.insert(chart_item,6)

	def exit(self,widget):
		if widget:
			log("User requested exit")
		sys.exit(666)

	def show_prefs(self, widget = None, data = None):
		"""
		Displays the Preferences dialog
		"""
		
		NodeDialog_Config(self.nodeutil)
		
if __name__ == "__main__":
	awnlib.init_start(InternodeAwnApp, {"name": applet_name,
		"short": "Internode Usage Meter",
		"version": applet_version,
		"description": applet_description,
		"logo": NodeIcons.logo_path,
		"author": "Dale Maggee",
		"copyright-year": 2011,
		"authors": ["Dale Maggee", "Sam Pohlenz"]})
