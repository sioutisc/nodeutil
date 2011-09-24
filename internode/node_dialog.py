import os.path
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
import datetime
import sys
import os

try:
	import gtk
	import gtk.glade
	import gtk.gdk as gdk
	import pango
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
from graph import Graph

log("---------------------------------------------------")
log('NodeDialog Init.')

#array of paths where internode applet should look for files (icons, glade, etc)
search_paths=[ os.path.join(os.path.dirname(os.path.dirname(__file__))),
	os.path.join(sys.prefix,'share','internode-applet'),
	os.path.join('usr','share','internode-applet'),
	os.path.join('usr','local','share','internode-applet') ]

for path in search_paths:
	log(" - Looking for nodeutil files in '%s'..." % path)
	if (os.path.exists(path)):
		gladefile=os.path.join(path,'internode-applet.glade')
		if (os.path.exists(gladefile)):
			log("Found '%s', setting UI_FILE..." % gladefile)
			UI_FILE=gladefile
			PIXMAP_PATH=os.path.join(path,'pixmaps')
			log("PIXMAP_PATH is '%s'" % PIXMAP_PATH)
			if not os.path.exists(PIXMAP_PATH):
				log("ERROR: PIXMAP_PATH ('%s') does not exist!" % PIXMAP_PATH)
				sys.exit(1)
			break

#path to the glade file:
#UI_FILE=os.path.join(os.path.dirname(os.path.dirname(__file__)),'internode-applet.glade')

if not UI_FILE:
	log("ERROR: Can't find internode-applet.glade! Make sure the applet is properly installed!")
	sys.exit(1)

def friendly_time(secs):
	"""
	turn a float/int number of seconds into a friendly looking string,
		like '2 seconds' or '18 minutes'
	"""
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
		
		#get controls from glade & add them to the parent...
		glade = gtk.glade.XML(UI_FILE, "details_vbox")
		controls = glade.get_widget("details_vbox")
		
		notebook = glade.get_widget("notebook")
		notebook.set_show_tabs(tabs_visible)

		glade.get_widget("btnCopyIP").connect("clicked",self.on_copy_ip_click)
		glade.get_widget("lnkVersionCheck").set_uri('http://users.on.net/~antisol/nodeutil/version-check.php?v=%s' % VERSION)
				
		self.glade = glade
		self.controls = controls

		self.notebook = notebook
				
		self.parent.add(controls)

		#add a chart to the notebook...
		graph_window = NodeDialog_Chart(self.nodeutil,self.notebook)
		self.graph = graph_window
		self.graph_populated = False

		#setup the alert editor...
		#NOTE: likely not available in the initial release, alerts got
		#	complicated fast.
		#alert_editor = NodeDialog_AlertEditor(self.notebook)

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
	The Internode Usage Alert Dialog - custom text, usage levels, with 'buy data' and 'ok' buttons
	"""
	def __init__(self,node,parent = None, title = "Internode Usage Alert", text = None, hidden = False):
		NodeDialog.__init__(self,node,parent)
		
		if not parent:
			self.set_title(title)
			self.parent.set_position(gtk.WIN_POS_CENTER)
		
		glade = gtk.glade.XML(UI_FILE, "alert_vbox")
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
	A More generalised Alert Message, doesn't show usage data
	"""
	def __init__(self,node,parent = None, title = "Internode Usage Alert", markup = None, hidden = False):
		#we don't pass 'hidden' off to the parent's constructor, we'll do that later -
		#	(we might want to change things between creation and showing)
		NodeDialog_UsageAlert.__init__(self,node,parent, title, None, False)

		#NodeDialog.__init__(self,node,parent)
		if False:
			if not parent:
				self.set_title(title)
				self.parent.set_position(gtk.WIN_POS_CENTER)

			glade = gtk.glade.XML(UI_FILE, "alert_vbox")
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
	def __init__(self,node):
		log("Showing Preferences Dialog")

		#The prefs dialog never has a parent
		NodeDialog.__init__(self,node,None)

		self.gconf_client = gconf.client_get_default()
		
		# Load and show the preferences dialog box
		glade = gtk.glade.XML(UI_FILE, "preferences")
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

	def write_prefs(self):
		log("Saving Preferences")
		self.gconf_client.set_string("/apps/internode-applet/username", self.nodeutil.username)
		self.gconf_client.set_string("/apps/internode-applet/password", self.nodeutil.password)
		self.gconf_client.set_bool("/apps/internode-applet/show_used", self.nodeutil.show_used)

class NodeDialog_Chart(NodeDialog):
	"""
	The Chart Dialog. 
	usually seen in a tab in the Main Dialog
	"""
	def __init__(self, node, parent = None):

		NodeDialog.__init__(self,node,parent)
		#self.nodeutil = node

		# Load and show the graph dialog box
		#if parent:
		glade = glade = gtk.glade.XML(UI_FILE, "graph_vbox")
		#controls = glade.get_widget("details_vbox")
		#	parent.add(glade.get_widget("graph_vbox"))
		#else:
		#	glade = gtk.glade.XML(UI_FILE, "graph")

		self.glade = glade
		back_button = glade.get_widget("graph_back_button")
		forward_button = glade.get_widget("graph_forward_button")
		self.date_label = glade.get_widget("date_label")
		self.usage_label = glade.get_widget("usage_label")
		self.days_spinner = glade.get_widget("graph_days")
		self.btnShowAll = glade.get_widget("btnShowAll")
		self.btnThisMonth = glade.get_widget("btnThisMonth")
		self.btn30d = glade.get_widget("btn30d")
		align = glade.get_widget("alignment1")
		vbox = glade.get_widget("graph_vbox")
		self.vbox = vbox
		self.controls = vbox
		self.graph = Graph()
		align.add(self.graph)
		#request more than 2px height for the chart area:
		self.graph.set_size_request(0,200)

		# Connect the signals
		self.graph.connect("motion-notify-event", self.select)
		self.graph.connect("leave-notify-event", self.clear_selection)
		back_button.connect("clicked", self.move_back)
		forward_button.connect("clicked", self.move_forward)
		self.days_spinner.connect("value_changed", self.change_days)
		self.btnShowAll.connect("clicked",self.show_all_data)
		self.btnThisMonth.connect("clicked",self.show_this_month)
		self.btn30d.connect("clicked",self.show_30_days)

		#self.graph.show_all()
		self.parent.add(vbox)
		self.set_title('Chart')
		self.parent.show_all()

		# The number of days to display
		self.days = 30
		# Where to start in the usage data
		self.start = 0

		self.days_spinner.set_value(self.days)
		self.fill_data()


	def select(self, widget, event):
		colour = (0.7,0.7,1)
		colval = self.graph.highlight_col(event, colour)
		
		if colval != None:
			try:
				day = int(colval[0][4:])
				month = int(colval[0][2:4])
				year = int(colval[0][:2]) + 2000
				usage_date = datetime.date(year, month, day)
				date_label = usage_date.strftime("%a %b %d %Y")
				usage_label = str(int(round(colval[1]))) + " MB"
			except TypeError:
				date_label = ""
				usage_label = ""

			self.usage_label.set_text(usage_label)
			self.date_label.set_text(date_label)


	def clear_selection(self, widget, event):
		self.graph.clear_selection()

	def change_days(self, event):
		self.days = int(self.days_spinner.get_value())

		if self.days > len(self.nodeutil.history):
			self.days = len(self.nodeutil.history)
			self.days_spinner.set_value(self.days)

		self.fill_data()
		self.graph.refresh()

	def move_forward(self, event):
		self.start = self.start + self.days
		if self.start >= len(self.nodeutil.history):
			self.start = len(self.nodeutil.history)/self.days * self.days

		end = self.start + self.days
		if end > len(self.nodeutil.history):
			end = len(self.nodeutil.history)
		if self.start == len(self.nodeutil.history):
			self.start = len(self.nodeutil.history) - self.days

		history = self.nodeutil.history[self.start:end]

		if len(history) < self.days:
			history = self._pad(history)

		self._set_data(history)
		self.graph.refresh()

	def move_back(self, event):
		self.start = self.start - self.days
		if self.start < 0: self.start = 0
		end = self.start + self.days
		if end == 0: return

		history = self.nodeutil.history[self.start:end]

		if len(history) < self.days:
			history = self._pad(history)

		self._set_data(history)
		self.graph.refresh()

        def _pad(self, data):
                for x in range(self.days-len(data)):
                        data.append((0,0))
                return data

	def _set_data(self, data):
		self.graph.data = [(x[0], float(x[1])) for x in data]

	def fill_data(self):
		history = self.nodeutil.history
		self.start = len(history) - self.days
		if self.start == len(history):
			self.start = len(history) - self.days
		end = self.start + self.days
		history = history[self.start:end]
		if len(history) < self.days:
			history = self._pad(history)
		self._set_data(history)

	def show_all_data(self, event):
		self.days = len(self.nodeutil.history)
		self.days_spinner.set_value(self.days)
		self.change_days(event)

	def show_this_month(self, event):
		self.days = 31
		self.days_spinner.set_value(self.days)
		self.start = len(self.nodeutil.history) - (self.days - self.nodeutil.daysleft)

		end = self.start + self.days
		history = self.nodeutil.history[self.start:end]
		if len(history) < self.days:
			history = self._pad(history)
		self._set_data(history)

		self.graph.refresh()

	def show_30_days(self, event):
		self.days = 30
		self.start = len(self.nodeutil.history) - 30
		self.days_spinner.set_value(self.days)
		self.change_days(event)


class AlertSettings:
	"""
	A simple enum for alert settings
	"""
	Percent, Mb, Days, Used, Remaining, RemainingPerDay = range(6)

	def from_int(self,value):
		"""
		convert from an int to a pretty text
		"""
		value = int(value)
		if (value == AlertSettings.Percent):
			return "%"
		elif (value == AlertSettings.Mb):
			return "MB"
		elif (value == AlertSettings.Days):
			return "Days"
		elif (value == AlertSettings.Used):
			return "Used"
		elif (value == AlertSettings.Remaining):
			return "Remaining"
		elif (value == AlertSettings.RemainingPerDay):
			return "Remaining/day"
		else:
			return ""

	def from_str(self,value):
		if (value == "Percent") or (value == "%"):
			return AlertSettings.Percent
		elif (value == "Mb") or (value == "Mb"):
			return AlertSettings.Mb
		elif (value == "Days"):
			return AlertSettings.Days
		elif (value == "Used"):
			return AlertSettings.Used
		elif (value == "Remaining"):
			return AlertSettings.Remaining
		elif (value == "RemainingPerDay") or (value == "Remaining/day"):
			return AlertSettings.RemainingPerDay
		else:
			return -1

class NodeDialog_AlertEditor(NodeDialog):
	"""
	The Alert Editor.
	usually seen in a tab in the main (should it be config?) dialog
	Allows editing of alerts.
	Also encapsulates the 'Edit an Alert' Dialog
	"""

	def __init__(self,parent = None):
		NodeDialog.__init__(self,None,parent)

		#code for the alert editor:

		list = gtk.ListStore(int,str,str,str)
		list.append([100, "%", "Used", "You be capped!"])
		list.append([90, "%", "Used", "Internode usage is critically high!"])
		list.append([75, "%", "Used", "Three Quarters of your Internode data has been used!"])
		list.append([50, "%", "Used", "You've used half your Internode data!"])
		list.append([0, "%", "Used", "A New Month!"])

		##alertlist = stats.get_widget("alertlist")
		#alertlist = gtk.TreeView(list)

		alerts = gtk.glade.XML(UI_FILE, "alerts_vbox")
		alerts_box = alerts.get_widget("alerts_vbox")
		self.vbox = alerts_box
		self.controls = alerts_box
		alertlist = alerts.get_widget("alert_list")
		alertlist.set_model(list)
		alertlist.set_rules_hint(True)

		rendererText = gtk.CellRendererText()
		rendererText.alignment = pango.ALIGN_RIGHT
		column = gtk.TreeViewColumn("At", rendererText, text=0)
		column.set_sort_column_id(0)
		alertlist.append_column(column)

		rendererText2 = gtk.CellRendererText()
		column2 = gtk.TreeViewColumn("", rendererText2, text=1)
		column2.set_sort_column_id(1)
		alertlist.append_column(column2)

		rendererText3 = gtk.CellRendererText()
		column3 = gtk.TreeViewColumn("", rendererText3, text=2)
		column3.set_sort_column_id(2)
		alertlist.append_column(column3)

		rendererText4 = gtk.CellRendererText()
		column4 = gtk.TreeViewColumn("Message", rendererText4, text=3)
		column4.set_sort_column_id(3)
		alertlist.append_column(column4)

		self.parent.add(alerts_box)

		#notebook.append_page(alerts_box)
		#notebook.set_tab_label_text(alerts_box, "Alerts")
		##alertlist.realize()

		#dialog.add(details)
		self.set_title("Alerts")
		self.parent.show_all()

class NodeIcons:
	"""
	NodeIcons Class
	Auto-loads and holds the icons used by the Internode Meter
	Note that this is a singleton - it loads icons once on init;
		just use e.g: NodeIcons.icons["x"]
	"""
	
	log("NodeIcons Init")
	icons = {}

	#Percentage Remaining icons
	icons["0"] = gtk.gdk.pixbuf_new_from_file(os.path.join(PIXMAP_PATH, "internode-0.png"))
	icons["25"] = gtk.gdk.pixbuf_new_from_file(os.path.join(PIXMAP_PATH, "internode-25.png"))
	icons["50"] = gtk.gdk.pixbuf_new_from_file(os.path.join(PIXMAP_PATH, "internode-50.png"))
	icons["75"] = gtk.gdk.pixbuf_new_from_file(os.path.join(PIXMAP_PATH, "internode-75.png"))
	icons["100"] = gtk.gdk.pixbuf_new_from_file(os.path.join(PIXMAP_PATH, "internode-100.png"))
	icons["x"] = gtk.gdk.pixbuf_new_from_file(os.path.join(PIXMAP_PATH, "internode-x.png"))

	#Percentage Used icons
	icons["u0"] = gtk.gdk.pixbuf_new_from_file(os.path.join(PIXMAP_PATH, "internode-u0.png"))
	icons["u25"] = gtk.gdk.pixbuf_new_from_file(os.path.join(PIXMAP_PATH, "internode-u25.png"))
	icons["u50"] = icons["50"]
	icons["u75"] = gtk.gdk.pixbuf_new_from_file(os.path.join(PIXMAP_PATH, "internode-u75.png"))
	icons["u100"] = gtk.gdk.pixbuf_new_from_file(os.path.join(PIXMAP_PATH, "internode-u100.png"))

	logo_path = os.path.join(PIXMAP_PATH, "internode.svg")
	# About logo
	logo_large = gtk.gdk.pixbuf_new_from_file(logo_path)
	#smaller logo
	logo = gtk.gdk.pixbuf_new_from_file_at_size(logo_path, 44, 48)

	log("%2d Icons Loaded." % (len(icons) + 2))