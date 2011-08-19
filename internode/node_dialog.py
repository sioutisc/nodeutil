#!/usr/bin/env python
#
# GTK GUI classes for Internode Applets
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
	import gobject
except ImportError:
	print "Failed to open GNOME libraries."
	print "Please ensure they are installed correctly."
	sys.exit(1)

from nodeutil import *
from history_window import HistoryWindow

def friendly_time(secs):
	
	if secs < 60:
		if int(secs) == 1:
			unit = "second"
		else:
			unit = "seconds"
		return "%1d %s" % (secs,unit)
	elif secs < 3600:
		mins = (secs / 60)
		if int(mins) == 1:
			unit = "minute"
		else:
			unit = "minutes"
		return "%1d %s" % (mins,unit)
	else:
		hrs = (secs / 3600)
		if int(hrs) == 1:
			unit = "hour"
		else:
			unit = "hours"
		
		ret = ("%1d %s" % (hrs,unit))
		if (secs % 3600):
			ret = ret + " and " + friendly_time(secs % 3600)

		return ret

class NodeDialog:
	"""
	Base class for all Internode Dialogs
		The Idea being that you can create a complete, functional dialog with a one-liner
		A parent can be specified, which allows placing a NodeDialog inside another object,
			like an awn dialog or a notebook
	"""
	
	def __init__(self, node, parent = None):
		"""
		creates a new NodeDialog
		@node - nodeutil object
		@parent - a gtk Container (gtk.Window or awn.Dialog)
								if none is specified, the dialog will create a new window
		"""

		self.nodeutil = node

		#subclasses of NodeDialog should populate these:
		self.controls = None
		#controls should usually be a vbox or the like - the main container for all controls
		#	inside the dialog
		self.glade = None
		#glade should be the glade object for the dialog

		#If no parent is provided, the dialog goes into a new GTK Window.
		# If you do this, you'll want to call set_title()
		if parent:
			self.parent = parent
		else:
			self.parent = gtk.Window()

	def show(self):
		"""
		Shows the dialog. this might not do what you'd expect if the
			parent is something unusual
		"""
		self.parent.show_all()

	def close(self, widget = None, data = None):
		"""
		Hides the dialog
				Extra params are so this can be connected to a GTK signal
		"""
		self.parent.hide()
		
	def set_title(self,text):
		"""
		sets the title of the Dialog. Note that the dialog might not have a title,
			in which case this doesn't do much
		Handles different types of containers:
		 - sets the title if parent is a gtk.Window
		 - will one day set tab title if parent is a gtk.Notebook
		"""
		if type(self.parent) == gtk.Window:
			self.parent.set_title(text)
		elif type(self.parent) == gtk.Notebook:
			if self.controls:	#we need at least one child control to do this...
				self.parent.set_tab_label_text(self.controls, text)

	def get_widget(self,widget_name):
		"""
		shortcut to self.glade.get_widget
		"""
		if self.glade:
			return self.glade.get_widget(widget_name)
		else:
			return None

class NodeDialog_Main(NodeDialog):
	"""
	The main 'Details' dialog which pops up on left-click
	"""
	def __init__(self,node,parent = None, tabs_visible = True):

		NodeDialog.__init__(self,node,parent)
		
		if not parent:
			self.set_title("Internode Usage")
		
		self.ui_file = os.path.join(os.path.dirname(os.path.dirname(__file__)),'internode-applet.glade')
		
		#get controls from glade & add them to the parent...
		glade = gtk.glade.XML(self.ui_file, "details_vbox")
		controls = glade.get_widget("details_vbox")
		
		notebook = glade.get_widget("notebook")
		notebook.set_show_tabs(tabs_visible)

		glade.get_widget("btnCopyIP").connect("clicked",self.on_copy_ip_click)
		glade.get_widget("lnkVersionCheck").set_uri('http://users.on.net/~antisol/nodeutil/version-check.php?v=%s' % VERSION)
				
		self.glade = glade
		self.controls = controls

		self.notebook = notebook
				
		self.parent.add(controls)

		#add a history window to the notebook...
		graph_window = HistoryWindow(self.nodeutil,
		os.path.join(os.path.dirname(os.path.dirname(__file__))),self.notebook)

		#request a graph taller than 2px...
		graph_window.graph.set_size_request(0,200)

		self.graph = graph_window
		self.graph_populated = False

		self.notebook.set_tab_label_text(self.graph.vbox, "Chart")

	def on_copy_ip_click(self,widget = None, data = None):
		#copy IP to clipboard...
		ip = self.get_widget("ip_addy").get_text()
		clipboard = gtk.clipboard_get()
		clipboard.set_text(ip)
		# make our data available to other applications
		clipboard.store()
			
	def refresh(self):
		if self.nodeutil.status == "OK":
			if self.graph_populated == False:
				#only do this once
				self.graph.fill_data()
				self.graph_populated = True

			self.get_widget("heading").set_markup(
				'<span size="12000">Internode Usage for: <b>%s</b></span>' % self.nodeutil.username)

			self.get_widget("usage_quota").set_markup(
				'<span size="16000"><b>%2.2f</b> MB / <b>%2d</b> MB</span> used.' %
				(self.nodeutil.used,self.nodeutil.quota))

			self.get_widget("progressbar").set_fraction(self.nodeutil.used / self.nodeutil.quota)

			self.get_widget("percentage").set_markup('<span size="16000"><i>%2.1f%%</i></span>' %
				((self.nodeutil.used / self.nodeutil.quota) * 100))

			self.get_widget("days_left").set_markup(
				'<span size="16000"><b>%2d</b></span> Days remaining' % self.nodeutil.daysleft)

			self.get_widget("mb_left").set_markup(
				'<span size="16000"><b>%2d</b> MB </span>remaining' % self.nodeutil.remaining)

			self.get_widget("rate_left").set_markup(
				'<span size="16000"><b>%2.2f</b> MB / Day</span> remaining' %
					(self.nodeutil.remaining / self.nodeutil.daysleft))

			rate = (self.nodeutil.remaining * 1024) / (self.nodeutil.daysleft * 24 * 60 * 60)

			self.get_widget("rate_suggest").set_markup(
				'Suggested download rate: <span size="12000"><b>%3.2f</b> KB/s</span>' % rate)

			secs = (time.time() - self.nodeutil.time)

			self.get_widget("last_updated").set_markup("Last updated: %s ago" % friendly_time(secs))

			self.get_widget("plan_name").set_markup("<b>%s</b>" % self.nodeutil.plan)
			self.get_widget("plan_type").set_markup("<b>%s</b>" % self.nodeutil.plan_interval)
			self.get_widget("plan_speed").set_markup("<b>%s</b>" % self.nodeutil.speed)
			self.get_widget("carrier").set_markup("<b>%s</b>" % self.nodeutil.carrier)
			if self.nodeutil.uploads_charged:
				txt = "Yes"
			else:
				txt = "No"

			self.get_widget("uploads_metered").set_markup("<b>%s</b>" % txt)
			self.get_widget("rollover_date").set_markup("<b>%s</b>" % self.nodeutil.rollover)
			self.get_widget("ip_addy").set_markup("<b>%s</b>" % self.nodeutil.ip)

		elif self.nodeutil.status == "Updating":
			self.get_widget("last_updated").set_markup("Last updated: <b><i>Updating Now!</i></b>")

		elif self.nodeutil.status == "Error":
			self.graph_populated = False

	def on_refresh_click(self,callback):
		self.get_widget("btnRefresh").connect("clicked",callback)

class NodeDialog_UsageAlert(NodeDialog):
	"""
	The Internode Alert Dialog - custom text, usage levels, with 'buy data' and 'ok' buttons
	"""
	def __init__(self,node,parent = None, title = "Internode Usage Alert", text = None, hidden = False):
		NodeDialog.__init__(self,node,parent)
		
		if not parent:
			self.set_title(title)
			self.parent.set_position(gtk.WIN_POS_CENTER)
			
		self.ui_file = os.path.join(os.path.dirname(os.path.dirname(__file__)),'internode-applet.glade')
		
		glade = gtk.glade.XML(self.ui_file, "alert_vbox")
		controls = glade.get_widget("alert_vbox")
		self.label = glade.get_widget("message")
		btnOK = glade.get_widget("btnOK")
		btnOK.connect("clicked",self.close)
		btnBuy = glade.get_widget("btnBuyData")
		self.handler = btnBuy.connect("clicked",self.buy_data)
				
		self.glade = glade
		self.controls = controls
		self.show_usage_data = True

		if text:
			self.set_text(text)
		
		self.parent.add(controls)
		
		if not hidden:
			self.parent.show_all()
		
	def show(self, text = None, show_usage = None):
		"""
		Shows the dialog.
		@text - if specified, sets the alert text first
		"""
		if show_usage != None:
			self.show_usage_data = show_usage
			
		if text:
			self.set_text(text)
		NodeDialog.show(self)
		
	def set_text(self,text):
		"""
		Sets the alert text
		"""
		try:
			#self.nodeutil.update()
			if self.nodeutil.status == "OK":
				if self.show_usage_data:
					self.label.set_markup('<span size="14000">%s</span>\n\
						\nYour internode usage for this month has reached <b>%2d%%</b>!\n\
						\nYou have <b>%2d</b> MB remaining over %2d days, or <b>%2.2f</b> MB / day' %
						(text, self.nodeutil.percent_used, self.nodeutil.remaining, self.nodeutil.daysleft,
							(self.nodeutil.remaining / self.nodeutil.daysleft) )
				)
				else:
					self.label.set_markup('<span size="14000">%s</span>' % text)
			else:
				self.label.set_markup('<span size="14000">%s</span>\n\n%s' % (text, self.nodeutil.error))
		except UpdateError:
			self.label.set_markup('<span size="14000">%s</span>\n\n%s' % (text, self.nodeutil.error))

		
	def buy_data(self, widget = None, data = None):
		os.spawnlp(os.P_NOWAIT,"xdg-open","xdg-open",
			"https://secure.internode.on.net/myinternode/sys2/blockscwt/purchaseBlocks.action")
		self.close()

class NodeDialog_Alert(NodeDialog_UsageAlert):
	"""
	A More generalised Alert Message
	"""
	def __init__(self,node,parent = None, title = "Internode Usage Alert", markup = None, hidden = False):
		#we don't pass 'hidden' off to the parent's constructor, we'll implement that later - 
		#	(we might want to change things between creation and showing)
		NodeDialog_UsageAlert.__init__(self,node,parent, title, None, False)

		#NodeDialog.__init__(self,node,parent)
		if False:
			if not parent:
				self.set_title(title)
				self.parent.set_position(gtk.WIN_POS_CENTER)

			self.ui_file = os.path.join(os.path.dirname(os.path.dirname(__file__)),'internode-applet.glade')

			glade = gtk.glade.XML(self.ui_file, "alert_vbox")
			controls = glade.get_widget("alert_vbox")
			self.label = glade.get_widget("message")

		btnOK = self.get_widget("btnOK")
		btnOK.connect("clicked",self.close)
		btnOK.set_label("Meh")
		btnBuy = self.get_widget("btnBuyData")
		btnBuy.set_label("Download Now...")
		btnBuy.disconnect(self.handler)
		btnBuy.connect("clicked",self.download)
				
		#self.glade = glade
		#self.controls = controls
		#self.show_usage_data = True

		if markup:
			self.set_markup(markup)


		#self.parent.add(controls)

		if not hidden:
			self.show()

	def download(self,widget = None,data = None):
		os.spawnlp(os.P_NOWAIT,"xdg-open","xdg-open",
			"http://users.on.net/~antisol/nodeutil/")
		self.close()

	def set_text(self,text):
		self.label.set_markup('<span size="14000">%s</span>' % text)

	def set_markup(self,markup):
		self.label.set_markup(markup)

class NodeDialog_Config(NodeDialog):
	"""
	The configuration dialog
	"""
	
class NodeDialog_Chart(NodeDialog):
	"""
	The Chart Dialog. 
	usually seen in a tab in the Main Dialog
	"""
	
class NodeDialog_AlertEditor(NodeDialog):
	"""
	The Alert Editor.
	usually seen in a tab in the main (should it be config?) dialog
	Allows editing of alerts.
	Also encapsulates the 'Edit an Alert' Dialog
	"""
	
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


class NodeIcons:
	"""
	NodeIcons Class
	Auto-loads and holds the icons used by the Internode Meter
	"""
	def __init__(self, node):
		self.nodeutil = node
		#TODO: Load icons from pixmaps into an array of pixbufs
		
	def get_current_icon(self):
		"""
		Returns a pixbuf representing the Icon we should be using, according to 
			settings / the current status / usage level
		"""
		
	def get_icon(self,icon_id):
		"""
		returns the specified icon
		"""
		
