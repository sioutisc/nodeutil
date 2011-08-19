####################################################
# nodeutil2 - threaded reimplementation of nodeutil
# Copyright (C) Dale Maggee
# GNU GPL Licensed
####################################################

import sys
import time
import datetime
import urllib2
import base64
from xml.dom import minidom
import thread
import threading

VERSION=0.2
LOGFILE=None
"""
If set, log() will output to a logfile (not implemented)
"""

DEBUG=True
"""
Sets Debugging Mode.
In debug mode, several things happen:
	- Calls to log() produce output
	- Time intervals are shortened dramatically 
		(i.e: refresh once per minute, rather than once per hour)
"""

INSANE_DEBUG = False

SIMULATE_NETERROR=False
"""
If True, NodeUtil will pretend like somebody just accidendally teh whole Intarwebs
"""

ONE_KB = 1000
"""
How many bytes per KB?
"""

def log(text):
	"""
	Log a message with a timestamp
		does nothing in debug mode
	"""
	if DEBUG:
		print time.strftime("%Y-%m-%d %H:%M:%S") + ": " + text	

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

class NodeUtil(object):
	"""
	Threaded version of nodeutil:
		- calls to things like update() will always return immediately.
		- we don't raise errors anymore - status simply becomes "Error"
		- there is a new 'status' attribute, which should be read before looking
			at anything else
		- properties use thread locks to ensure safe reading/updating
	"""
	def __init__(self):
		log("NodeUtil v%0.1f - Init" % VERSION)
		self._status = "Initialising"
		self.user_agent_text = ""
		self.error = ""
		self.api_host = "https://customer-webtools-api.internode.on.net"

		self.username = ""
		self.password = ""

		self.show_used = False

		self._time = 0
		self._percent_used = 0
		self._percent_remaining = 0
		self._quota = 0
		self._used = 0
		self._remaining = 0
		self._daysleft = 0
		self._history = []
		self._speed = "Unknown"
		self._carrier = "Unknown"
		self._plan = "Unknown"
		self._uploads_charged = False
		self._plan_interval = "Unknown"
		self._rollover = "Unknown"
		self._ip = "0.0.0.0"

		self.can_has_callback = False
		self._callback = None

		self.update_interval = 30 * 60 #half an hour

		self.lock = threading.RLock()

		self.status = "Ready"

	"""
	getter / setter for status property
	"""
	def get_status(self):
		with self.lock:
			return self._status

	def set_status(self,value):
		with self.lock:
			self._status = value
		log("NodeUtil.status = '%s' (thread: %s)" % (value,thread.get_ident()))
		#self.send_signal()

	status = property(get_status,set_status)

	#def on_status_change(self,callback):
	#	 """
	#	 sets the callback which is called when status changes
	#	 """
	#	 self.can_has_callback = True
	#	 self._callback = callback

	#def send_signal(self):
	#	 log("signal fire: %s" % self.can_has_callback)
	#	 if self.can_has_callback:
	#		 log("Firing StatusChange Callback (thread: %s)" % (thread.get_ident()))
	#		 self._callback()

	"""
	property getters and setters.
		Note that they all use a reentrant lock to be threadsafe.
	"""
	def get_time(self):
		with self.lock:
			return self._time
	def set_time(self,value):
		with self.lock:
			self._time = value
	time = property(get_time,set_time)

	def get_percent_used(self):
		with self.lock:
			return self._percent_used
	def set_percent_used(self,value):
		with self.lock:
			self._percent_used = value
	percent_used = property(get_percent_used,set_percent_used)

	def get_percent_remaining(self):
		with self.lock:
			return self._percent_remaining
	def set_percent_remaining(self,value):
		with self.lock:
			self._percent_remaining = value
	percent_remaining = property(get_percent_remaining,set_percent_remaining)

	def get_quota(self):
		with self.lock:
			return self._quota
	def set_quota(self,value):
		with self.lock:
			self._quota = value
	quota = property(get_quota,set_quota)

	def get_used(self):
		with self.lock:
			return self._used
	def set_used(self,value):
		with self.lock:
			self._used = value
	used = property(get_used,set_used)

	def get_remaining(self):
		with self.lock:
			return self._remaining
	def set_remaining(self,value):
		with self.lock:
			self._remaining = value
	remaining = property(get_remaining,set_remaining)

	def get_daysleft(self):
		with self.lock:
			return self._daysleft
	def set_daysleft(self,value):
		with self.lock:
			self._daysleft = value
	daysleft = property(get_daysleft,set_daysleft)

	def get_history(self):
		with self.lock:
			return self._history
	def set_history(self,value):
		with self.lock:
			self._history = value
	history = property(get_history,set_history)

	def get_speed(self):
		with self.lock:
			return self._speed
	def set_speed(self,value):
		with self.lock:
			self._speed = value
	speed = property(get_speed,set_speed)

	def get_carrier(self):
		with self.lock:
			return self._carrier
	def set_carrier(self,value):
		with self.lock:
			self._carrier = value
	carrier = property(get_carrier,set_carrier)

	def get_plan(self):
		with self.lock:
			return self._plan
	def set_plan(self,value):
		with self.lock:
			self._plan = value
	plan = property(get_plan,set_plan)

	def get_uploads_charged(self):
		with self.lock:
			return self._uploads_charged
	def set_uploads_charged(self,value):
		with self.lock:
			self._uploads_charged = value
	uploads_charged = property(get_uploads_charged,set_uploads_charged)

	def get_plan_interval(self):
		with self.lock:
			return self._plan_interval
	def set_plan_interval(self,value):
		with self.lock:
			self._plan_interval = value
	plan_interval = property(get_plan_interval,set_plan_interval)

	def get_rollover(self):
		with self.lock:
			return self._rollover
	def set_rollover(self,value):
		with self.lock:
			self._rollover = value
	rollover = property(get_rollover,set_rollover)

	def get_ip(self):
		with self.lock:
			return self._ip
	def set_ip(self,value):
		with self.lock:
			self._ip = value
	ip = property(get_ip,set_ip)

	"""
	Internode API functions.
		These are called from within the update thread
	"""
	def get_services(self):
		if INSANE_DEBUG:
			log("Retrieving services...")
		try:
			services = []

			dom = self.api_request("/api/v1.5/")
			for node in dom.getElementsByTagName('service'):
				services.append({
					'id':		self.get_text(node),
					'type': node.getAttribute('type'),
					'path': node.getAttribute('href')
				})

			if INSANE_DEBUG:log("Services retrieved.")

			return services

		except:
			self.error = "Failed to fetch service data."
			self.status = "Error"

	def get_usage(self, service):
		if INSANE_DEBUG:log("Retrieving usage...")
		try:
			dom = self.api_request("%s/usage" % service['path'])

			traffic = dom.getElementsByTagName('traffic')[0]

			self.quota = float(traffic.getAttribute('quota')) / ONE_KB / ONE_KB
			self.used = float(self.get_text(traffic)) / ONE_KB / ONE_KB
			self.remaining = self.quota - self.used

			self.percent_remaining = int(round(self.remaining / self.quota * 100))
			self.percent_used = int(round(self.used / self.quota * 100))

			self.daysleft = get_date_difference(traffic.getAttribute('rollover'))

			self.time = time.time()
			if INSANE_DEBUG:log( "Data updated for username %s." % self.username)

			self.error = ""

		except:
			self.error = "Failed to fetch usage data."
			self.status = "Error"

	def get_history(self, service):
		if INSANE_DEBUG:log("Retrieving history...")
		try:
			dom = self.api_request("%s/history" % service['path'])

			usagelist = dom.getElementsByTagName('usage')

			self.history = []
			for node in usagelist:
				date = parse_date(node.getAttribute('day')).strftime('%y%m%d')
				mb = "%.6f" % (self.fetch_traffic_total(node) / ONE_KB / ONE_KB)
				self.history.append((date, mb))

		except:
			self.error = "Failed to fetch usage data."
			self.status = "Error"

	def get_service_info(self,service):
		if INSANE_DEBUG: 
			log("retrieving service info...")

		try:
			dom = self.api_request("%s/service" % service['path'])

			self.speed = self.get_text(dom.getElementsByTagName('speed')[0])
			self.carrier = self.get_text(dom.getElementsByTagName('carrier')[0])
			self.plan = self.get_text(dom.getElementsByTagName('plan')[0])

			tmp = self.get_text(dom.getElementsByTagName('usage-rating')[0])
			if tmp != "down":
				self.uploads_charged = True
			else:
				self.uploads_charged = False

			self.plan_interval = self.get_text(dom.getElementsByTagName('plan-interval')[0])
			self.rollover = self.get_text(dom.getElementsByTagName('rollover')[0])
		except:
			#this is non-critical info, so we won't set an error state.
			pass


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

	def fetch_ip_address(self):
		
		log("NodeUtil.fetch_ip_address()")
		try:
			if SIMULATE_NETERROR:
				#fake an error
				log("Simulating a network error")
				raise IOError

			request = urllib2.Request("https://customer-webtools-api.internode.on.net/cgi-bin/showmyip")
			user_agent = ('NodeUtil/%02.1f (%s)' % (VERSION,self.user_agent_text))
			#log("User Agent: '%s'" % user_agent)
			request.add_header('User-Agent', user_agent)
			request.add_header('Authorization', self.http_auth_string())
			result = urllib2.urlopen(request)
			ip = result.read().rstrip()
			result.close()

			if INSANE_DEBUG:
				log("Your IP Address is: %s" % ip)

			return ip
		except:
			log("Error retrieving IP!")
			return ""

	def check_version(self):
		#returns a float containing the current version of NodeUtil,
		#	for comparing with VERSION
		try:
			log("NodeUtil.check_version()")

			if SIMULATE_NETERROR:
				#fake an error
				log("Simulating a network error")
				raise IOError

			request = urllib2.Request("http://users.on.net/~antisol/nodeutil/version-check.php?t=1")
			user_agent = ('NodeUtil/%02.1f (%s)' % (VERSION,self.user_agent_text))
			#log("User Agent: '%s'" % user_agent)
			request.add_header('User-Agent', user_agent)
			request.add_header('Authorization', self.http_auth_string())
			result = urllib2.urlopen(request)
			version = result.read().rstrip()
			result.close()

			if INSANE_DEBUG:
				log("The Latest version of NodeUtil is: %s" % version)

			return float(version)
		
		except:
			#this is non-fatal, just return our version if it dies
			log("Version Check failed!")
			return float(VERSION)

	def api_request(self, path):
		log("NodeUtil.api_request('%s')" % path)
		if SIMULATE_NETERROR:
			#fake an error
			log("Simulating a network error")
			raise IOError
		request = urllib2.Request("%s%s" % (self.api_host, path))
		user_agent = ('NodeUtil/%02.1f (%s)' % (VERSION,self.user_agent_text))
		#log("User Agent: '%s'" % user_agent)
		request.add_header('User-Agent', user_agent)
		request.add_header('Authorization', self.http_auth_string())
		result = urllib2.urlopen(request)
		return minidom.parse(result)

	def http_auth_string(self):
		base64string = base64.encodestring("%s:%s" % (self.username, self.password))[:-1]
		return "Basic %s" % base64string

	"""
	Update functions
	"""
	def update(self,force = False):
		"""
		do a fetch if the data is old enough, or if force is True

		fetch is done by spawning a new thread.

		"""

		if self.status != "Updating" and (
			(time.time() - self.update_interval > self.time) or force):
				log("NodeUtil.update(%s)" % force)
				if INSANE_DEBUG:log("Spawning Thread...")
				thread.start_new_thread(self.update_thread_func,())
				if INSANE_DEBUG:log("Thread Started.")

	def update_thread_func(self):
		"""
		this function is our worker thread.
		it fetches data from teh internodes, updates our NodeUtil Properties, and exits
		"""
		if INSANE_DEBUG:log("NodeUtil.update_thread_func()")

		self.status = "Updating"
		self.time = time.time()

		# Just get data for first service
		#try:
		service = self.get_services()[0]
		self.get_usage(service)
		self.get_history(service)
		self.get_service_info(service)
		self.ip = self.fetch_ip_address()

		if (self.status == "Updating"):
			self.status = "OK"
		#except:
		#	self.status = "Error"
		#	self.error = "An unexpected error occurred"

		log("Nodeutil.update complete")
		#thread.interrupt_main()

		#thread exits silently...
		thread.exit()
