# ==================================================
# Copyright 2012,  Christos Sioutis
# christos.sioutis@gmail.com
#
# The CredentialsManager uses the Gnome Keyring to 
# store credentials. This is more secure than the
# gconf solution used previously
# ==================================================

import gnomekeyring as gk
import glib

class CredentialsManager:

	def __init__(self):
		self.keyring = "login"
		self.display_name = "nodeutil"
		self.username = None
		self.password = None
		self.show_used = True
		glib.set_application_name(self.display_name)

	def load_credentials(self):
		item_keys = gk.list_item_ids_sync(self.keyring)
		for key in item_keys:
			item_info = gk.item_get_info_sync(self.keyring, key)
			if item_info.get_display_name() == self.display_name:
				item_info = gk.item_get_info_sync(self.keyring, key)
				keyring_attrs = gk.item_get_attributes_sync(self.keyring, key)
				self.username = keyring_attrs["username"]
				self.password = item_info.get_secret()
				self.show_used = bool(keyring_attrs["show_used"])
				return True;
		return False;

	def save_credentials(self,username,passw,show_used):		
		self.username = username
		self.password = passw
		self.show_used = show_used
		gk.item_create_sync(self.keyring, gk.ITEM_GENERIC_SECRET, self.display_name,
								  {"username":username,"show_used":show_used}, passw, True)

	def print_credentials(self):
		print "username: " + self.username
		print "password: " + self.password
		print "show_used: " + str(self.show_used)

	def prompt_for_credentials(self):
		self.username = raw_input("Enter username: ")
		self.password = raw_input("Enter password: ")
		self.show_used = True
		self.save_credentials(self.username,self.password,self.show_used)

def print_keyring_items(keyring):
	item_keys = gk.list_item_ids_sync(keyring)
	print 'Existing item Keys:',item_keys 
	for key in item_keys:
		item_info = gk.item_get_info_sync(keyring, key)
		print "\nItem number",key
		print "\tName:", item_info.get_display_name()
		print "\tPassword:", item_info.get_secret()
		print "\tAttributes:", gk.item_get_attributes_sync(keyring, key)

if __name__ == "__main__":
	try:
		cm = CredentialsManager()
		cm.load_credentials()
		cm.print_credentials()
	except AttributeError:
		print "Error: No credentials found"

