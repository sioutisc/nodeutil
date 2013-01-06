#!/bin/bash
PWD=`pwd`
cd `dirname $0`
echo "Creating tarball..."
tar --exclude=*.tgz --exclude=Screenshot* --exclude=*.pyc --exclude=.* -zcvf ~/node_applet.tgz *
echo "Done."
./create-self-extractor.sh ~/node_applet.tgz ~/nodeutil_installer.sh installer
cd $PWD

