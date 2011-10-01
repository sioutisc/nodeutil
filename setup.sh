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

echo -e "\nInternode Applet for GNOME and AWN - Installer.\n\nSearching for Gnome / AWN..."

locate_gnome_panel
locate_awn

if [ -z "$GNOMEPREFIX" ] && [ -z "$AWNPREFIX" ]; then
	#echo "You need to have either (or both) Gnome Panel or Avant Window Navigator installed to use this applet!"
	#exit 1
	echo -e "\nNOTICE: This applet probably won't be particularly useful if you're not using gnome-panel or avant-window-navigator. You should probably install one or both of these before proceeding. "
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

echo ""
read -p "Proceed? (Y/N) " c
if [ -z "`echo $c | egrep '[Yy]([Ee][Ss])?'`" ]; then
	echo -e "\n"
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
echo -e "\n\nInstallation is complete. You'll need to restart the relevant program(s) with commands like:"
if [ -n "$AWNPREFIX" ]; then
	echo "  killall avant-window-navigator && avant-window-navigator &"
fi
if [ -n "$GNOMEPREFIX" ]; then
	echo "  killall gnome-panel"
fi
echo -e "Or you can just log out and back in. or reboot. or alt-prtscn-k. or maybe ctrl-alt-bksp. or sudo killall xinit."
echo -e "Once you've restarted your panel app(s), you should be able to add the internode applet to the Gnome panel and/or AWN\n"
echo -e "You can get a usage report from the command-line by typing 'internode-usage-report'.\n"
echo "You can also run '$APPPATH/run_in_window' to get the GNOME applet in it's own small window."
echo -e "\nIf you have problems, check out /tmp/internode-applet.log. You can also email this file to antisol@internode.on.net with 'internode applet' in the subject."
echo -e "\nEnjoy! :)\n\n"

