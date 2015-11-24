#!/bin/bash


# Some variables for pretty output

red=`tput setaf 1`
green=`tput setaf 2`
reset=`tput sgr0`
ok="[${green}ok${reset}]"
error="[${red}error${reset}]"


# Path to configuration file containing essid and key
# for the cards own wifi (this file is created by the
# installation script install.sh)

CONFIGPATH=/usr/local/eyefiserver/etc
CONFIGFILE=${CONFIGPATH}/eyeficard.wpa


# Check if run as root
function check_root()
{
	if [ "$(whoami)" != "root" ]
	then
		display "Must be run as root!" "Exiting"
		exit 0
	fi
}


# Stop built-in network manager and make sure this 
# opperation succeeds
function stop_nm()
{
	echo -n "Stopping network manager... "
	result="$(stop network-manager 2>&1 1>/dev/null)"
	if [ "${#result}" -eq 0 ]
	then
		echo "${ok}"
	else
		if [ "${result}" = "stop: Unknown instance: " ]
		then
			echo "[${green}already stopped${reset}]"
		else
			echo "${error}"
			echo "${result}"
			exit 0
		fi
	fi
}


# Start network-manager and check result
function start_nm()
{
	echo -n "Starting network manager... "
	result="$(start network-manager 2>&1)"
	case ${result} in
	"start: Job is already running: network-manager")
		echo "[${green}already running${reset}]"
		;;
	"network-manager start/running, process "[0-9]*)
		pid="$(echo ${result} | grep -P -o '(?<=(start/running, process ))[0-9]*(?=())')"
		echo "[${green}pid=${pid}${reset}]"
		;;
	*)
		echo "${error}"
		echo "${result}"
		exit
	esac
}


# Parse eyeficard.wpa for desired SSID
function get_des_ssid()
{
	des_ssid="$(cat ${CONFIGFILE} | grep -P -o '(?<=(ssid=\")).*(?=(\"))')"
}


# Get SSID of currently connected AP
function cur_ssid()
{
	echo "$(iwconfig wlan0 | grep -P -o '(?<=(ESSID:\")).*(?=(\"))')"
}


# Check if desired SSID is available
function is_available()
{
	# enable wlan
	ifconfig wlan0 up
	
	# sleep shortly
	sleep 1

	# scan for ssids
	result="$(iw wlan0 scan | grep "SSID: ${des_ssid}")"
	if [ "${#result}" -eq 0 ]
	then
		# not found, return 'false'
		echo "false"
	else
		# found, return true
		echo "true"
	fi
}


# Try to connect using wpa_supplicant
function connect()
{
	# make sure no other wpa_supplicant is running
	killall wpa_supplicant

	# try starting wpa_supplicant using config-file
	wpa_supplicant -B -iwlan0 -c ${CONFIGFILE}

	# give the deamon a little time to complete the connection
	sleep 2
}


# display title + status
function display()
{
	clear
	echo "================================"
	echo "== Auto connect to EyeFi-card =="
	echo "================================"
	echo 
	echo
	echo $1
	echo $2
	echo $3
	echo "( Stop with Ctrl+C )"
	echo
	echo "================================"
	echo
	if [ "$1" != "" ]
	then
		sleep 1
	fi
}


# Trap for Ctrl+C to cleanly exit the script
int_trap()
{
	display "Stopping..."

	pkill wpa_supplicant
	pkill dhclient

	start_nm
	exit 0
}



################# Program ####################

display

# Check if executed as root or sudo
display "$(check_root)"

# Get desired AP SSID from config file
get_des_ssid

# Stop network-manager
display "$(stop_nm)"


# Endless loop
first="true"

trap int_trap INT
while [ 1 -eq 1 ]
do

	# Check if we are already connected to the desired AP
	if [ "$(cur_ssid)" == "${des_ssid}" ]
	then
		# If yes, do nothing
		# except the first time. start dhclient then
		if [ "${first}" == "true" ]
		then
			dhclient wlan0
			first="false"
		fi
		display "Connected to $(cur_ssid)"
	else
		# Check if card wlan is at all available
		if [ "$(is_available)" == "true" ]
		then
			# try to connect
			display "Connecting..."
			display "$(connect)"
		else
			# do nothing
			display "Network not found"
			first="true"
		fi
	fi

	# wait
	sleep 1

done



