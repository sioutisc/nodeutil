#!/usr/bin/env python

import gobject
import pango
import gtk
from gtk import gdk
try:
    import cairo
except ImportError:
    pass

class Graph(gtk.Widget):
	__gsignals__ = {'realize': 'override',
			'expose-event' : 'override',
			'size-allocate': 'override',
		     }
	def __init__(self):
		gtk.Widget.__init__(self)
		self.draw_gc = None
		self.border =  0.02	# Percentage Width of the border
		self.selected = -1	# Currently selected column
		self.data = []		# The data the graph shows
                                         
	def do_realize(self):
		self.set_flags(self.flags() | gtk.REALIZED)
		self.window = gdk.Window(self.get_parent_window(),
				width = self.allocation.width,
				height = self.allocation.height,
				window_type = gdk.WINDOW_CHILD,
				wclass = gdk.INPUT_OUTPUT,
				event_mask =
					self.get_events() 
					| gdk.EXPOSURE_MASK
					| gdk.POINTER_MOTION_MASK
					| gdk.BUTTON_PRESS_MASK
					| gdk.BUTTON_RELEASE_MASK
					| gdk.LEAVE_NOTIFY_MASK
				)

		if not hasattr(self.window, "cairo_create"):
			print "No cairo"
		self.window.set_user_data(self)
		self.style.attach(self.window)
		self.style.set_background(self.window, gtk.STATE_NORMAL)
		self.window.move_resize(*self.allocation)

	def do_size_allocate(self, allocation):
		self.allocation = allocation
		if self.flags() & gtk.REALIZED:
			self.window.move_resize(*allocation)

	def _expose_cairo(self, event, cr):
		x, y, w, h = self.allocation

		self._draw_graph(cr, x, y, w, h)

	def do_expose_event(self, event):
		self.chain(event)
		try:
			cr = self.window.cairo_create()
		except AttributeError:
			print "Could not create cairo canvas"
		return self._expose_cairo(event, cr)
        
	def refresh(self):
		"""
		Redraw the graph
		"""
		try:
			cr = self.window.cairo_create()
		except AttributeError:
			return

		x, y, w, h = self.allocation        
		self.window.invalidate_rect((0,0,w,h),False)        
		self._draw_graph(cr, x, y, w, h)

	def _draw_graph(self, cr, x, y, w, h):
		"""
		The cairo method to draw the graph
		"""

		if len(self.data) == 0: return

		bw = w * self.border		# border width
		colw = self._colwidth(w)	# column width
		colx = x+2*bw
		lw = colw/9			# line width
		fill_color = (0.5,0.5,1)
		maxno = self._max_no()

		# Paint the background
		self._draw_background(cr, bw, w, h)

		# Draw the mean line
		self._draw_average(cr, maxno, w, h, bw, lw)
		
		# Draw all the columns   
		for i in range(len(self.data)):
			self._draw_col(i+1, cr, colw, lw, fill_color, x, h, maxno, bw)
        
		# Draw a border around the graph
		self._draw_border(cr, bw, w, h)
        
	def _draw_col(self, colno, cr, colw, lw, colour, x, h, maxno, bw):
		"""
		The cairo method to draw a column of the graph
		"""

		# make sure the requested column exists
		if colno > len(self.data) or colno <= 0: return

		# don't draw a negative column
		if self.data[colno-1][1] < 0: return

		# don't draw columns outside the range
		if colno > len(self.data): return
		        
		colx = bw + (colno-1) * colw	# column top left corner
		# relative height of the column
		try: rh = self.data[colno-1][1] / float(maxno)  
		except ZeroDivisionError: rh = 0

		ch = (h - 2*bw) * rh		# actual height of the column
		coly = h - ch - bw        

		cr.rectangle(colx, coly, colw, ch-lw)

		cr.set_line_width(lw)
		cr.set_line_join(cairo.LINE_JOIN_ROUND)

		# Set the colour and fill
		r,g,b = colour
		cr.set_source_rgb (r,g,b)
		cr.fill_preserve()

		# Set the colour darker and stoke
		cr.set_source_rgb(r*0.7, g*0.7, b*0.7)
		cr.stroke()
        
	def _draw_border(self, cr, bw, w, h):
		"""
		The cairo method to draw a border around the graph
		"""

		r,g,b = (0.5,0.5,1)
		cr.set_source_rgb(r*0.7, g*0.7, b*0.7)
		cr.rectangle(bw/2, bw/2, w - bw, h - 1.5*bw)
		cr.set_line_width(self.border * w/5)
		cr.stroke()
	
	def _draw_background(self, cr, bw, w, h):
		"""
		The cairo method to draw the background
		"""

		pat = cairo.LinearGradient (0.0, 0.0, 0.0, h)
		pat.add_color_stop_rgba (h, 0.5, 0.5, 1, 1)
		pat.add_color_stop_rgba (0, 1, 1, 1, 0)

		cr.rectangle(bw/2, bw/2, w - bw, h - 1.5*bw)
		cr.set_source (pat)
		cr.fill ()

	def _draw_average(self, cr, maxno, w, h, bw, lw):
		"""
		Draw a line representing the mean usage
		"""

		# relative height of the column
		try: rh = self._average() / float(maxno)    
		except ZeroDivisionError: rh = 0

		# actual height of the column
		ch = (h - 2*bw) * rh
		coly = h - ch - bw

		cr.move_to (bw/2, coly)
		cr.rel_line_to (w-bw, 0)

		cr.set_line_width(lw*2)
		cr.set_line_join(cairo.LINE_JOIN_ROUND)
		cr.set_source_rgb (1,0,0)
		cr.stroke()	
                
	def _colwidth(self, width):
		"""
		Calculate the width that each column should be
		"""

		return (width - 2 * self.border * width) / len(self.data)
        
	def highlight_col(self, event, colour):
		"""
		Highlight the column at an event location
		"""

		if len(self.data) == 0: return
					
		colno = self.selected_col(event.x)        
		if colno > len(self.data) or colno <= 0: return       
		if colno == self.selected: return

		x, y, w, h = self.allocation

		try:
			cr = self.window.cairo_create()
		except AttributeError:
			return self._expose_gdk(event)

		bw = self.border * w            #border width
		colw = self._colwidth(w)        #column width
		lw = colw/9                     #line width
		maxno = self._max_no()

		# Deselect the previous column
		self._draw_col(self.selected, cr, colw, lw, (0.5,0.5,1), x, h, maxno, bw)

		# Highlight the new one
		self._draw_col(colno, cr, colw, lw, colour, x, h, maxno, bw)
		self._draw_border(cr, bw, w, h)
		self.selected = colno

		return self.data[colno-1]

	def clear_selection(self):
		"""
		Un highlight the selected column
		"""

		if len(self.data) == 0:
			return
		        
		try:
			cr = self.window.cairo_create()
		except AttributeError:
			print "No Cairo"

		x, y, w, h = self.allocation        

		bw = self.border * w		#border width
		colw = self._colwidth(w)	#column width
		lw = colw/9			#line width
		maxno = self._max_no()

		# Deselect the previous column
		self._draw_col(self.selected, cr, colw, lw, (0.5,0.5,1), x, h, maxno, bw)
		self.selected = -1
        
	def selected_col(self, x):
		"""
		Calculate the coulumn corresponding to the given x value
		"""

		w = self.allocation[2]
		bw = self.border * w
		colw = self._colwidth(w)	#column width
		x = x - bw

		return int(x/colw) + 1

	def _average(self):
		"""
		Calculate the mean value of the data
		"""

		total = 0
		for x, y in self.data:
			total = total + y
		return float(total) / len(self.data)
	
	def _max_no(self):
		"""
		Calculate the maximum value in the data set
		"""
		return max([x[1] for x in self.data])

	def to_png(self, width, height):
		"""
		Write the graph out to a png file    
		"""

		surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
		cr = cairo.Context(surface)

		self._draw_graph(cr, 0, 0, width, height)

		surface.write_to_png('graph.png')
