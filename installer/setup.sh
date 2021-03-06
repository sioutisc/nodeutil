#!/bin/bash
#####################################################
# Installer for internode applet.
# By Dale Maggee
#####################################################

if [ "`whoami`" != "root" ]; then
	echo -e "\nThis installer needs to be run as root.\n"
	exit 1
fi

#this is a 1-liner function I rote to use select to recursively/interactively choose an install dir.
#	set $DIR to an initial path, then call this. once done, $LOC will be populated with a path
#(unused)
#get_dir() { PS3="Choose Option: ";if [ -z "$DIR" ]; then DIR="/"; fi; select i in "---Install Here---" "(parent)" $DIR* ; do if [ "$REPLY" == "1" ]; then LOC=$DIR; break; fi; if [ "$REPLY" == "2" ]; then DIR="`dirname $DIR`"; else DIR="$i/"; fi; get_dir mert; RECURSE=""; break; done; if [ -z "$1" ]; then echo "You chose: $LOC"; fi }

#populate $AWNPREFIX and $AWNSUFFIX
locate_awn() {
	AWNSUFFIX="share/avant-window-navigator/applets"
	AWNPREFIX="/usr/local"
	if [ -z "`ls $AWNPREFIX/$AWNSUFFIX 2>/dev/null`" ]; then
		AWNPREFIX="/usr"
		if [ -z "`ls $AWNPREFIX/$AWNSUFFIX 2>/dev/null`" ]; then
			AWNPREFIX=""
			echo " - AWN not found!"
			return 1
		fi;
	fi;
	echo " - AWN applet will be installed in '$AWNPREFIX/$AWNSUFFIX'"
	return 0
}

#populate $GNOMEPREFIX and $GNOMESUFFIX
locate_gnome_panel() {
	GNOMESUFFIX="lib/bonobo/servers"
	GNOMEPREFIX="/usr/local"
	if [ -z "`ls $GNOMEPREFIX/$GNOMESUFFIX 2>/dev/null`" ]; then
		GNOMEPREFIX="/usr"
		if [ -z "`ls $GNOMEPREFIX/$GNOMESUFFIX 2>/dev/null`" ]; then
			GNOMEPREFIX=""
			echo " - GNOME-panel not found!"
			return 1
		fi;
	fi;
	echo " - GNOME Applet will be installed in '$GNOMEPREFIX/$GNOMESUFFIX'"
	return 0
}

echo -e "\nThe NodeUtil Suite - Installer.\n"

#check dependencies...
if ./checkdeps; then
	echo "No vital dependencies are missing, good."
else 
	echo -e "\n\nVital dependencies are missing, aborting install."
	exit 1
fi	

echo -e "Searching for Gnome / AWN..."

locate_gnome_panel
locate_awn

if [ -z "$GNOMEPREFIX" ] && [ -z "$AWNPREFIX" ]; then
	#echo "You need to have either (or both) Gnome Panel or Avant Window Navigator installed to use this applet!"
	#exit 1
	echo -e "\nNOTICE: You don't seem to have either gnome-panel or avant-window-navigator installed! You will only be able to use the command-line tools. "
fi



if [ -n "$GNOMEPREFIX" ]; then
	APPPATH="$GNOMEPREFIX/share/internode-applet"
else
	if [ -n "$AWNPREFIX" ]; then
		APPPATH="$AWNPREFIX/share/internode-applet"
	else
		APPPATH="/usr/share/internode-applet"
	fi;
fi

echo " - Internode Applet files will be installed in '$APPPATH'"



#for dpkg-based systems, try to detect and warn about python-gnomeapplet and awn-extras dependencies, which may not be
#	installed on a clean system
#if [ -n "`which dpkg`" ]; then
#	echo " - Your system seems to use dpkg, checking for dependencies..."
#	if [ -z "`dpkg -L python-gnomeapplet 2>/dev/null`" ]; then
#		#warn about missing python-gnomeapplet library
#		echo -e "\nNOTICE: it appears that python-gnomeapplet is not installed. You may want to run 'sudo apt-get install python-gnomeapplet' to install it. If you're not running Ubuntu, this might not be a problem - the library you need might have a different name."
#		read -p "Shall I try to run this now (only guaranteed to work if you're running Ubuntu 10.04-11.04) (Y/N)?" c
#		if [ -n "`echo $c | egrep '[Yy]([Ee][Ss])?'`" ]; then
#			apt-get install python-gnomeapplet
#		fi
#	fi
#	
#	if [ -n "$AWNPREFIX" ]; then
#		#look for awnlib
#		if [ -z "`dpkg -L python-awn-extras`" ]; then
#			echo -e "\nNOTICE: it appears that awn is installed, but python-awn-extras is not installed. You may want to run 'sudo apt-get install python-awn-extras' to install it if you intend to use the awn applet. If you're not running Ubuntu, this might not be a problem - the library you need might have a different name."
#			read -p "Shall I try to run this now (only guaranteed to work if you're running Ubuntu 10.04-11.04) (Y/N)?" c
#			if [ -n "`echo $c | egrep '[Yy]([Ee][Ss])?'`" ]; then
#				apt-get install python-awn-extras
#			fi
#		fi	
#	fi
#fi

echo ""
read -p "Proceed with install? (Y/N) " c
if [ -z "`echo $c | egrep '[Yy]([Ee][Ss])?'`" ]; then
	echo -e "\nAborted.\n\n"
	exit 1
fi

echo -e "\nOkie Dokie Doctor Jones, hold on to your potatoes!\n"
#copy files into the application dir...

#array containing files to copy to $APPPATH
internode_files=( "awn-applet.py" "INSTALL" "internode-applet.glade" "internode-applet.py" "internode.desktop" "InternodeUsageMeterApplet.server.in" "Makefile" "run_in_window" "setup.sh" "README" "internode-usage-report" )
#array containing folders to copy (recursively, with all files) to $APPPATH
internode_dirs=( "internode" "pixmaps" )

#array of files to mark as executable for everyone - should be a path relative to $APPPATH:
make_executable=( "internode-applet.py" "awn-applet.py" "run_in_window" "setup.sh" "internode-usage-report" )

if [ ! -d "$APPPATH" ]; then
	echo " - Creating '$APPPATH'..."
	mkdir $APPPATH
else
	echo "  (Overwriting previous installation!)"
fi
echo -n " - Copying files..."
for f in "${internode_files[@]}"; do
	cp -v $f $APPPATH
done

for d in "${internode_dirs[@]}"; do
	cp -Rv $d $APPPATH/
done
for f in "${make_executable[@]}"; do
	chmod a+x $APPPATH/$f
done
#now that all our files are in $APPPATH, create symlinks for awn and gnome to find...
echo ", Done."

if [ -n "$GNOMEPREFIX" ]; then
	echo " - Installing GNOME Applet..."
	cp $APPPATH/InternodeUsageMeterApplet.server.in $APPPATH/InternodeUsageMeterApplet.server
	#TODO: replace "@PREFIX@" in the .server file with $APPPATH
	sed -i "s|@PREFIX@|$APPPATH|g" $APPPATH/InternodeUsageMeterApplet.server
	ln -s $APPPATH/InternodeUsageMeterApplet.server $GNOMEPREFIX/$GNOMESUFFIX/InternodeUsageMeterApplet.server
fi

if [ -n "$AWNPREFIX" ]; then
	echo " - Installing AWN Applet..."
	#create symlinks in awn's applets dir: one to $APPPATH, and one for the desktop file...
	ln -s $APPPATH $AWNPREFIX/$AWNSUFFIX/internode
	ln -s $APPPATH/internode.desktop $AWNPREFIX/$AWNSUFFIX/internode.desktop
fi

echo " - Installing 'internode-usage-report' command-line app..."
ln -s $APPPATH/internode-usage-report /usr/bin/internode-usage-report
#everything's perfect, tell the user how to get the applets
echo "-------------------------------------------------------------------------------"
echo -e "\n\nInstallation is complete. You'll need to restart the relevant program(s) with commands like:"
if [ -n "$AWNPREFIX" ]; then
	echo "  killall avant-window-navigator && avant-window-navigator &"
fi
if [ -n "$GNOMEPREFIX" ]; then
	echo "  killall gnome-panel"
fi
echo -e "Or you can just log out and back in.\n"
echo -e "Once you've restarted your panel app(s), you should be able to add the internode applet to the Gnome panel and/or AWN\n"
read -p "Shall I try to restart your panel app(s) now (Y/N)?" c
if [ -n "`echo $c | egrep '[Yy]([Ee][Ss])?'`" ]; then
	if [ -n "$GNOMEPREFIX" ]; then
		echo " - Killing gnome-panel..."
		killall gnome-panel
	fi
	if [ -n "$AWNPREFIX" ]; then
		echo " - Killing avant-window-navigator..."
		killall avant-window-navigator
		sudo -u1000 avant-window-navigator &
		echo "    NOTE: You'll probably have to run 'avant-window-navigator' yourself"
	fi
	echo -e "Done!\n\n"
fi

echo -e "You can get a usage report from the command-line by typing 'internode-usage-report'.\n"
echo "You can also run '$APPPATH/run_in_window' to get the GNOME applet in it's own small window."
echo -e "\nIf you have problems, check out /tmp/internode-applet.log. You can also email this file to nodeutil@antisol.org with 'internode applet' in the subject."
echo -e "\nEnjoy! :)\n\n - Dale Maggee\n\n"

