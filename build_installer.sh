#!/bin/bash
PWD=`pwd`
cd `dirname $0`
tar --exclude=*.tgz --exclude=Screenshot* --exclude=*.pyc --exclude=.* -zcvf ~/node_applet.tgz *
./create-self-extractor.sh ~/node_applet.tgz ~/nodeutil_installer.sh installer
cd $PWD

