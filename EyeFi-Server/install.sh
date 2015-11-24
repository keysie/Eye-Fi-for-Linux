#!/bin/sh

SRCPATH=./eyefiserver
DSTPATH=/usr/local/eyefiserver
PYTHONPATH=/usr/bin
RCDPATH=/usr/local/eyefiserver/rc.d

# Check if run as root

if [ "$(whoami)" != "root" ]
then
	echo "Must be run as root!"
	echo "Exiting"
	exit 0
fi


# Intro

clear
echo "============================================="
echo "== Eye-Fi for Linux installation by keysie =="
echo "============================================="
echo


# Read path to settings.xml-file

echo "Enter path to your card's \"Settings.xml\"-file"
echo "You can find it after configuring the card here:"
echo "C:\Users\<user>\AppData\Roaming\Eye-Fi\\"
echo
echo "(Press [ENTER] for './Settings.xml'):"
read SETTFILE


# Check if only [ENTER] has been pressed and if yes,
# use ./Settings.xml

if [ ${SETTFILE}=="\n" ]
then
	SETTFILE="./Settings.xml"
fi


# Check if file exists. If not throw error and exit.

if [ -e "${SETTFILE}" ]
then
	# okay
	echo "Parsing file..."
else
	#throw error and exit
	echo "File does not exist."
	exit 0
fi


# Automatically parse the file to find uploadkey,
# ESSID and WPA2-password

uploadkey="$(cat ${SETTFILE} | grep -P -o '(?<=(<UploadKey>))[0-9a-z]*(?=(</UploadKey>))')"
essid="$(cat Settings.xml | grep -P -o '(?<=(SSIDName=")).*(?=(" CustomName=))')"
wpa2key="$(cat Settings.xml | grep -P -o '(?<=(<ConfigInfo KeyInfo="))[0-9A-Z]*(?=(" SSIDName))')"


# Check lengths of outputs to 'sort of' verify success

if [ ${#uploadkey} -lt 30 ] || [ ${#essid} -lt 1 ] || [ ${#wpa2key} -lt 8 ]
then 
	echo "Failed to parse file."
	exit 0
fi


# If we are here, all went well and we can disply 
# the results from the config-file to show how cool
# this script is

echo
echo -n "Upload-key found: "
echo "${uploadkey}"
echo -n "     ESSID found: "
echo "${essid}"
echo -n "  WPA2-key found: "
echo "${wpa2key}"
echo


# Also, store essid and key in a new config-file
# so they can be used e.g. from a script automating
# the connection to the card.
# Furthermore, prepend a line instructing wpa_supplicant
# to use the standard control interface so wpa_cli can
# talk to it.

rm ${SRCPATH}/etc/eyeficard.wpa 1>/dev/null 2>/dev/null
touch ${SRCPATH}/etc/eyeficard.wpa > /dev/null 2>&1

echo "ctrl_interface=/var/run/wpa_supplicant" > ${SRCPATH}/etc/eyeficard.wpa
wpa_passphrase "${essid}" "${wpa2key}" >> ${SRCPATH}/etc/eyeficard.wpa


# Next step: Get the path to where files should be
# uploaded by the server. Make user with ID 1000
# the default case.

user="$(getent passwd "1000" | cut -d: -f1)"

echo "Enter your Eye-Fi upload path"
echo "When connecting, all files are downloaded in one directory"
echo "the name of the directory can be a formatted string like" 
echo "/volume1/<shared folder>/%%Y-%%m-%%d"
echo

echo "(Press [ENTER] for '/home/${user}/Pictures/Eye-Fi/%%Y-%%m-%%d'):"
read uploaddir
echo

if [ ${uploaddir}=="\n" ]
then
	uploaddir="/home/${user}/Pictures/Eye-Fi/%%Y-%%m-%%d"
else
	echo "Enter default user to use eyefiserver:"
	read user
fi


#parse eyefiserver.tmpl and write to eyefiserver.conf

rm "${SRCPATH}/etc/eyefiserver.conf" > /dev/null 2>&1
while read line
do
    eval echo "$line" >> "${SRCPATH}/etc/eyefiserver.conf"
done < "${SRCPATH}/etc/eyefiserver.tmpl"


# stop currently installed version (if exists)

${RCDPATH}/S99EyeFiServer.sh stop > /dev/null 2 > /dev/null


# Create destination directory and copy files

mkdir ${DSTPATH} > /dev/null 2>&1
mkdir ${RCDPATH} > /dev/null 2>&1
echo Copying files..
cp ${SRCPATH}/* ${DSTPATH} -r 

# copy underlying start/stop script
# (could be used to make eyefiserver
#  start on boot for example)

cp ./rc.d/S99EyeFiServer.sh ${RCDPATH} 
echo 
echo Setting properties..
chmod +x ${DSTPATH}/bin/eyefiserver.py > /dev/null 2>&1
chmod +x ${RCDPATH}/S99EyeFiServer.sh > /dev/null 2>&1
chown ${user}:${user} ${DSTPATH}/var/log/eyefiserver.log > /dev/null 2>&1


# Make sure start.sh and stop.sh are executable and owned by
# the right user

chmod +x ./start.sh
chown ${user}:${user} ./start.sh
chmod +x ./stop.sh
chown ${user}:${user} ./stop.sh

echo "Starting server verbosely and on foreground to verify"
echo "installation. If this works correctly, start and stop"
echo "server using './start.sh [-v]' and './stop.sh'"
echo "NOTE: Both scripts must be run as root to work nicely,"
echo "      but they may be copied to or run from anywhere."
echo

./start.sh -v

# BELOW: OLD CONFIGURATION

#echo "If this throws an error about the socket"
#echo "being already in use, execute:"
#echo
#echo "sudo netstat -pln | grep 59278"
#echo
#echo "and kill the returned process"
#echo

#${PYTHONPATH}/python ${DSTPATH}/bin/eyefiserver.py ${DSTPATH}/etc/eyefiserver.conf ${DSTPATH}/var/eyefiserver.log


