#!/bin/bash
#############################################################
# Self-extracting bash script creator
# By Dale Maggee
# Public Domain
#############################################################
#
# This script creates a self-extracting bash script
#	containing a compressed payload.
# Optionally, it can also have the self-extractor run a
#	script after extraction.
#
#############################################################
VERSION='0.1'

output_extract_script() {
#echoes the extraction script which goes at the top of our self-extractor
#arguments:
#	$target - suggested destination directory (default: somewhere in /tmp)
#	$installer - name of installer script to run after extract
#			(if specified, $target is ignored and /tmp is used)

#NOTE: odd things in this function due to heredoc:
# - no indenting
# - things like $ and backticks need to be escaped to get into the destination script

cat <<EndOfHeader
#!/bin/bash
echo "Self-extracting bash script. By Dale Maggee."
echo "Extracting..."
target=\`mktemp -d /tmp/XXXXXXXXX\`

EndOfHeader

#here we put our conditional stuff for the extractor script. 
#note: try to keep it minimal (use vars) so as to make it nice and clean.
if [ "$installer" != "" ]; then
	#installer specified
	echo 'INSTALLER="'$installer'"'
else
	if [ "$target" != "" ]; then
		echo '(temp dir: '$target')'
	fi
fi

cat <<EndOfFooter

echo "(temp dir: \$target)"

#do the extraction...
ARCHIVE=\`awk '/^---BEGIN TGZ DATA---/ {print NR + 1; exit 0; }' \$0\`

tail -n+\$ARCHIVE \$0 | tar xz -C \$target

CDIR=\`pwd\`
cd \$target
./installer

cd \$CDIR
rm -rf \$target

exit 0
---BEGIN TGZ DATA---
EndOfFooter
}

make_self_extractor() {

	echo "Building Self Extractor: $2 from $1."

	if [ -f "$3" ]; then
		installer="$3"
		echo " - Installer script: $installer"
	fi

	if [ "$4" != "" ]; then
		target="$4"
		echo " - Default target is: $target"
	fi

	src="$1"
	dest="$2"
	#check input...
	if [ ! -f "$src" ]; then
		echo "source: '$src' does not exist!"
		exit 1
	fi
	if [ -f "$dest" ]; then
		echo "'$dest' will be overwritten!"
	fi

	#ext=`echo $src|awk -F . '{print $NF}'`

	#create the extraction script...
	output_extract_script > $dest
	cat $src >> $dest

	chmod a+x $dest

	echo "Done! Self-extracting script is: '$dest'"
}

show_usage() {
	echo "Usage:"
	echo -e "\t$0 src dest installer"

	echo -en "\n\n"
} 


############
# Main
############

if [ -z "$1" ] || [ -z "$2" ]; then
	show_usage
	exit 1
else
	make_self_extractor $1 $2 $3
fi
