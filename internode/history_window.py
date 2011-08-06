#!/usr/bin/env python

import gtk
import gtk.glade

from graph import Graph
from datetime import date

class HistoryWindow:

	def __init__(self, util, ui_dir):
		self.nodeutil = util

		# Load and show the graph dialog box
		glade = gtk.glade.XML(ui_dir + "/internode-applet.glade", "graph")
		back_button = glade.get_widget("graph_back_button")
		forward_button = glade.get_widget("graph_forward_button")
		self.date_label = glade.get_widget("date_label")
		self.usage_label = glade.get_widget("usage_label")
		self.days_spinner = glade.get_widget("graph_days")
		align = glade.get_widget("alignment1")
		vbox = glade.get_widget("graph_vbox")
		window = glade.get_widget("graph")

		self.graph = Graph()
		align.add(self.graph)

		# Connect the signals
		self.graph.connect("motion-notify-event", self.select)
		self.graph.connect("leave-notify-event", self.clear_selection)
		back_button.connect("clicked", self.move_back)
		forward_button.connect("clicked", self.move_forward)
		self.days_spinner.connect("value_changed", self.change_days)

		window.show_all()

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
				usage_date = date(year, month, day)
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
		self.start = len(history)/self.days * self.days
		if self.start == len(history):
			self.start = len(history) - self.days
		end = self.start + self.days
		history = history[self.start:end]
		if len(history) < self.days:
			history = self._pad(history)
		self._set_data(history)
