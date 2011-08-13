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

from nodeutil import NodeUtil, UpdateError

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

		#If no parent is provided, the dialog goes into a new GTK Window.
		# If you do this, you'll want to call set_title()
		if parent:
			self.parent = parent
		else:
			self.parent = gtk.Window()
		
	def show(self):
		"""
		Shows the dialog
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
		sets the title of the Dialog
			Handles different types of containers:
			 - sets the title if parent is a gtk.Window
			 - will one day set tab title if parent is a gtk.Notebook
		"""
		if type(self.parent) == gtk.Window:
			self.parent.set_title(text)
		elif type(self.parent) == gtk.Notebook:
			print "TODO: set notebook tab title"

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
		
		self.parent.add(controls)
			
	def refresh(self):
		print "refresh!"

class NodeDialog_Alert(NodeDialog):
	"""
	The Internode Alert Dialog - custom text, usage levels, with 'buy data' and 'ok' buttons
	"""
	def __init__(self,node,text,parent = None, title = "Internode Usage Alert", hidden = False):
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
		btnBuy.connect("clicked",self.buy_data)
		
		self.set_text(text)
		
		self.parent.add(controls)
		
		if not hidden:
			self.parent.show_all()
		
	def show(self, text = None):
		"""
		Shows the dialog.
		@text - if specified, sets the alert text first
		"""
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
				self.label.set_markup('<span size="14000">%s</span>\n\
					\nYour internode usage for this month has reached <b>%2d%%</b>!\n\
					\nYou have <b>%2d</b> MB remaining over %2d days, or <b>%2.2f</b> MB / day' % 
					(text, self.nodeutil.percent_used, self.nodeutil.remaining, self.nodeutil.daysleft, 
						(self.nodeutil.remaining / self.nodeutil.daysleft) )
				)
			else:
				self.label.set_markup('<span size="14000">%s</span>\n\n%s' % (text, self.nodeutil.error))
		except UpdateError:
			self.label.set_markup('<span size="14000">%s</span>\n\n%s' % (text, self.nodeutil.error))

		
	def buy_data(self, widget = None, data = None):
		os.spawnlp(os.P_NOWAIT,"gnome-www-browser","gnome-www-browser",
			"https://secure.internode.on.net/myinternode")
		self.close()
		
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
		
