#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++#
#																																							#
# nodeutil.py - Support file for the																					#
#								GNOME ADSL Internode Usage Meter Panel Applet									#
#																																							#
# Copyright (C) 2005	Sam Pohlenz <retrix@internode.on.net>										#
#																																							#
# This program is free software; you can redistribute it and/or								#
# modify it under the terms of the GNU General Public License									#
# as published by the Free Software Foundation; either version 2							#
# of the License, or (at your option) any later version.											#
#																																							#
# This program is distributed in the hope that it will be useful,							#
# but WITHOUT ANY WARRANTY; without even the implied warranty of							#
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	See the								#
# GNU General Public License for more details.																#
#																																							#
# You should have received a copy of the GNU General Public License						#
# along with this program; if not, write to the Free Software									#
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA	 02111-1307, USA. #
#																																							#
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++#

#
# If you wish to create your own usage meter interface, do not copy the
# interface from this program, please contact Internode via
# http://www.internode.on.net/contact/support/ for the API document
#

###########
# Imports #
###########

import time
import datetime
import urllib2
import base64
from xml.dom import minidom


#####################
# Class Definitions #
#####################

class NodeUtil:
	""" 
	Updates usage information, caching the data to avoid excessive requests
	to the Internode servers. New data will only be fetched once per hour.
	"""

	def __init__(self):
		"""
		Initalize the Internode utility class
		"""
		
		self.api_host = "https://customer-webtools-api.internode.on.net"

		self.username = ""
		self.password = ""
		self.show_used = False
		self.time = 0
		
		self.error = ""

		self.percent_used = 0
		self.percent_remaining = 0
		self.quota = 0
		self.used = 0
		self.remaining = 0

		self.daysleft = 0
		
		self.history = []


	def do_update(self):
		"""
		Updates data, regardless of currently held data
		"""
		
		# Just get data for first service
		service = self.get_services()[0]
		
		self.get_usage(service)
		self.get_history(service)

		# params_dic = {}
		# params_dic["username"] = self.username
		# params_dic["password"] = self.password
		# params = urllib.urlencode(params_dic)

		# try:
		# 	params_dic["history"] = 1
		# 	params = urllib.urlencode(params_dic)
		# 	f = urllib.urlopen("https://customer-webtools-api.internode.on.net/cgi-bin/padsl-usage", params)
		# 	history = f.read().split()
		# 	self.history = [(history[x],history[x+1]) for x in range(0,len(history),2)]
		# except IOError:
		# 	self.error = "Failed to fetch history data."
		# 	raise UpdateError

			
	def get_services(self):
		try:
			services = []
		
			dom = self.api_request("/api/v1.5/")
			for node in dom.getElementsByTagName('service'):
				services.append({
					'id':		self.get_text(node),
					'type': node.getAttribute('type'),
					'path': node.getAttribute('href')
				})
		
			return services
		
		except IOError:
			self.error = "Failed to fetch service data."
			raise UpdateError
		
	def get_usage(self, service):
		try:
			dom = self.api_request("%s/usage" % service['path'])
			traffic = dom.getElementsByTagName('traffic')[0]
			
			self.quota = float(traffic.getAttribute('quota')) / 1024 / 1024
			self.used = float(self.get_text(traffic)) / 1024 / 1024
			self.remaining = self.quota - self.used
			
			self.percent_remaining = int(round(self.remaining / self.quota * 100))
			self.percent_used = int(round(self.used / self.quota * 100))
			
			self.daysleft = get_date_difference(traffic.getAttribute('rollover'))
			
			self.time = time.time()
			print "Data updated for username %s." % self.username

			self.error = ""
		
		except IOError:
			self.error = "Failed to fetch usage data."
			raise UpdateError
	
	def get_history(self, service):
		try:
			dom = self.api_request("%s/history" % service['path'])
			usagelist = dom.getElementsByTagName('usage')
			
			self.history = []
			for node in usagelist:
				date = parse_date(node.getAttribute('day')).strftime('%y%m%d')
				mb = "%.6f" % (self.fetch_traffic_total(node) / 1024 / 1024)
				self.history.append((date, mb))
			
		except IOError:
			self.error = "Failed to fetch usage data."
			raise UpdateError
	
	def get_text(self, node):
		text = ""
		for node in node.childNodes:
			if node.nodeType == node.TEXT_NODE:
				text = text + node.data
		return text
		
	def fetch_traffic_total(self, node):
		traffic = node.getElementsByTagName('traffic')
		for t in traffic:
			if t.getAttribute('name') == 'total':
				return float(self.get_text(t))
			
		return 0

	def api_request(self, path):
		request = urllib2.Request("%s%s" % (self.api_host, path))
		request.add_header('User-Agent', 'UsageMeterForGNOME/1.7')
		request.add_header('Authorization', self.http_auth_string())
		result = urllib2.urlopen(request)
		return minidom.parse(result)
	
	def http_auth_string(self):
		base64string = base64.encodestring("%s:%s" % (self.username, self.password))[:-1]
		return "Basic %s" % base64string
		
	def update(self):
		"""
		Updates data, first checking that there is no recent data
		"""

		if time.time() - 3600 > self.time:
			self.do_update()


class UpdateError(Exception):
	"""
	Exception class to handle update errors
	"""
	
	pass


def parse_date(date):
	datetuple = time.strptime(date, '%Y-%m-%d')
	return datetime.date(datetuple[0], datetuple[1], datetuple[2])

def get_date_difference(rollover):
	diff = parse_date(rollover) - datetime.date.today()
	return diff.days
	