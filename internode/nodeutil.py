####################################################
# nodeutil2 - threaded reimplementation of nodeutil
# Copyright (C) Dale Maggee, 2011.
# Based on the GNOME meter by Sam Pohlenz 
#	(http://www.sampohlenz.com/)
# see license.txt for License information
####################################################

import sys
import time
import datetime
import urllib2
import base64
from xml.dom import minidom
import thread
import threading

import credentials

VERSION=0.5

LOGFILE="/tmp/internode-applet.log"
"""
If set, log() wiimport gconfll output to a logfile
if set to None, log() goes to stdout, if debug is also true
"""

debug=False
"""
Sets Debugging Mode.
In debug mode:
	- Calls to log() produce output when LOGFILE is None (to stderr)
"""
def set_debug(v = True):
	global debug
	debug=v

INSANE_DEBUG = False

SIMULATE_NETERROR=False
"""
If True, NodeUtil will pretend like somebody just accidendally teh whole Intarwebs
"""
NETERR_MSG="*** Simulating a network error after 5 seconds ***"
"""
String to spit to log when simulating a network error
"""

ONE_KB = 1000
"""
How many bytes per KB/MB/etc do we use in calculations?

Internode uses 1000 (50000 bytes = 50 Kb) in their plans, si units: 1024
"""

def errprint(text):
	sys.stderr.write("%s\n" % text)

def log(text):
	"""
	Log a message with a timestamp
		if LOGFILE is set, log() will append to that file
		if debug is set log() will (also) output to stdout
	"""
	global debug
	ln = time.strftime("%Y-%m-%d %H:%M:%S") + ": " + text
	if LOGFILE:
		try:
			with open(LOGFILE, "a") as myfile:
				myfile.write(ln + "\n")
		except:
			#cannot write to logfile...
			errprint(time.strftime("%Y-%m-%d %H:%M:%S") + (": *** ERROR: Cannot log to file: '%s'. Check permissions?" % LOGFILE))
			errprint(ln)

	if debug:
		errprint(ln)

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

		self.credentials = credentials.CredentialsManager()

		self._time = 0
		#how long retrieval took
		self._took = 0
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

		#gconf client for retrieving gnome settings
		#self.gconf_client = gconf.client_get_default()

		#we set the 'updating' state initially, as 'OK' implies that we have data
		self.status = "Updating"

		self.keyring_id = None

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

	"""
	callbacks run into threading issues with GTK
		(updating GTK controls from a different thread causes issues, and is
			painful to do threadsafe, so we don't use them).
		instead, we poll nodeutil.status from the main thread

		the code below does provide callback functionality, though:
		usage:

			def callback_func():
				global mert
				print "Status changed to: " + mert.status

			mert = NodeUtil()
			mert.on_status_change(callback_func)
	"""
	
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
		Important Note: that they all use a reentrant lock to be threadsafe.
			Everything which is accessed/set from inside update_thread_func()
			needs to use a lock, or bad things can happen.

		When using these properties repeatedly, it's best to get their value once
			into a temp variable and use that repeatedly
	"""
	def get_time(self):
		with self.lock:
			return self._time
	def set_time(self,value):
		with self.lock:
			self._time = value
	time = property(get_time,set_time)

	# self.took is a float giving us the number of seconds
	#	we spent updating (i.e: how long it took to retrieve
	#	data from internode)
	def get_took(self):
		with self.lock:
			return self._took
	def set_took(self,value):
		with self.lock:
			self._took = value
	took = property(get_took,set_took)

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

	def get_mbperday(self):
		with self.lock:
			days = self.daysleft
			if days == 0: 
				days = 1
			return float(self.remaining / days)

	mbperday = property(get_mbperday)

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

	def set_error(self,errortext):
		"""
		Updates the nodeutil error message and status
		"""
		log("Nodeutil Error: %s" % errortext)
		self.error = errortext
		self.status = "Error"

	def load_prefs(self):
		log('Loading Preferences')
		return self.credentials.load_credentials()

	def save_prefs(self,username,password,show_used):
		log('Saving Preferences')
		self.credentials.username = username
		self.credentials.password = password
		self.credentials.show_used = show_used
		self.credentials.save_credentials()

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
			self.set_error("Failed to fetch service data.")

	def get_usage(self, service):
		if INSANE_DEBUG:log("Retrieving usage...")
		try:
			dom = self.api_request("%s/usage" % service['path'])

			traffic = dom.getElementsByTagName('traffic')[0]

			self.quota = float(traffic.getAttribute('quota')) / ONE_KB / ONE_KB
			self.used = float(self.get_text(traffic)) / ONE_KB / ONE_KB
			self.remaining = self.quota - self.used

			self.percent_remaining = self.remaining / self.quota * 100
			self.percent_used = self.used / self.quota * 100

			self.daysleft = get_date_difference(traffic.getAttribute('rollover'))

			self.time = time.time()
			if INSANE_DEBUG:log( "Data updated for username %s." % self.credentials.username)

			self.error = ""

		except:
			self.set_error("Failed to fetch usage data.")

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
			self.set_error("Failed to fetch usage data.")

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
				log(NETERR_MSG)
				time.sleep(5)
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
		#Note that unlike nodeutil.update(), this function blocks while network
		#	retrieval happens - it does not spawn a thread.
		try:
			log("NodeUtil.check_version()")

			if SIMULATE_NETERROR:
				#fake an error
				log(NETERR_MSG)
				time.sleep(5)
				raise IOError

			request = urllib2.Request("http://antisol.org/nodeutil/version-check.php?t=1")
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
			log(NETERR_MSG)
			time.sleep(5)
			raise IOError
		request = urllib2.Request("%s%s" % (self.api_host, path))
		user_agent = ('NodeUtil/%02.1f (%s)' % (VERSION,self.user_agent_text))
		#log("User Agent: '%s'" % user_agent)
		request.add_header('User-Agent', user_agent)
		request.add_header('Authorization', self.http_auth_string())
		result = urllib2.urlopen(request)
		return minidom.parse(result)

	def http_auth_string(self):
		base64string = base64.encodestring("%s:%s" % (self.credentials.username, self.credentials.password))[:-1]
		return "Basic %s" % base64string

	"""
	Update functions
	"""
	def update(self,force = False):
		"""
		do a fetch if the data is old enough, or if force is True

		fetch is done by spawning a new thread.

		"""

		if (self.status != "Updating" and (
			(time.time() - self.update_interval > self.time)) or force):
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

		
		try:
			# Just get data for first service
			service = self.get_services()[0]
			#don't continue to attempt retrieval after an error has occurred
			if self.status != "Error": self.get_usage(service)
			if self.status != "Error": self.get_history(service)
			if self.status != "Error": self.get_service_info(service)
			if self.status != "Error": self.ip = self.fetch_ip_address()
	
			#don't set status to OK if an error occurred:
			if (self.status != "Error"):
				self.status = "OK"
		except:
			if self.status != "Error":	#don't overwrite existing error message
				self.status = "Error"
				self.set_error("An unexpected error occurred")

		#calculate how long we took and populate self.took
		took = time.time() - self.time
		self.took = took
		log("Nodeutil.update complete after %2.3f seconds" % took)

		#thread.interrupt_main()

		#thread exits silently...
		thread.exit()
